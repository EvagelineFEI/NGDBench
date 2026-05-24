"""Unstructured evidence dataset construction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol

from .neo4j_executor import Neo4jExecutor
from .translation import (
    OpenAITranslationClient,
    TranslationClient,
    TranslationPromptConfig,
    translate_queries,
)


class EvidenceExecutor(Protocol):
    def execute(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ...


def construct_unstructured_dataset(
    input_path: str | Path,
    output_path: str | Path,
    neo4j_uri: str | None,
    neo4j_user: str | None,
    neo4j_password: str | None,
    api_key: str,
    base_url: str,
    model: str,
    chunk_size: int = 50,
    fail_fast: bool = False,
    translate_only: bool = False,
    limit: int | None = None,
    keep_template_id: bool = True,
    translation_client: TranslationClient | None = None,
    prompt_config: TranslationPromptConfig | None = None,
) -> dict[str, Any]:
    records = _load_records(input_path, limit=limit)

    if translate_only:
        output_records = [
            build_unstructured_record(
                record,
                executor=None,
                keep_template_id=keep_template_id,
                fail_fast=fail_fast,
                translate_only=True,
            )
            for record in records
        ]
    else:
        with Neo4jExecutor(neo4j_uri, neo4j_user, neo4j_password) as executor:
            output_records = [
                build_unstructured_record(
                    record,
                    executor=executor,
                    keep_template_id=keep_template_id,
                    fail_fast=fail_fast,
                )
                for record in records
            ]

    client = translation_client or OpenAITranslationClient(
        api_key,
        base_url,
        model,
        prompt_config=prompt_config,
    )
    translations, translation_stats = translate_queries(
        [record["query"] for record in output_records],
        client=client,
        chunk_size=chunk_size,
        fail_fast=fail_fast,
    )
    for record, nlp in zip(output_records, translations):
        record["nlp"] = nlp

    _write_records(output_path, output_records)
    return {
        "total": len(output_records),
        "translation_failed_batches": translation_stats.failed_batches,
    }


def build_unstructured_record(
    record: dict[str, Any],
    executor: EvidenceExecutor | None,
    keep_template_id: bool = True,
    fail_fast: bool = False,
    translate_only: bool = False,
) -> dict[str, Any]:
    query = record.get("query", "")
    answer = record.get("answer", [])
    output_record: dict[str, Any] = {
        "template_type": record.get("template_type", ""),
        "query": query,
        "answer": answer,
        "query_node_ids": [],
        "answer_node_ids": [],
        "mention_in_nodes": [],
        "error": None,
        "nlp": "",
    }
    if keep_template_id:
        output_record["template_id"] = record.get("template_id")
    if "gnd" in record:
        output_record["gnd"] = record["gnd"]

    try:
        query_node_ids = extract_node_ids_from_query(query)
        answer_node_ids = extract_node_ids_from_answer(answer)
        query_mentions: list[str] = []
        answer_mentions: list[str] = []
        if not translate_only:
            if executor is None:
                raise ValueError("executor is required unless translate_only=True")
            query_mentions = get_mention_in_target_ids(executor, query_node_ids)
            answer_mentions = get_mention_in_target_ids(executor, answer_node_ids)

        output_record["query_node_ids"] = sorted(query_node_ids)
        output_record["answer_node_ids"] = sorted(answer_node_ids)
        output_record["mention_in_nodes"] = sorted(set(query_mentions) | set(answer_mentions))
        return output_record
    except Exception as exc:
        output_record["error"] = str(exc)
        if fail_fast:
            raise
        return output_record


def extract_node_ids_from_query(query: str) -> set[str]:
    node_ids: set[str] = set()
    patterns = [
        r"\{[^}]*id\s*:\s*['\"]([^'\"]+)['\"]",
        r"\bid\s*=\s*['\"]([^'\"]+)['\"]",
    ]
    for pattern in patterns:
        node_ids.update(re.findall(pattern, query))
    return node_ids


def extract_node_ids_from_answer(answer: Any) -> set[str]:
    node_ids: set[str] = set()
    special_single_id_keys = {
        "ProviderID",
        "TargetFunction",
        "a.id",
        "b.id",
        "m.id",
        "ComputeNode",
        "StorageProvider",
    }
    special_list_id_keys = {
        "ListOfMemoryFunctions",
        "ListOfCodeProviders",
        "m_list",
        "n_list",
    }

    def is_id_key(key: str) -> bool:
        return key == "id" or (isinstance(key, str) and key.endswith(".id"))

    def extract_from_value(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("id") is not None:
                node_ids.add(str(value["id"]))

            for key, inner in value.items():
                if is_id_key(key) and inner is not None:
                    node_ids.add(str(inner))

            for key in special_single_id_keys:
                if value.get(key) is not None:
                    node_ids.add(str(value[key]))

            for key in special_list_id_keys:
                if isinstance(value.get(key), list):
                    for item in value[key]:
                        if item is not None:
                            node_ids.add(str(item))

            for inner in value.values():
                extract_from_value(inner)
            return

        if isinstance(value, list):
            for item in value:
                extract_from_value(item)

    extract_from_value(answer)
    return node_ids


def get_mention_in_target_ids(
    executor: EvidenceExecutor,
    node_ids: set[str],
    batch_size: int = 100,
) -> list[str]:
    if not node_ids:
        return []

    target_ids: set[str] = set()
    node_id_list = sorted(node_ids)
    for start in range(0, len(node_id_list), batch_size):
        batch_ids = node_id_list[start : start + batch_size]
        try:
            results = executor.execute(
                """
                MATCH (n)-[:mention_in]->(m)
                WHERE n.id IN $node_ids
                RETURN DISTINCT m.id AS target_id
                """,
                {"node_ids": batch_ids},
            )
        except Exception:
            results = _get_mention_targets_one_by_one(executor, batch_ids)

        for row in results:
            target_id = row.get("target_id")
            if target_id:
                target_ids.add(str(target_id))
    return sorted(target_ids)


def _get_mention_targets_one_by_one(
    executor: EvidenceExecutor,
    node_ids: list[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for node_id in node_ids:
        try:
            results.extend(
                executor.execute(
                    """
                    MATCH (n)-[:mention_in]->(m)
                    WHERE n.id = $node_id
                    RETURN DISTINCT m.id AS target_id
                    """,
                    {"node_id": node_id},
                )
            )
        except Exception:
            continue
    return results


def _load_records(input_path: str | Path, limit: int | None) -> list[dict[str, Any]]:
    with Path(input_path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("input JSON must contain a list of query records")
    return data[:limit] if limit is not None else data


def _write_records(output_path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

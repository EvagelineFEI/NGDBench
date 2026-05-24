"""One-shot dataset construction workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cleaning import clean_answer, clean_answer_for_node_aliases, is_empty_answer
from .cypher_rewrite import get_node_id_return_aliases, rewrite_return_nodes_to_ids
from .neo4j_executor import Neo4jExecutor
from .translation import (
    OpenAITranslationClient,
    TranslationClient,
    TranslationPromptConfig,
    translate_queries,
)


def construct_dataset(
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
    skip_empty_answer: bool = False,
    translate_only: bool = False,
    limit: int | None = None,
    keep_template_id: bool = True,
    translation_client: TranslationClient | None = None,
    prompt_config: TranslationPromptConfig | None = None,
) -> dict[str, Any]:
    records = _load_records(input_path, limit=limit)
    output_records = _build_records(records, keep_template_id=keep_template_id)

    if not translate_only:
        with Neo4jExecutor(neo4j_uri, neo4j_user, neo4j_password) as executor:
            _execute_noise_queries(output_records, executor, fail_fast=fail_fast)

    if skip_empty_answer:
        output_records = [
            record for record in output_records if not is_empty_answer(record["clean_answer"])
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


def _load_records(input_path: str | Path, limit: int | None) -> list[dict[str, Any]]:
    with Path(input_path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("input JSON must contain a list of query records")
    return data[:limit] if limit is not None else data


def _build_records(
    records: list[dict[str, Any]],
    keep_template_id: bool,
) -> list[dict[str, Any]]:
    output_records: list[dict[str, Any]] = []
    for record in records:
        rewritten_query = rewrite_return_nodes_to_ids(record.get("query", ""))
        output_record = {
            "template_type": record.get("template_type", ""),
            "query": rewritten_query,
            "clean_answer": clean_answer(record.get("answer", [])),
            "noise_answer": None,
            "same_as_cleangraph": False,
            "nlp": "",
        }
        if keep_template_id:
            output_record["template_id"] = record.get("template_id")
        output_records.append(output_record)
    return output_records


def _execute_noise_queries(
    records: list[dict[str, Any]],
    executor: Neo4jExecutor,
    fail_fast: bool,
) -> None:
    for record in records:
        try:
            noise_raw = executor.execute(record["query"])
            record["noise_answer"] = clean_answer_for_node_aliases(
                noise_raw,
                node_id_aliases=get_node_id_return_aliases(record["query"]),
            )
            record["same_as_cleangraph"] = record["clean_answer"] == record["noise_answer"]
        except Exception as exc:
            record["noise_answer"] = None
            record["same_as_cleangraph"] = False
            record["error"] = str(exc)
            if fail_fast:
                raise


def _write_records(output_path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

"""Constructors for the non-standard dataset shapes documented in case.md."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cleaning import clean_answer
from .neo4j_executor import Neo4jExecutor
from .translation import (
    OpenAITranslationClient,
    TranslationClient,
    TranslationPromptConfig,
    translate_queries,
)


def construct_management_dataset(
    input_path: str | Path,
    output_path: str | Path,
    api_key: str,
    base_url: str,
    model: str,
    chunk_size: int = 50,
    fail_fast: bool = False,
    translate_only: bool = False,
    limit: int | None = None,
    translation_client: TranslationClient | None = None,
    prompt_config: TranslationPromptConfig | None = None,
) -> dict[str, Any]:
    records = _load_records(input_path, limit=limit)
    output_records = [_build_management_record(record) for record in records]

    query_refs: list[tuple[dict[str, Any], str]] = []
    queries: list[str] = []
    for record in output_records:
        for step in record.get("steps", []):
            query_refs.append((step, "operate_nlp"))
            queries.append(step.get("operate_query", ""))
            query_refs.append((step, "valid_nlp"))
            queries.append(step.get("valid_query", ""))

    client = translation_client or OpenAITranslationClient(
        api_key,
        base_url,
        model,
        prompt_config=prompt_config,
    )
    translations, translation_stats = translate_queries(
        queries,
        client=client,
        chunk_size=chunk_size,
        fail_fast=fail_fast,
    )
    for (step, field), translation in zip(query_refs, translations):
        step[field] = translation

    _write_records(output_path, output_records)
    return {
        "total": len(output_records),
        "translation_failed_batches": translation_stats.failed_batches,
    }


def construct_judge_dataset(
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
    translation_client: TranslationClient | None = None,
    prompt_config: TranslationPromptConfig | None = None,
) -> dict[str, Any]:
    records = _load_records(input_path, limit=limit)
    output_records = [_build_judge_record(record) for record in records]

    if not translate_only and _has_neo4j_config(neo4j_uri, neo4j_user, neo4j_password):
        with Neo4jExecutor(neo4j_uri, neo4j_user, neo4j_password) as executor:
            for record in output_records:
                if record.get("noise_answer") is not None:
                    continue
                try:
                    valid_answer = clean_answer(executor.execute(record["template_query"]))
                    invalid_answer = clean_answer(executor.execute(record["anti_template_query"]))
                    record["noise_answer"] = {
                        "valid_answer": _as_judge_rows(valid_answer, True),
                        "invalid_answer": _as_judge_rows(invalid_answer, False),
                    }
                except Exception as exc:
                    record["noise_answer"] = None
                    record["error"] = str(exc)
                    if fail_fast:
                        raise

    client = translation_client or OpenAITranslationClient(
        api_key,
        base_url,
        model,
        prompt_config=prompt_config,
    )
    translations, translation_stats = translate_queries(
        [record["template_query"] for record in output_records],
        client=client,
        chunk_size=chunk_size,
        fail_fast=fail_fast,
    )
    for record, translation in zip(output_records, translations):
        record["nlp"] = translation

    _write_records(output_path, output_records)
    return {
        "total": len(output_records),
        "translation_failed_batches": translation_stats.failed_batches,
    }


def _has_neo4j_config(
    neo4j_uri: str | None,
    neo4j_user: str | None,
    neo4j_password: str | None,
) -> bool:
    return bool(neo4j_uri and neo4j_user and neo4j_password)


def _build_management_record(record: dict[str, Any]) -> dict[str, Any]:
    if "steps" in record and isinstance(record.get("steps"), list):
        return {"steps": _normalize_management_steps(record["steps"])}

    if "template" in record and "validation" in record:
        return {"steps": _build_management_steps_from_legacy_record(record)}

    return {"steps": []}


def _normalize_management_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_steps = []
    for index, step in enumerate(steps, 1):
        normalized_steps.append(
            {
                "step": step.get("step", index),
                "operate_query": step.get("operate_query", ""),
                "valid_query": step.get("valid_query", ""),
                "answer": clean_answer(step.get("answer", [])),
                "operate_nlp": step.get("operate_nlp", ""),
                "valid_nlp": step.get("valid_nlp", ""),
            }
        )
    return normalized_steps


def _build_management_steps_from_legacy_record(
    record: dict[str, Any],
) -> list[dict[str, Any]]:
    template = record.get("template", {})
    validation = record.get("validation", [])
    if not isinstance(template, dict) or not isinstance(validation, list):
        return []

    query_list = template.get("query", [])
    if not isinstance(query_list, list):
        return []

    # Legacy format uses query[0] as the initial state and validation index 0 as baseline.
    template_queries = query_list[1:] if len(query_list) > 1 else []
    validation_items = [
        item
        for item in validation
        if isinstance(item, dict) and item.get("index", -1) >= 1
    ]
    validation_items.sort(key=lambda item: item.get("index", 0))

    steps = []
    for fallback_index, validation_item in enumerate(validation_items, 1):
        validation_index = validation_item.get("index", fallback_index)
        query_index = validation_index - 1
        if not template_queries:
            continue
        if query_index >= len(template_queries):
            operate_query = template_queries[-1]
        else:
            operate_query = template_queries[query_index]

        steps.append(
            {
                "step": validation_index,
                "operate_query": operate_query,
                "valid_query": validation_item.get("query", ""),
                "answer": clean_answer(validation_item.get("answer", [])),
                "operate_nlp": "",
                "valid_nlp": "",
            }
        )
    return steps


def _build_judge_record(record: dict[str, Any]) -> dict[str, Any]:
    clean_answer_value = record.get("clean_answer")
    if clean_answer_value is None and "CandidateSet" in record:
        clean_answer_value = record["CandidateSet"]

    output_record = {
        "type": record.get("type", record.get("template_type", "")),
        "template_query": record.get("template_query", ""),
        "anti_template_query": record.get("anti_template_query", ""),
        "contains_noise": record.get("contains_noise", False),
        "clean_answer": clean_answer_value,
        "noise_answer": record.get("noise_answer"),
        "nlp": record.get("nlp", ""),
    }
    if record.get("error") is not None:
        output_record["error"] = record["error"]
    return output_record


def _as_judge_rows(answer: Any, judge: bool) -> list[dict[str, Any]]:
    if isinstance(answer, list):
        rows = answer
    else:
        rows = [answer]
    judge_rows = []
    for row in rows:
        if isinstance(row, dict):
            judge_row = row.copy()
        else:
            judge_row = {"a": row}
        judge_row["judge"] = judge
        judge_rows.append(judge_row)
    return judge_rows


def _load_records(input_path: str | Path, limit: int | None) -> list[dict[str, Any]]:
    with Path(input_path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("input JSON must contain a record or list of records")
    return data[:limit] if limit is not None else data


def _write_records(output_path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

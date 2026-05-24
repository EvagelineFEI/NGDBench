"""Answer cleaning rules for dataset construction."""

from __future__ import annotations

import json
from typing import Any


NODE_ID_KEY = "_node_id"


def clean_answer(answer: Any, node_id_key: str = NODE_ID_KEY) -> Any:
    return clean_answer_for_node_aliases(answer, node_id_key=node_id_key)


def clean_answer_for_node_aliases(
    answer: Any,
    node_id_key: str = NODE_ID_KEY,
    node_id_aliases: set[str] | None = None,
) -> Any:
    """Clean normal and aggregate query answers."""
    if not isinstance(answer, list):
        return answer
    if not answer:
        return []

    if len(answer) == 1 and isinstance(answer[0], dict):
        first = answer[0]
        if len(first) == 1:
            return _clean_value(next(iter(first.values())), node_id_key)

    if _all_single_node_rows(answer, node_id_key):
        return [next(iter(row.values()))[node_id_key] for row in answer]

    if node_id_aliases and _all_single_node_id_alias_rows(answer, node_id_aliases):
        values = [next(iter(row.values())) for row in answer]
        return values[0] if len(values) == 1 else values

    return [_clean_value(row, node_id_key) for row in answer]


def clean_judge_answers(answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve existing judge cleaning semantics."""
    cleaned_answers: list[dict[str, Any]] = []
    for answer in answers:
        if not isinstance(answer, dict):
            cleaned_answers.append(answer)
            continue

        cleaned_answer = answer.copy()
        for key in ("a", "b"):
            value = cleaned_answer.get(key)
            if isinstance(value, dict):
                cleaned_answer[key] = (
                    {NODE_ID_KEY: value[NODE_ID_KEY]} if NODE_ID_KEY in value else {}
                )

        bs = cleaned_answer.get("bs")
        if isinstance(bs, list):
            cleaned_answer["bs"] = _dedupe_keep_order(bs)[:5]

        cleaned_answers.append(cleaned_answer)
    return cleaned_answers


def clean_management_answer(answer: Any, node_id_key: str = NODE_ID_KEY) -> Any:
    """Clean management validation answers with the normal rules."""
    return clean_answer(answer, node_id_key=node_id_key)


def clean_record_answer(record: dict[str, Any], node_id_key: str = NODE_ID_KEY) -> Any:
    """Choose the appropriate answer cleaning rule for a source record."""
    if "CandidateSet" in record and isinstance(record["CandidateSet"], dict):
        return {
            "valid_answer": clean_judge_answers(
                record["CandidateSet"].get("valid_answer", [])
            ),
            "invalid_answer": clean_judge_answers(
                record["CandidateSet"].get("invalid_answer", [])
            ),
        }
    return clean_answer(record.get("answer", []), node_id_key=node_id_key)


def is_empty_answer(answer: Any) -> bool:
    return answer == [] or answer == 0


def _clean_value(value: Any, node_id_key: str) -> Any:
    if isinstance(value, dict):
        if node_id_key in value:
            return value[node_id_key]
        return {key: _clean_value(inner, node_id_key) for key, inner in value.items()}
    if isinstance(value, list):
        return [_clean_value(item, node_id_key) for item in value]
    return value


def _all_single_node_rows(rows: list[Any], node_id_key: str) -> bool:
    for row in rows:
        if not isinstance(row, dict) or len(row) != 1:
            return False
        value = next(iter(row.values()))
        if not isinstance(value, dict) or node_id_key not in value:
            return False
    return True


def _all_single_node_id_alias_rows(rows: list[Any], node_id_aliases: set[str]) -> bool:
    for row in rows:
        if not isinstance(row, dict) or len(row) != 1:
            return False
        key, value = next(iter(row.items()))
        if key not in node_id_aliases:
            return False
        if not (isinstance(value, (str, int, float, bool)) or value is None):
            return False
    return True


def _dedupe_keep_order(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    unique_values: list[Any] = []
    for value in values:
        key = (
            value
            if isinstance(value, (str, int, float, bool, type(None)))
            else json.dumps(value, sort_keys=True)
        )
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(value)
    return unique_values

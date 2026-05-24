"""Backfill MCP mention_in_nodes from offline KG extraction outputs."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .unstructured import extract_node_ids_from_answer, extract_node_ids_from_query

RELATION_FIELDS = (
    "tool_sequence_extraction_dict",
    "task_tool_context_extraction_dict",
)
NODE_KEYS = ("subject", "object")


def backfill_mcp_mention_in_nodes(
    input_path: str | Path,
    kg_extraction_dir: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    input_file = Path(input_path)
    output_file = Path(output_path) if output_path is not None else input_file
    kg_dir = Path(kg_extraction_dir)
    records = _load_query_records(input_file)
    node_to_texts = build_node_text_index(kg_dir.glob("*.json"))

    updated_records = 0
    records_with_mentions = 0
    unresolved_nodes: set[str] = set()

    for record in records:
        mention_texts, missing_nodes = build_record_mentions(record, node_to_texts)
        unresolved_nodes.update(missing_nodes)
        if record.get("mention_in_nodes") != mention_texts:
            updated_records += 1
        if mention_texts:
            records_with_mentions += 1
        record["mention_in_nodes"] = mention_texts

    _write_records(output_file, records)
    return {
        "total_records": len(records),
        "updated_records": updated_records,
        "records_with_mentions": records_with_mentions,
        "records_without_mentions": len(records) - records_with_mentions,
        "indexed_nodes": len(node_to_texts),
        "unresolved_unique_nodes": len(unresolved_nodes),
        "output_path": str(output_file),
    }


def build_node_text_index(
    paths: Iterable[str | Path],
) -> dict[str, list[str]]:
    node_to_texts: dict[str, list[str]] = {}
    for path_like in paths:
        path = Path(path_like)
        for item in _iter_json_objects(path):
            original_text = item.get("original_text")
            if not isinstance(original_text, str) or not original_text.strip():
                continue

            for relation_field in RELATION_FIELDS:
                for relation in item.get(relation_field) or []:
                    if not isinstance(relation, dict):
                        continue
                    for node_key in NODE_KEYS:
                        node_id = relation.get(node_key)
                        if not isinstance(node_id, str) or not node_id.strip():
                            continue
                        for candidate in normalize_node_id_candidates(node_id):
                            _append_unique(node_to_texts, candidate, original_text)
    return node_to_texts


def build_record_mentions(
    record: dict[str, Any],
    node_to_texts: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    mention_texts: list[str] = []
    seen_texts: set[str] = set()
    missing_nodes: list[str] = []

    existing_mentions = record.get("mention_in_nodes")
    if isinstance(existing_mentions, list):
        for text in existing_mentions:
            if isinstance(text, str) and text not in seen_texts:
                seen_texts.add(text)
                mention_texts.append(text)

    for node_id in collect_record_node_ids(record):
        texts = node_to_texts.get(node_id)
        if not texts:
            missing_nodes.append(node_id)
            continue
        for text in texts:
            if text in seen_texts:
                continue
            seen_texts.add(text)
            mention_texts.append(text)

    return mention_texts, missing_nodes


def collect_record_node_ids(record: dict[str, Any]) -> list[str]:
    node_ids: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        if not isinstance(value, str) or not value:
            return
        for candidate in normalize_node_id_candidates(value):
            if candidate in seen:
                continue
            seen.add(candidate)
            node_ids.append(candidate)

    for field in ("query_node_ids", "answer_node_ids"):
        values = record.get(field)
        if isinstance(values, list):
            for value in values:
                add(value)

    for value in sorted(extract_node_ids_from_query(record.get("query", ""))):
        add(value)
    for value in sorted(_extract_node_ids_from_query_loose(record.get("query", ""))):
        add(value)
    for value in sorted(extract_node_ids_from_answer(record.get("answer", []))):
        add(value)

    return node_ids


def normalize_node_id_candidates(node_id: str) -> list[str]:
    payload_match = re.match(r"^(.+?):\d+\{.*\}$", node_id)
    if payload_match:
        base = payload_match.group(1).strip()
        return [node_id.strip(), base] if base else [node_id.strip()]

    truncated_payload_match = re.match(r"^(.+?):\d+\{$", node_id)
    if truncated_payload_match:
        base = truncated_payload_match.group(1).strip()
        return [base] if base else []

    stripped = node_id.strip()
    return [stripped] if stripped else []


def _extract_node_ids_from_query_loose(query: str) -> set[str]:
    node_ids: set[str] = set()
    patterns = [
        r"\{[^}]*id\s*:\s*'([^']+)'",
        r'\{[^}]*id\s*:\s*"([^"]+)"',
        r"\bid\s*=\s*'([^']+)'",
        r'\bid\s*=\s*"([^"]+)"',
    ]
    for pattern in patterns:
        node_ids.update(re.findall(pattern, query))
    return node_ids


def _iter_json_objects(path: Path) -> Iterable[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(
                        f"Expected JSON object in {path} line {line_number}, got {type(item).__name__}"
                    )
                yield item
        return

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                raise ValueError(
                    f"Expected objects inside JSON array in {path}, got {type(item).__name__}"
                )
            yield item
        return

    if isinstance(data, dict):
        yield data
        return

    raise ValueError(f"Unsupported JSON structure in {path}: {type(data).__name__}")


def _load_query_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("input query file must be a JSON array")
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("input query file must contain JSON objects")
    return data


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def _append_unique(node_to_texts: dict[str, list[str]], node_id: str, text: str) -> None:
    existing = node_to_texts.setdefault(node_id, [])
    if text not in existing:
        existing.append(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill mention_in_nodes for MCP query datasets from KG extraction files.",
    )
    parser.add_argument("--input", required=True, help="Input query JSON file.")
    parser.add_argument(
        "--kg-extraction-dir",
        required=True,
        help="Directory containing KG extraction JSON/JSONL files.",
    )
    parser.add_argument(
        "--output",
        help="Output JSON file. Defaults to overwriting --input.",
    )
    args = parser.parse_args()

    stats = backfill_mcp_mention_in_nodes(
        input_path=args.input,
        kg_extraction_dir=args.kg_extraction_dir,
        output_path=args.output,
    )
    print(
        "Backfilled {total_records} records; updated {updated_records}; "
        "records_with_mentions={records_with_mentions}; "
        "records_without_mentions={records_without_mentions}; "
        "indexed_nodes={indexed_nodes}; unresolved_unique_nodes={unresolved_unique_nodes}; "
        "output={output_path}".format(**stats)
    )


if __name__ == "__main__":
    main()

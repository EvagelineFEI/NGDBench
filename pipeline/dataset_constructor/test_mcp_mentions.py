from __future__ import annotations

import json

from pipeline.dataset_constructor.mcp_mentions import (
    backfill_mcp_mention_in_nodes,
    build_node_text_index,
    build_record_mentions,
    collect_record_node_ids,
)


def test_build_node_text_index_from_jsonl(tmp_path):
    kg_path = tmp_path / "kg.json"
    kg_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "original_text": "text one",
                        "tool_sequence_extraction_dict": [
                            {"subject": "node_a", "relation": "r", "object": "node_b"},
                        ],
                        "task_tool_context_extraction_dict": [],
                    }
                ),
                json.dumps(
                    {
                        "original_text": "text two",
                        "tool_sequence_extraction_dict": [],
                        "task_tool_context_extraction_dict": [
                            {"subject": "node_b", "relation": "r", "object": "node_c"},
                        ],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    index = build_node_text_index([kg_path])

    assert index["node_a"] == ["text one"]
    assert index["node_b"] == ["text one", "text two"]
    assert index["node_c"] == ["text two"]


def test_collect_record_node_ids_falls_back_to_query_and_answer():
    record = {
        "query": "MATCH (a {id: 'node_q'}) RETURN a",
        "answer": [{"b": {"id": "node_a"}}, {"c.id": "node_c"}],
    }

    assert collect_record_node_ids(record) == ["node_q", "node_a", "node_c"]


def test_build_record_mentions_deduplicates_texts():
    record = {
        "query_node_ids": ["node_a"],
        "answer_node_ids": ["node_b"],
        "mention_in_nodes": ["existing text"],
    }
    node_to_texts = {
        "node_a": ["existing text", "source text one"],
        "node_b": ["source text one", "source text two"],
    }

    mention_texts, missing_nodes = build_record_mentions(record, node_to_texts)

    assert mention_texts == ["existing text", "source text one", "source text two"]
    assert missing_nodes == []


def test_backfill_mcp_mention_in_nodes_updates_output(tmp_path):
    input_path = tmp_path / "queries.json"
    output_path = tmp_path / "queries_filled.json"
    kg_dir = tmp_path / "kg"
    kg_dir.mkdir()

    input_path.write_text(
        json.dumps(
            [
                {
                    "query": "MATCH (a {id: 'node_q'}) RETURN a",
                    "answer": [{"b": {"id": "node_a"}}],
                    "mention_in_nodes": [],
                },
                {
                    "query_node_ids": ["node_missing"],
                    "answer_node_ids": [],
                    "mention_in_nodes": [],
                },
            ]
        ),
        encoding="utf-8",
    )
    (kg_dir / "sample.json").write_text(
        json.dumps(
            {
                "original_text": "source text",
                "tool_sequence_extraction_dict": [
                    {"subject": "node_q", "relation": "r", "object": "node_a"},
                ],
                "task_tool_context_extraction_dict": [],
            }
        ),
        encoding="utf-8",
    )

    stats = backfill_mcp_mention_in_nodes(input_path, kg_dir, output_path)
    output = json.loads(output_path.read_text(encoding="utf-8"))

    assert stats["total_records"] == 2
    assert stats["updated_records"] == 1
    assert stats["records_with_mentions"] == 1
    assert stats["records_without_mentions"] == 1
    assert stats["unresolved_unique_nodes"] == 1
    assert output[0]["mention_in_nodes"] == ["source text"]
    assert output[1]["mention_in_nodes"] == []

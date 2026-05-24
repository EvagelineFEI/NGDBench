from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.dataset_constructor.case_builders import construct_judge_dataset
from pipeline.dataset_constructor.cli import _merge_judge_translation_config
from pipeline.dataset_constructor.constructor import construct_dataset
from pipeline.dataset_constructor.translation import (
    TranslationPromptConfig,
    _build_prompt,
    translate_queries,
)
from pipeline.dataset_constructor.unstructured_answer_judge import (
    AnswerJudgePromptConfig,
    _build_judge_prompt,
    construct_unstructured_answer_judgments,
)
from pipeline.dataset_constructor.unstructured import construct_unstructured_dataset


class FakeTranslationClient:
    def translate_batch(self, queries: list[str]) -> list[str]:
        return [f"translated: {query}" for query in queries]


class FakeAnswerJudgeClient:
    def judge_batch(self, records: list[dict[str, object]]) -> list[dict[str, str]]:
        return [
            {
                "llm_label": "true",
                "gnd": "The answer correctly identifies 'loan_task_tiered_resource_pools' as the output.",
            }
            for record in records
        ]


class RetryUnknownOnlyJudgeClient:
    def __init__(self) -> None:
        self.seen_queries: list[str] = []

    def judge_batch(self, records: list[dict[str, object]]) -> list[dict[str, str]]:
        self.seen_queries.extend(str(record["query"]) for record in records)
        return [
            {
                "llm_label": "false",
                "gnd": "The correct answer should include 'workflow_task_final_summary'.",
            }
            for _ in records
        ]


class RetryLabelJudgeClient:
    def __init__(self) -> None:
        self.seen_queries: list[str] = []

    def judge_batch(self, records: list[dict[str, object]]) -> list[dict[str, str]]:
        self.seen_queries.extend(str(record["query"]) for record in records)
        return [
            {
                "llm_label": "true",
                "gnd": "The answer correctly identifies 'workflow_task_search' as the tool.",
            }
            for _ in records
        ]


class FailingSecondBatchJudgeClient:
    def __init__(self) -> None:
        self.calls = 0

    def judge_batch(self, records: list[dict[str, object]]) -> list[dict[str, str]]:
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("stop after first checkpoint")
        return [
            {
                "llm_label": "true",
                "gnd": "The answer correctly identifies 'workflow_task_search' as the tool.",
            }
            for _ in records
        ]


class FalseButMatchingGndJudgeClient:
    def judge_batch(self, records: list[dict[str, object]]) -> list[dict[str, str]]:
        return [
            {
                "llm_label": "false",
                "gnd": "list available platforms",
            }
            for _ in records
        ]


class PartialBatchTranslationClient:
    def translate_batch(self, queries: list[str]) -> list[str]:
        if len(queries) > 2:
            return [f"translated: {queries[0]}", ""]
        return [f"translated: {query}" for query in queries]


class TranslationPromptTests(unittest.TestCase):
    def test_prompt_includes_literal_preservation_hints(self) -> None:
        prompt = _build_prompt(
            [
                "CREATE (n:Loan {balance: 294985775592768095})",
                "MATCH (n:Loan {loanId: 4908360643880420273}) DETACH DELETE n",
            ]
        )

        self.assertIn("Do not invent or swap property names.", prompt)
        self.assertIn("Property names: balance", prompt)
        self.assertIn("Literal values: 294985775592768095", prompt)
        self.assertIn("Operations: CREATE", prompt)
        self.assertIn("Property names: loanId", prompt)
        self.assertIn("Operations: DETACH DELETE, MATCH, DELETE", prompt)

    def test_translate_queries_retries_when_batch_contains_blanks(self) -> None:
        translations, stats = translate_queries(
            [
                "CREATE (n:Person {isBlocked: 507})",
                "MATCH (n:Person) RETURN count(n) AS cnt",
                "CREATE (n:Person {isBlocked: 30786325578657})",
                "MATCH (n:Person {personId: 957}) DETACH DELETE n",
            ],
            client=PartialBatchTranslationClient(),
            chunk_size=4,
        )

        self.assertEqual(
            translations,
            [
                "translated: CREATE (n:Person {isBlocked: 507})",
                "translated: MATCH (n:Person) RETURN count(n) AS cnt",
                "translated: CREATE (n:Person {isBlocked: 30786325578657})",
                "translated: MATCH (n:Person {personId: 957}) DETACH DELETE n",
            ],
        )
        self.assertGreater(stats.retried_batches, 0)
        self.assertEqual(stats.failed_batches, 0)

    def test_translation_prompt_config_supports_json_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "dataset_config.json"
            config_path.write_text(
                "\n".join(
                    [
                        "{",
                        '  "system": "dataset system",',
                        '  "dataset_description": "dataset description",',
                        '  "translation_notes": [',
                        '    // translation comment',
                        '    "keep prefixes"',
                        "  ]",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            prompt_config = TranslationPromptConfig.from_path(config_path)

            self.assertEqual(prompt_config.system, "dataset system")
            self.assertIn("dataset description", prompt_config.context)
            self.assertIn("keep prefixes", prompt_config.context)

    def test_judge_kind_dataset_config_merges_judge_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "dataset_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "system": "judge dataset system",
                        "dataset_description": "judge dataset description",
                        "translation_notes": ["preserve judge query literals"],
                        "judge_notes": ["template query is paired with anti-template query"],
                    }
                ),
                encoding="utf-8",
            )

            prompt_config = TranslationPromptConfig.from_path(config_path)
            merged = _merge_judge_translation_config(
                prompt_config=prompt_config,
                config_path=str(config_path),
                prompt_key=None,
            )

            self.assertEqual(merged.system, "judge dataset system")
            self.assertIn("judge dataset description", merged.context)
            self.assertIn("preserve judge query literals", merged.context)
            self.assertIn("template query is paired with anti-template query", merged.context)


class TranslateOnlyTests(unittest.TestCase):
    def test_structured_translate_only_skips_neo4j(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "structured.json"
            output_path = Path(tmp_dir) / "structured_out.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "template_id": "T001",
                            "template_type": "basic",
                            "query": "MATCH (m:Loan) RETURN m",
                            "answer": [{"m": {"_node_id": "Loan:1", "balance": 1}}],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            stats = construct_dataset(
                input_path=input_path,
                output_path=output_path,
                neo4j_uri=None,
                neo4j_user=None,
                neo4j_password=None,
                api_key="dummy",
                base_url="http://example.com",
                model="dummy-model",
                translate_only=True,
                translation_client=FakeTranslationClient(),
            )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(stats["total"], 1)
            self.assertIsNone(data[0]["noise_answer"])
            self.assertFalse(data[0]["same_as_cleangraph"])
            self.assertTrue(data[0]["nlp"].startswith("translated:"))

    def test_unstructured_translate_only_extracts_ids_without_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "unstructured.json"
            output_path = Path(tmp_dir) / "unstructured_out.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "template_id": "U001",
                            "template_type": "chain",
                            "query": "MATCH (a:entity {id: 'loan_1'}) RETURN a",
                            "answer": [{"a": {"id": "loan_1"}}],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            stats = construct_unstructured_dataset(
                input_path=input_path,
                output_path=output_path,
                neo4j_uri=None,
                neo4j_user=None,
                neo4j_password=None,
                api_key="dummy",
                base_url="http://example.com",
                model="dummy-model",
                translate_only=True,
                translation_client=FakeTranslationClient(),
            )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(stats["total"], 1)
            self.assertEqual(data[0]["query_node_ids"], ["loan_1"])
            self.assertEqual(data[0]["answer_node_ids"], ["loan_1"])
            self.assertEqual(data[0]["mention_in_nodes"], [])
            self.assertTrue(data[0]["nlp"].startswith("translated:"))

    def test_judge_without_neo4j_skips_noise_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "judge.json"
            output_path = Path(tmp_dir) / "judge_out.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "type": "judge_case",
                            "template_query": "MATCH (n:Loan) RETURN n",
                            "anti_template_query": "MATCH (m:Loan) RETURN m",
                            "contains_noise": True,
                            "clean_answer": {"valid_answer": [], "invalid_answer": []},
                        }
                    ]
                ),
                encoding="utf-8",
            )

            stats = construct_judge_dataset(
                input_path=input_path,
                output_path=output_path,
                neo4j_uri=None,
                neo4j_user=None,
                neo4j_password=None,
                api_key="dummy",
                base_url="http://example.com",
                model="dummy-model",
                translation_client=FakeTranslationClient(),
            )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(stats["total"], 1)
            self.assertIsNone(data[0]["noise_answer"])
            self.assertTrue(data[0]["nlp"].startswith("translated:"))

    def test_answer_judge_outputs_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "judge_input.json"
            output_path = Path(tmp_dir) / "judge_output.json"
            config_path = Path(tmp_dir) / "judge_config.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "query": "MATCH (a:entity {id: 'loan_task_allocating_resources'})-[:produces_output]->(b:entity) RETURN b.id",
                            "answer": ["loan_task_tiered_resource_pools"],
                            "mention_in_nodes": ["loan task produces tiered resource pools"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            config_path.write_text(
                "\n".join(
                    [
                        "{",
                        '  "system": "judge system",',
                        '  "dataset_description": "judge description",',
                        '  "translation_notes": ["should be ignored"],',
                        '  "judge_notes": [',
                        '    // judge comment',
                        '    "use evidence only"',
                        "  ]",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            prompt_config = AnswerJudgePromptConfig.from_path(config_path)
            self.assertEqual(prompt_config.system, "judge system")
            self.assertIn("judge description", prompt_config.context)
            self.assertIn("use evidence only", prompt_config.context)
            self.assertNotIn("should be ignored", prompt_config.context)

            stats = construct_unstructured_answer_judgments(
                input_path=input_path,
                output_path=output_path,
                api_key="dummy",
                base_url="http://example.com",
                model="dummy-model",
                judge_client=FakeAnswerJudgeClient(),
                prompt_config=prompt_config,
            )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(stats["total"], 1)
            self.assertEqual(
                data[0]["query"],
                "MATCH (a:entity {id: 'loan_task_allocating_resources'})-[:produces_output]->(b:entity) RETURN b.id",
            )
            self.assertEqual(data[0]["answer"], ["loan_task_tiered_resource_pools"])
            self.assertEqual(
                data[0]["mention_in_nodes"],
                ["loan task produces tiered resource pools"],
            )
            self.assertEqual(data[0]["llm_label"], "true")
            self.assertEqual(data[0]["gnd"], "tiered resource pools")

    def test_answer_judge_retry_unknown_only_preserves_existing_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "judge_input.json"
            output_path = Path(tmp_dir) / "judge_output.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "query": "MATCH (a:entity {id: 'loan_task'}) RETURN a.id",
                            "answer": ["loan_task"],
                            "mention_in_nodes": ["loan task is the requested entity"],
                            "llm_label": "true",
                            "gnd": "The answer correctly identifies 'loan_task' as the entity.",
                        },
                        {
                            "query": "MATCH (a:entity {id: 'workflow_task_seed'})-[:produces_output]->(b:entity) RETURN b.id",
                            "answer": ["workflow_task_final_summary"],
                            "mention_in_nodes": ["workflow task produces a final summary"],
                            "llm_label": "unknown",
                            "gnd": "Cannot tell from the evidence.",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            judge_client = RetryUnknownOnlyJudgeClient()
            stats = construct_unstructured_answer_judgments(
                input_path=input_path,
                output_path=output_path,
                api_key="dummy",
                base_url="http://example.com",
                model="dummy-model",
                judge_client=judge_client,
                retry_unknown_only=True,
            )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(stats["rejudged"], 1)
            self.assertEqual(
                judge_client.seen_queries,
                ["MATCH (a:entity {id: 'workflow_task_seed'})-[:produces_output]->(b:entity) RETURN b.id"],
            )
            self.assertEqual(data[0]["llm_label"], "true")
            self.assertEqual(data[0]["gnd"], "loan task")
            self.assertEqual(data[1]["llm_label"], "false")
            self.assertEqual(data[1]["gnd"], "final summary")

    def test_answer_judge_retry_label_rejudges_only_matching_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "judge_input.json"
            output_path = Path(tmp_dir) / "judge_output.json"
            false_query = "MATCH (a:entity {id: 'workflow_task_seed'})-[:uses_tool]->(b:entity) RETURN b.id"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "query": "MATCH (a:entity {id: 'loan_task'}) RETURN a.id",
                            "answer": ["loan_task"],
                            "mention_in_nodes": ["loan task is the requested entity"],
                            "llm_label": "true",
                            "gnd": "The answer correctly identifies 'loan_task' as the entity.",
                        },
                        {
                            "query": false_query,
                            "answer": ["workflow_task_search"],
                            "mention_in_nodes": ["workflow task uses search"],
                            "llm_label": "false",
                            "gnd": "search",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            judge_client = RetryLabelJudgeClient()
            stats = construct_unstructured_answer_judgments(
                input_path=input_path,
                output_path=output_path,
                api_key="dummy",
                base_url="http://example.com",
                model="dummy-model",
                judge_client=judge_client,
                retry_labels={"false"},
            )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(stats["rejudged"], 1)
            self.assertEqual(judge_client.seen_queries, [false_query])
            self.assertEqual(data[0]["llm_label"], "true")
            self.assertEqual(data[0]["gnd"], "loan task")
            self.assertEqual(data[1]["llm_label"], "true")
            self.assertEqual(data[1]["gnd"], "search")

    def test_answer_judge_corrects_false_label_when_gnd_matches_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "judge_input.json"
            output_path = Path(tmp_dir) / "judge_output.json"
            input_path.write_text(
                json.dumps(
                    [
                        {
                            "query": "MATCH (n:entity {id: 'facebook_server_status_check_facebook'})-[:then]->(m) RETURN m.id",
                            "answer": ["list_available_platforms"],
                            "mention_in_nodes": ["Use 'status list' to see available platforms."],
                            "llm_label": "false",
                            "gnd": "list available platforms",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            stats = construct_unstructured_answer_judgments(
                input_path=input_path,
                output_path=output_path,
                api_key="dummy",
                base_url="http://example.com",
                model="dummy-model",
                judge_client=FalseButMatchingGndJudgeClient(),
                retry_labels={"false"},
            )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(stats["rejudged"], 1)
            self.assertEqual(data[0]["llm_label"], "true")
            self.assertEqual(data[0]["gnd"], "list available platforms")

    def test_answer_judge_prompt_audits_existing_gnd_against_answer(self) -> None:
        prompt = _build_judge_prompt(
            [
                {
                    "query": "MATCH (n:entity {id: 'buy_neon_threads_giftcard_bitrefill_api_server'})-[:provides_tool]->(m) RETURN m.id",
                    "answer": ["buy_neon_threads_giftcard_bitrefill_api_search"],
                    "existing_gnd": "search",
                    "existing_llm_label": "false",
                    "mention_in_nodes": ["assistant searched Bitrefill for Neon Threads"],
                }
            ]
        )

        self.assertIn('"existing_gnd": "search"', prompt)
        self.assertIn('"existing_llm_label": "false"', prompt)
        self.assertIn("First compare existing_gnd with answer semantically.", prompt)
        self.assertIn(
            "Treat existing_gnd as correct when it is essentially the same answer as answer",
            prompt,
        )
        self.assertIn("Existing labels may be wrong", prompt)

    def test_answer_judge_prompt_requires_all_multi_item_answer_parts(self) -> None:
        prompt = _build_judge_prompt(
            [
                {
                    "query": "MATCH (a:entity {id: 'skybuilder96_creator_profile_no_results_found_varied'})-[:produces_output *1..3]-(b:entity) RETURN a.id, b.id",
                    "answer": [
                        "skybuilder96_creator_profile_no_results_found_varied",
                        "skybuilder96_creator_profile_varied_keyword_search",
                    ],
                    "existing_gnd": "varied keyword search",
                    "existing_llm_label": "false",
                    "mention_in_nodes": ["assistant tried varied keyword search after no profile results"],
                }
            ]
        )

        self.assertIn("RETURN a.id, b.id", prompt)
        self.assertIn("judge all of them", prompt)
        self.assertIn("covers every required item in answer", prompt)
        self.assertIn("Do not collapse a multi-item answer into one phrase", prompt)
        self.assertIn("gnd\" must include all required items from answer", prompt)

    def test_answer_judge_writes_checkpoint_after_each_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "judge_input.json"
            output_path = Path(tmp_dir) / "judge_output.json"
            records = [
                {
                    "query": f"MATCH (a:entity {{id: 'workflow_task_seed_{index}'}})-[:uses_tool]->(b:entity) RETURN b.id",
                    "answer": ["workflow_task_search"],
                    "mention_in_nodes": ["workflow task uses search"],
                    "llm_label": "false",
                    "gnd": "search",
                }
                for index in range(2)
            ]
            input_path.write_text(json.dumps(records), encoding="utf-8")

            with self.assertRaises(RuntimeError, msg="stop after first checkpoint"):
                construct_unstructured_answer_judgments(
                    input_path=input_path,
                    output_path=output_path,
                    api_key="dummy",
                    base_url="http://example.com",
                    model="dummy-model",
                    judge_client=FailingSecondBatchJudgeClient(),
                    retry_labels={"false"},
                    chunk_size=1,
                    fail_fast=True,
                )

            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["llm_label"], "true")
            self.assertEqual(data[0]["gnd"], "search")
            self.assertEqual(data[1]["llm_label"], "false")
            self.assertEqual(data[1]["gnd"], "search")


if __name__ == "__main__":
    unittest.main()

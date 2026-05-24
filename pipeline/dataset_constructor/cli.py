"""Command line interface for dataset construction."""

from __future__ import annotations

import argparse
import sys

from .case_builders import construct_judge_dataset, construct_management_dataset
from .constructor import construct_dataset
from .mcp_mentions import backfill_mcp_mention_in_nodes
from .translation import TranslationPromptConfig
from .unstructured_answer_judge import (
    AnswerJudgePromptConfig,
    construct_unstructured_answer_judgments,
)
from .unstructured import construct_unstructured_dataset


SUBCOMMANDS = {"build", "mcp-mentions", "answer-judge"}


def _add_build_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--kind",
        choices=["structured", "unstructured", "management", "judge"],
        default="structured",
        help="Dataset construction mode.",
    )
    parser.add_argument("--input", required=True, help="Clean graph query result JSON")
    parser.add_argument("--output", required=True, help="Output dataset JSON path")
    parser.add_argument("--neo4j-uri")
    parser.add_argument("--neo4j-user")
    parser.add_argument("--neo4j-password")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--dataset-config",
        help="Optional JSON file describing dataset-specific translation context.",
    )
    parser.add_argument(
        "--dataset-context",
        help="Optional one-line dataset-specific translation hint.",
    )
    parser.add_argument(
        "--prompt-config",
        help="Deprecated alias of --dataset-config.",
    )
    parser.add_argument(
        "--prompt-key",
        help="Optional dotted path inside the dataset config JSON.",
    )
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument(
        "--translate-only",
        action="store_true",
        help="Translate and build output structure without executing Neo4j queries.",
    )
    parser.add_argument("--skip-empty-answer", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--keep-template-id",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep template_id in output records.",
    )


def _build_legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Construct an NGDB dataset JSON.")
    _add_build_arguments(parser)
    return parser


def _build_subcommand_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Construct and post-process NGDB datasets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build",
        help="Construct structured, unstructured, management, or judge datasets.",
    )
    _add_build_arguments(build_parser)

    mentions_parser = subparsers.add_parser(
        "mcp-mentions",
        help="Backfill mention_in_nodes for MCP datasets from KG extraction files.",
    )
    mentions_parser.add_argument("--input", required=True, help="Input dataset JSON file.")
    mentions_parser.add_argument("--output", required=True, help="Output dataset JSON file.")
    mentions_parser.add_argument(
        "--kg-extraction-dir",
        required=True,
        help="Directory containing MCP KG extraction JSON/JSONL files.",
    )

    answer_judge_parser = subparsers.add_parser(
        "answer-judge",
        help="Use an LLM to judge unstructured-query answers from mention evidence.",
    )
    answer_judge_parser.add_argument("--input", required=True, help="Input dataset JSON file.")
    answer_judge_parser.add_argument("--output", required=True, help="Output dataset JSON file.")
    answer_judge_parser.add_argument("--api-key", required=True)
    answer_judge_parser.add_argument("--base-url", required=True)
    answer_judge_parser.add_argument("--model", required=True)
    answer_judge_parser.add_argument(
        "--dataset-config",
        help="Optional JSON file describing dataset-specific judge context.",
    )
    answer_judge_parser.add_argument(
        "--prompt-key",
        help="Optional dotted path inside the dataset config JSON.",
    )
    answer_judge_parser.add_argument("--chunk-size", type=int, default=5)
    answer_judge_parser.add_argument("--fail-fast", action="store_true")
    answer_judge_parser.add_argument("--limit", type=int)
    answer_judge_parser.add_argument(
        "--retry-unknown-only",
        action="store_true",
        help="Only rejudge records whose existing llm_label is unknown or blank.",
    )
    answer_judge_parser.add_argument(
        "--retry-label",
        action="append",
        choices=["true", "false", "incomplete", "unknown"],
        help=(
            "Only rejudge records with this existing llm_label. "
            "Can be passed multiple times; overrides --retry-unknown-only."
        ),
    )
    return parser


def _run_build(args: argparse.Namespace) -> None:

    if args.kind in {"structured", "unstructured"} and not args.translate_only:
        missing = [
            name
            for name in ("neo4j_uri", "neo4j_user", "neo4j_password")
            if not getattr(args, name)
        ]
        if missing:
            raise SystemExit(
                "--neo4j-uri, --neo4j-user, and --neo4j-password are required "
                f"for {args.kind} datasets"
            )

    prompt_config_path = args.dataset_config or args.prompt_config
    prompt_config = TranslationPromptConfig.from_path(
        prompt_config_path,
        prompt_key=args.prompt_key,
    )
    if args.kind == "judge":
        prompt_config = _merge_judge_translation_config(
            prompt_config=prompt_config,
            config_path=prompt_config_path,
            prompt_key=args.prompt_key,
        )
    if args.dataset_context:
        prompt_config.context = "\n".join(
            part for part in [prompt_config.context, args.dataset_context.strip()] if part
        )

    kwargs = {
        "input_path": args.input,
        "output_path": args.output,
        "api_key": args.api_key,
        "base_url": args.base_url,
        "model": args.model,
        "chunk_size": args.chunk_size,
        "fail_fast": args.fail_fast,
        "translate_only": args.translate_only,
        "limit": args.limit,
        "prompt_config": prompt_config,
    }
    if args.kind in {"structured", "unstructured", "judge"}:
        kwargs.update(
            {
                "neo4j_uri": args.neo4j_uri,
                "neo4j_user": args.neo4j_user,
                "neo4j_password": args.neo4j_password,
            }
        )
    if args.kind in {"structured", "unstructured"}:
        kwargs["keep_template_id"] = args.keep_template_id
    if args.kind == "structured":
        kwargs["skip_empty_answer"] = args.skip_empty_answer
        constructor = construct_dataset
    elif args.kind == "unstructured":
        constructor = construct_unstructured_dataset
    elif args.kind == "management":
        constructor = construct_management_dataset
    else:
        constructor = construct_judge_dataset
    stats = constructor(**kwargs)
    print(f"Constructed {stats['total']} records at {args.output}")
    if stats["translation_failed_batches"]:
        print(f"Translation failed batches: {stats['translation_failed_batches']}")


def _merge_judge_translation_config(
    prompt_config: TranslationPromptConfig,
    config_path: str | None,
    prompt_key: str | None,
) -> TranslationPromptConfig:
    if config_path is None:
        return prompt_config

    judge_prompt_config = AnswerJudgePromptConfig.from_path(
        config_path,
        prompt_key=prompt_key,
    )
    context = "\n".join(
        part for part in [prompt_config.context, judge_prompt_config.context] if part
    )
    system = prompt_config.system or judge_prompt_config.system
    return TranslationPromptConfig(system=system, context=context)


def _run_mcp_mentions(args: argparse.Namespace) -> None:
    stats = backfill_mcp_mention_in_nodes(
        input_path=args.input,
        output_path=args.output,
        kg_extraction_dir=args.kg_extraction_dir,
    )
    print(
        "Backfilled {total_records} records at {output_path}; "
        "updated={updated_records}; records_with_mentions={records_with_mentions}; "
        "records_without_mentions={records_without_mentions}; "
        "indexed_nodes={indexed_nodes}; unresolved_unique_nodes={unresolved_unique_nodes}".format(
            **stats
        )
    )


def _run_answer_judge(args: argparse.Namespace) -> None:
    prompt_config = AnswerJudgePromptConfig.from_path(
        args.dataset_config,
        prompt_key=args.prompt_key,
    )
    stats = construct_unstructured_answer_judgments(
        input_path=args.input,
        output_path=args.output,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        chunk_size=args.chunk_size,
        fail_fast=args.fail_fast,
        limit=args.limit,
        prompt_config=prompt_config,
        retry_unknown_only=args.retry_unknown_only,
        retry_labels=set(args.retry_label or []),
    )
    print(f"Judged {stats['total']} records at {args.output}")
    if args.retry_label:
        labels = ", ".join(args.retry_label)
        print(f"Rejudged {stats['rejudged']} records with llm_label in {{{labels}}}")
    elif args.retry_unknown_only:
        print(f"Rejudged {stats['rejudged']} unknown-or-blank records")
    if stats["judge_failed_batches"]:
        print(f"Judge failed batches: {stats['judge_failed_batches']}")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in SUBCOMMANDS:
        parser = _build_subcommand_parser()
        args = parser.parse_args(argv)
        if args.command == "build":
            _run_build(args)
            return
        if args.command == "mcp-mentions":
            _run_mcp_mentions(args)
            return
        _run_answer_judge(args)
        return

    parser = _build_legacy_parser()
    args = parser.parse_args(argv)
    _run_build(args)


if __name__ == "__main__":
    main()

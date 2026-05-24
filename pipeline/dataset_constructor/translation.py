"""OpenAI-compatible Cypher-to-English translation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .dataset_config_loader import load_dataset_config


class TranslationClient(Protocol):
    def translate_batch(self, queries: list[str]) -> list[str]:
        ...


@dataclass
class TranslationStats:
    attempted: int = 0
    failed_batches: int = 0
    retried_batches: int = 0


@dataclass
class TranslationPromptConfig:
    system: str = ""
    context: str = ""

    @classmethod
    def from_path(
        cls,
        path: str | Path | None,
        prompt_key: str | None = None,
    ) -> "TranslationPromptConfig":
        if path is None:
            return cls()

        raw = load_dataset_config(path)
        selected = _select_prompt_section(raw, prompt_key)
        if isinstance(selected, str):
            return cls(context=selected.strip())

        if not isinstance(selected, dict):
            raise ValueError("prompt config must resolve to a JSON object or string")

        normalized = _normalize_prompt_object(selected)
        if normalized is not None:
            return normalized

        implicit_section = _unwrap_single_section(selected)
        if implicit_section is not None:
            normalized = _normalize_prompt_object(implicit_section)
            if normalized is not None:
                return normalized
        raise ValueError(
            "prompt config does not contain supported translation context fields"
        )


class OpenAITranslationClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        prompt_config: TranslationPromptConfig | None = None,
    ):
        if not api_key or not base_url or not model:
            raise ValueError("api_key, base_url, and model are required")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai is required for translation. Install project dependencies first."
            ) from exc

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.prompt_config = prompt_config or TranslationPromptConfig()

    def translate_batch(self, queries: list[str]) -> list[str]:
        if not queries:
            return []

        prompt = _build_prompt(queries, self.prompt_config)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": _build_system_prompt(self.prompt_config),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return _parse_lines(content, len(queries))


def translate_queries(
    queries: list[str],
    client: TranslationClient,
    chunk_size: int = 50,
    fail_fast: bool = False,
) -> tuple[list[str], TranslationStats]:
    stats = TranslationStats()
    translations: list[str] = []

    for start in range(0, len(queries), chunk_size):
        chunk = queries[start : start + chunk_size]
        stats.attempted += len(chunk)
        translations.extend(
            _translate_chunk_with_fallback(
                chunk,
                client=client,
                stats=stats,
                fail_fast=fail_fast,
            )
        )

    return translations, stats


def _translate_chunk_with_fallback(
    queries: list[str],
    client: TranslationClient,
    stats: TranslationStats,
    fail_fast: bool,
) -> list[str]:
    try:
        translations = client.translate_batch(queries)
        if _has_missing_translations(translations, len(queries)):
            raise ValueError("translation batch returned blank or incomplete results")
        return translations
    except Exception:
        if len(queries) == 1:
            stats.failed_batches += 1
            if fail_fast:
                raise
            return [""]

        stats.retried_batches += 1
        midpoint = len(queries) // 2
        left = _translate_chunk_with_fallback(
            queries[:midpoint],
            client=client,
            stats=stats,
            fail_fast=fail_fast,
        )
        right = _translate_chunk_with_fallback(
            queries[midpoint:],
            client=client,
            stats=stats,
            fail_fast=fail_fast,
        )
        return left + right


def _has_missing_translations(translations: list[str], expected_count: int) -> bool:
    if len(translations) != expected_count:
        return True
    return any(not translation.strip() for translation in translations)


def _build_prompt(
    queries: list[str],
    prompt_config: TranslationPromptConfig | None = None,
) -> str:
    prompt_config = prompt_config or TranslationPromptConfig()
    lines = [
        "Task: Write ONE concise English natural-language description for each Cypher query.",
        "Key rules:",
        "- Preserve all numeric, date, time, LIMIT, SKIP, slice, count, and threshold literals.",
        "- Preserve property names, labels, relationship types, string ids, and large integer ids exactly as written when they constrain the query.",
        "- Do not replace explicit literals with vague phrases like 'specific value', 'specified balance', or 'a node'.",
        "- Do not invent or swap property names. For example, if the query uses `balance`, do not say `loanId` or `loanUsage`.",
        "- When min() or max() is applied to strings, interpret it as lexicographic ordering.",
        "- Return exactly one translation per query, in order, one per line.",
        "- Do not include explanations, numbering, prefixes, or metadata.",
        "",
    ]
    if prompt_config.context:
        lines.append("Dataset-specific context:")
        lines.append(prompt_config.context.strip())
        lines.append("")
    for index, query in enumerate(queries, 1):
        lines.append(f"Query {index}:")
        lines.append(query)
        preservation_hint = _build_preservation_hint(query)
        if preservation_hint:
            lines.append("Must preserve in translation:")
            lines.extend(f"- {item}" for item in preservation_hint)
        lines.append("")
    return "\n".join(lines)


def _parse_lines(content: str, expected_count: int) -> list[str]:
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(
            r"^(\d+[\.\)、]?\s*|Query\s*\d+[:：]?\s*)",
            "",
            line,
            flags=re.IGNORECASE,
        )
        if line:
            lines.append(line)
    while len(lines) < expected_count:
        lines.append("")
    return lines[:expected_count]


def _build_system_prompt(prompt_config: TranslationPromptConfig) -> str:
    base = (
        "You are a professional database query analysis expert. Respond in English. "
        "You must preserve the exact semantics of Cypher queries and keep critical identifiers and literals verbatim."
    )
    if not prompt_config.system:
        return base
    return f"{base}\n\nDataset background:\n{prompt_config.system.strip()}"


def _build_preservation_hint(query: str) -> list[str]:
    hints: list[str] = []

    labels = _extract_node_labels(query)
    if labels:
        hints.append(f"Node labels: {', '.join(labels)}")

    relationship_types = _extract_relationship_types(query)
    if relationship_types:
        hints.append(f"Relationship types: {', '.join(relationship_types)}")

    properties = _extract_property_names(query)
    if properties:
        hints.append(f"Property names: {', '.join(properties)}")

    literals = _extract_literals(query)
    if literals:
        hints.append(f"Literal values: {', '.join(literals)}")

    operations = _extract_operations(query)
    if operations:
        hints.append(f"Operations: {', '.join(operations)}")

    return hints


def _extract_node_labels(query: str) -> list[str]:
    labels = re.findall(r"\([^)]+:([A-Za-z_][A-Za-z0-9_]*)", query)
    return _unique_preserve_order(labels)


def _extract_relationship_types(query: str) -> list[str]:
    rel_types = re.findall(r"\[:\s*([A-Za-z_][A-Za-z0-9_]*)", query)
    return _unique_preserve_order(rel_types)


def _extract_property_names(query: str) -> list[str]:
    candidates: list[str] = []
    for block in re.findall(r"\{([^{}]+)\}", query):
        candidates.extend(re.findall(r"([A-Za-z_][A-Za-z0-9_.]*)\s*:", block))
    candidates.extend(
        re.findall(
            r"\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|<>|!=|<=|>=|<|>|IN\b|CONTAINS\b|STARTS\s+WITH\b|ENDS\s+WITH\b)",
            query,
            flags=re.IGNORECASE,
        )
    )
    return _unique_preserve_order(candidates)


def _extract_literals(query: str) -> list[str]:
    string_literals = re.findall(r"'([^']*)'|\"([^\"]*)\"", query)
    strings = [f"'{left or right}'" for left, right in string_literals if (left or right)]
    numbers = re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])", query)
    return _unique_preserve_order(strings + numbers)


def _extract_operations(query: str) -> list[str]:
    operations: list[str] = []
    normalized = query.upper()
    for candidate in (
        "DETACH DELETE",
        "CREATE",
        "MERGE",
        "MATCH",
        "DELETE",
        "SET",
        "REMOVE",
        "RETURN",
        "ORDER BY",
        "LIMIT",
        "SKIP",
    ):
        if candidate in normalized:
            operations.append(candidate)
    return operations


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        ordered.append(stripped)
    return ordered


def _select_prompt_section(raw: object, prompt_key: str | None) -> object:
    if prompt_key is None:
        return raw

    current = raw
    for part in prompt_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"prompt key not found: {prompt_key}")
        current = current[part]
    return current


def _normalize_prompt_object(raw: dict[str, object]) -> TranslationPromptConfig | None:
    system = _first_string(raw, ["system", "system_prompt", "translation_system"])
    context_parts = [
        _first_string(
            raw,
            [
                "context",
                "translation",
                "translation_prompt",
                "query_translation",
                "dataset_description",
                "dataset_context",
            ],
        )
    ]
    context_parts.extend(_normalize_text_list(raw.get("translation_notes")))
    context_parts.extend(_normalize_text_list(raw.get("instructions")))
    context_parts.extend(_normalize_text_list(raw.get("notes")))
    context_parts.extend(_normalize_prefix_rules(raw.get("node_prefix_rules")))
    context_parts.extend(_normalize_prefix_rules(raw.get("prefix_rules")))
    context_parts.extend(_normalize_text_list(raw.get("examples")))
    context = "\n".join(part for part in context_parts if part)
    if system or context:
        return TranslationPromptConfig(system=system, context=context)
    return None


def _unwrap_single_section(raw: dict[str, object]) -> dict[str, object] | None:
    if len(raw) != 1:
        return None
    value = next(iter(raw.values()))
    if not isinstance(value, dict):
        return None
    return value


def _first_string(raw: dict[str, object], keys: list[str]) -> str:
    for key in keys:
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            strings = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            if strings:
                return "\n".join(strings)
    return ""


def _normalize_text_list(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        stripped = raw.strip()
        return [stripped] if stripped else []
    if isinstance(raw, list):
        strings = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                strings.append(item.strip())
        return strings
    return []


def _normalize_prefix_rules(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        rules = []
        for prefix, meaning in raw.items():
            if isinstance(meaning, str) and meaning.strip():
                rules.append(f"Prefix `{prefix}` means {meaning.strip()}")
        return rules
    if isinstance(raw, list):
        rules = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                rules.append(item.strip())
            elif isinstance(item, dict):
                prefix = item.get("prefix")
                meaning = item.get("meaning")
                if isinstance(prefix, str) and isinstance(meaning, str):
                    rules.append(f"Prefix `{prefix}` means {meaning.strip()}")
        return rules
    return []

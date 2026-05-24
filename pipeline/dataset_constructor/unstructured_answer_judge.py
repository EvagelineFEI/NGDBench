"""LLM-based validation for unstructured-query answers."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .dataset_config_loader import load_dataset_config


class AnswerJudgeClient(Protocol):
    def judge_batch(self, records: list[dict[str, Any]]) -> list[dict[str, str]]:
        ...


VALID_JUDGE_LABELS = {"true", "false", "incomplete", "unknown"}


@dataclass
class AnswerJudgeStats:
    attempted: int = 0
    failed_batches: int = 0
    retried_batches: int = 0


@dataclass
class AnswerJudgePromptConfig:
    system: str = ""
    context: str = ""

    @classmethod
    def from_path(
        cls,
        path: str | Path | None,
        prompt_key: str | None = None,
    ) -> "AnswerJudgePromptConfig":
        if path is None:
            return cls()

        raw = load_dataset_config(path)
        selected = _select_prompt_section(raw, prompt_key)
        if isinstance(selected, str):
            return cls(context=selected.strip())

        if not isinstance(selected, dict):
            raise ValueError("prompt config must resolve to a JSON object or string")

        normalized = _normalize_judge_prompt_object(selected)
        if normalized is not None:
            return normalized

        implicit_section = _unwrap_single_section(selected)
        if implicit_section is None:
            raise ValueError("prompt config does not contain supported judge context fields")

        normalized = _normalize_judge_prompt_object(implicit_section)
        if normalized is None:
            raise ValueError("prompt config does not contain supported judge context fields")
        return normalized


class OpenAIAnswerJudgeClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        prompt_config: AnswerJudgePromptConfig | None = None,
    ):
        if not api_key or not base_url or not model:
            raise ValueError("api_key, base_url, and model are required")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai is required for answer judging. Install project dependencies first."
            ) from exc

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.prompt_config = prompt_config or AnswerJudgePromptConfig()

    def judge_batch(self, records: list[dict[str, Any]]) -> list[dict[str, str]]:
        if not records:
            return []

        prompt = _build_judge_prompt(records, self.prompt_config)
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
        return _parse_judge_results(content, len(records))


def construct_unstructured_answer_judgments(
    input_path: str | Path,
    output_path: str | Path,
    api_key: str,
    base_url: str,
    model: str,
    chunk_size: int = 5,
    fail_fast: bool = False,
    limit: int | None = None,
    judge_client: AnswerJudgeClient | None = None,
    prompt_config: AnswerJudgePromptConfig | None = None,
    retry_unknown_only: bool = False,
    retry_labels: set[str] | None = None,
) -> dict[str, Any]:
    records = _load_records(input_path, limit=limit)
    output_records = [_build_output_record(record) for record in records]
    judge_indices = [
        index
        for index, record in enumerate(records)
        if _should_judge_record(
            record,
            retry_unknown_only=retry_unknown_only,
            retry_labels=retry_labels,
        )
    ]

    judge_stats = AnswerJudgeStats()
    _normalize_preserved_records(output_records, records, set(judge_indices))
    _write_records(output_path, output_records)

    if judge_indices:
        client = judge_client or OpenAIAnswerJudgeClient(
            api_key,
            base_url,
            model,
            prompt_config=prompt_config,
        )
        judge_stats = _judge_and_checkpoint_records(
            records=records,
            output_records=output_records,
            judge_indices=judge_indices,
            output_path=output_path,
            client=client,
            chunk_size=chunk_size,
            fail_fast=fail_fast,
        )
    return {
        "total": len(output_records),
        "judge_failed_batches": judge_stats.failed_batches,
        "rejudged": len(judge_indices),
    }


def _normalize_preserved_records(
    output_records: list[dict[str, Any]],
    source_records: list[dict[str, Any]],
    judge_indices: set[int],
) -> None:
    for index, record in enumerate(output_records):
        source_record = source_records[index]
        if index not in judge_indices:
            record["llm_label"] = _normalize_label(source_record.get("llm_label"))
            record["gnd"] = str(source_record.get("gnd", "")).strip()
        _normalize_output_record_gnd(record, correct_false_label=False)


def _judge_and_checkpoint_records(
    records: list[dict[str, Any]],
    output_records: list[dict[str, Any]],
    judge_indices: list[int],
    output_path: str | Path,
    client: AnswerJudgeClient,
    chunk_size: int,
    fail_fast: bool,
) -> AnswerJudgeStats:
    stats = AnswerJudgeStats()
    for start in range(0, len(judge_indices), chunk_size):
        chunk_indices = judge_indices[start : start + chunk_size]
        chunk = [_build_judge_input(records[index]) for index in chunk_indices]
        stats.attempted += len(chunk)
        judgments = _judge_chunk_with_fallback(
            chunk,
            client=client,
            stats=stats,
            fail_fast=fail_fast,
        )
        for index, judgment in zip(chunk_indices, judgments):
            output_records[index]["llm_label"] = _normalize_label(judgment.get("llm_label"))
            output_records[index]["gnd"] = str(judgment.get("gnd", "")).strip()
            _normalize_output_record_gnd(output_records[index], correct_false_label=True)
        _write_records(output_path, output_records)
    return stats


def _normalize_output_record_gnd(
    record: dict[str, Any],
    correct_false_label: bool = False,
) -> None:
    if correct_false_label and _is_false_label_with_matching_gnd(
        query=record.get("query", ""),
        answer=record.get("answer"),
        raw_gnd=record.get("gnd", ""),
        label=record.get("llm_label", ""),
    ):
        record["llm_label"] = "true"
    record["gnd"] = _normalize_gnd(
        query=record.get("query", ""),
        answer=record.get("answer"),
        label=record.get("llm_label", ""),
        raw_gnd=record.get("gnd", ""),
    )


def judge_unstructured_answers(
    records: list[dict[str, Any]],
    client: AnswerJudgeClient,
    chunk_size: int = 5,
    fail_fast: bool = False,
) -> tuple[list[dict[str, str]], AnswerJudgeStats]:
    stats = AnswerJudgeStats()
    judgments: list[dict[str, str]] = []

    for start in range(0, len(records), chunk_size):
        chunk = records[start : start + chunk_size]
        stats.attempted += len(chunk)
        judgments.extend(
            _judge_chunk_with_fallback(
                chunk,
                client=client,
                stats=stats,
                fail_fast=fail_fast,
            )
        )

    return judgments, stats


def _judge_chunk_with_fallback(
    records: list[dict[str, Any]],
    client: AnswerJudgeClient,
    stats: AnswerJudgeStats,
    fail_fast: bool,
) -> list[dict[str, str]]:
    try:
        judgments = client.judge_batch(records)
        if _has_missing_judgments(judgments, len(records)):
            raise ValueError("judge batch returned blank or incomplete results")
        return judgments
    except Exception as exc:
        if len(records) == 1:
            stats.failed_batches += 1
            if fail_fast:
                raise
            return [{"llm_label": "unknown", "gnd": f"judge_error: {exc}"}]

        stats.retried_batches += 1
        midpoint = len(records) // 2
        left = _judge_chunk_with_fallback(
            records[:midpoint],
            client=client,
            stats=stats,
            fail_fast=fail_fast,
        )
        right = _judge_chunk_with_fallback(
            records[midpoint:],
            client=client,
            stats=stats,
            fail_fast=fail_fast,
        )
        return left + right


def _has_missing_judgments(judgments: list[dict[str, str]], expected_count: int) -> bool:
    if len(judgments) != expected_count:
        return True
    for judgment in judgments:
        label = judgment.get("llm_label", "").strip()
        gnd = judgment.get("gnd", "").strip()
        if not label or not gnd:
            return True
    return False


def _build_output_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": record.get("query", ""),
        "gnd": str(record.get("gnd", "")).strip(),
        "llm_label": _normalize_label(record.get("llm_label")),
        "mention_in_nodes": _as_string_list(record.get("mention_in_nodes")),
        "answer": record.get("answer"),
    }


def _build_judge_input(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": record.get("query", ""),
        "answer": record.get("answer"),
        "existing_gnd": str(record.get("gnd", "")).strip(),
        "existing_llm_label": _normalize_label(record.get("llm_label")),
        "mention_in_nodes": _as_string_list(record.get("mention_in_nodes")),
    }


def _build_judge_prompt(
    records: list[dict[str, Any]],
    prompt_config: AnswerJudgePromptConfig | None = None,
) -> str:
    prompt_config = prompt_config or AnswerJudgePromptConfig()
    payload = [
        {
            "query": record.get("query", ""),
            "answer": record.get("answer"),
            "existing_gnd": str(record.get("existing_gnd", "")).strip(),
            "existing_llm_label": _normalize_label(record.get("existing_llm_label")),
            "mention_in_nodes": _as_string_list(record.get("mention_in_nodes")),
        }
        for record in records
    ]

    lines = [
        "Task: Audit each existing answer judgment and correct mislabeled records.",
        "Evidence policy:",
        "- Use the query, answer, existing_gnd, existing_llm_label, and mention_in_nodes as the only evidence.",
        "- Do not rely on outside knowledge.",
        "- First compare existing_gnd with answer semantically.",
        "- Treat existing_gnd as correct when it is essentially the same answer as answer, even if one is a concise phrase and the other is a task-prefixed entity id.",
        "- Treat existing_gnd as acceptable when it is less verbose than answer but still names the same tool, entity, action, or returned value required by the query.",
        "- If the query returns multiple columns or paths, such as RETURN a.id, b.id, answer may contain multiple required items; judge all of them.",
        "- In multi-item answers, existing_gnd is correct only if it covers every required item in answer, either explicitly or with clear semantic equivalents.",
        "- Do not collapse a multi-item answer into one phrase when the query asks for multiple returned ids or values.",
        "- Then understand the query intent and check whether answer is supported by mention_in_nodes.",
        "- Infer graph relationships from the described tool sequence, tool outputs, and assistant reasoning when they clearly imply the answer.",
        "- Do not require the exact entity id string to appear verbatim when the mentioned action or output clearly refers to the same node.",
        "- Existing labels may be wrong; do not preserve an existing false label when existing_gnd and answer are semantically aligned and answer is supported.",
        "Labels:",
        '- Use "true" when answer is fully supported and existing_gnd is semantically the same answer or an acceptable concise form for every required answer item.',
        '- Use "false" only when answer is contradicted by the evidence or existing_gnd points to a different answer.',
        # '- Use "incomplete" when answer is partially correct but missing required content, or existing_gnd captures only part of a multi-part answer.',
        # '- Use "unknown" only when the evidence genuinely cannot determine the answer.',
        "Output rules:",
        '- Return strict JSON only.',
        '- Return a JSON array in the same order as the input records.',
        '- Each item must be an object with exactly two string fields: "llm_label" and "gnd".',
        '- For "true" and "false", "gnd" must be the shortest correct answer phrase, not an explanation sentence.',
        '- For multi-item answers, "gnd" must include all required items from answer in a concise form, not just the item that differs from the query seed.',
        '- Example: if query returns a.id and b.id, and answer has two entity ids, true-label gnd should include both semantic answer items.',
        '- Prefer human-readable phrases like "tiered resource pools" instead of validator prose or full task-prefixed ids.',
        # '- For "incomplete", keep gnd brief and state what supported answer is present plus that more may be required.',
        # '- If evidence is insufficient, say briefly what cannot be determined.',
        "",
    ]
    if prompt_config.context:
        lines.append("Dataset-specific context:")
        lines.append(prompt_config.context.strip())
        lines.append("")
    lines.append("Input records:")
    lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def _build_system_prompt(prompt_config: AnswerJudgePromptConfig) -> str:
    base = (
        "You are a careful graph-query answer validator. "
        "Judge answer correctness conservatively and return strict JSON."
    )
    if not prompt_config.system:
        return base
    return f"{base}\n\nDataset background:\n{prompt_config.system.strip()}"


def _parse_judge_results(content: str, expected_count: int) -> list[dict[str, str]]:
    parsed = _parse_json_payload(content)
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise ValueError("judge response must be a JSON object or array")

    results: list[dict[str, str]] = []
    for item in parsed[:expected_count]:
        if not isinstance(item, dict):
            raise ValueError("judge response items must be objects")
        label = str(item.get("llm_label", "")).strip().lower()
        gnd = str(item.get("gnd", "")).strip()
        results.append({"llm_label": label, "gnd": gnd})
    return results


def _should_judge_record(
    record: dict[str, Any],
    retry_unknown_only: bool,
    retry_labels: set[str] | None = None,
) -> bool:
    normalized_retry_labels = {
        _normalize_label(label) for label in (retry_labels or set()) if str(label).strip()
    }
    if normalized_retry_labels:
        label = _normalize_label(record.get("llm_label"))
        return label in normalized_retry_labels
    if not retry_unknown_only:
        return True
    label = _normalize_label(record.get("llm_label"))
    return label in {"", "unknown"}


def _normalize_label(value: Any) -> str:
    label = str(value or "").strip().lower()
    return label if label in VALID_JUDGE_LABELS else label


def _normalize_gnd(query: str, answer: Any, label: str, raw_gnd: str) -> str:
    label = _normalize_label(label)
    stripped = str(raw_gnd or "").strip()

    if label in {"true", "false"}:
        quoted_entities = _extract_quoted_entities(stripped)
        concise_entities = _filter_query_entities(quoted_entities, query)
        if concise_entities:
            return _join_phrases(_humanize_entities(concise_entities, query))
        if label == "true":
            answer_entities = _extract_answer_entities(answer)
            concise_answer_entities = _filter_query_entities(answer_entities, query)
            if concise_answer_entities:
                return _join_phrases(_humanize_entities(concise_answer_entities, query))

    if label == "incomplete":
        quoted_entities = _filter_query_entities(_extract_quoted_entities(stripped), query)
        if quoted_entities:
            return f"{_join_phrases(_humanize_entities(quoted_entities, query))}; may be incomplete."
        return "Partially supported, but may be incomplete."

    if label == "unknown":
        return "Cannot be determined from the available evidence."

    return stripped


def _is_false_label_with_matching_gnd(
    query: str,
    answer: Any,
    raw_gnd: str,
    label: str,
) -> bool:
    if _normalize_label(label) != "false":
        return False

    answer_entities = _filter_query_entities(_extract_answer_entities(answer), query)
    if not answer_entities:
        return False

    if _looks_like_validator_prose(raw_gnd):
        return False

    answer_phrases = _humanize_entities(answer_entities, query)
    gnd_tokens = _token_set(raw_gnd)
    if not gnd_tokens:
        return False

    return all(_token_set(phrase).issubset(gnd_tokens) for phrase in answer_phrases)


def _looks_like_validator_prose(value: str) -> bool:
    normalized = str(value).strip().lower()
    return any(
        marker in normalized
        for marker in (
            "the correct answer",
            "correct answer should",
            "answer correctly",
            "should include",
            "should be",
            "is incorrect",
            "is contradicted",
        )
    )


def _parse_json_payload(content: str) -> Any:
    content = content.strip()
    if not content:
        raise ValueError("judge response is empty")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    start = content.find("[")
    end = content.rfind("]")
    if start != -1 and end != -1 and start < end:
        return json.loads(content[start : end + 1])

    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and start < end:
        return json.loads(content[start : end + 1])

    raise ValueError("judge response does not contain valid JSON")


def _extract_quoted_entities(text: str) -> list[str]:
    candidates = re.findall(r"'([^']+)'", text)
    candidates.extend(re.findall(r'"([^"]+)"', text))
    seen: set[str] = set()
    entities: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip()
        if (
            not normalized
            or normalized in seen
            or len(normalized) > 160
            or not _looks_like_entity_id(normalized)
        ):
            continue
        seen.add(normalized)
        entities.append(normalized)
    return entities


def _looks_like_entity_id(value: str) -> bool:
    if "_" in value:
        return True
    return any(token in value for token in (":", "{", "}", "[", "]"))


def _extract_query_entity_ids(query: str) -> list[str]:
    return re.findall(r"id:\s*'([^']+)'", query)


def _extract_answer_entities(answer: Any) -> list[str]:
    entities: list[str] = []
    _collect_answer_entities(answer, entities)
    return entities


def _collect_answer_entities(answer: Any, entities: list[str]) -> None:
    if isinstance(answer, str):
        stripped = answer.strip()
        if stripped:
            entities.append(stripped)
        return
    if isinstance(answer, list):
        for item in answer:
            _collect_answer_entities(item, entities)
        return
    if isinstance(answer, dict):
        for value in answer.values():
            _collect_answer_entities(value, entities)


def _filter_query_entities(entities: list[str], query: str) -> list[str]:
    query_entities = set(_extract_query_entity_ids(query))
    filtered = [entity for entity in entities if entity not in query_entities]
    return filtered or entities


def _humanize_entities(entities: list[str], query: str) -> list[str]:
    shared_answer_prefix = _common_prefix_tokens(entities)
    query_entities = _extract_query_entity_ids(query)
    humanized: list[str] = []
    seen: set[str] = set()
    for entity in entities:
        phrase = _humanize_entity(entity, query_entities, shared_answer_prefix)
        if phrase in seen:
            continue
        seen.add(phrase)
        humanized.append(phrase)
    return humanized


def _humanize_entity(entity: str, query_entities: list[str], shared_answer_prefix: list[str]) -> str:
    tokens = [token for token in entity.split("_") if token]
    if not tokens:
        return entity.strip()

    shared_lengths = [len(shared_answer_prefix)] if shared_answer_prefix else []
    for query_entity in query_entities:
        if entity == query_entity:
            continue
        query_tokens = [token for token in query_entity.split("_") if token]
        shared_lengths.append(_shared_prefix_length(tokens, query_tokens))

    strip_count = max(shared_lengths, default=0)
    if strip_count >= len(tokens):
        strip_count = max(0, len(tokens) - 1)

    phrase_tokens = tokens[strip_count:] or tokens
    return " ".join(phrase_tokens)


def _token_set(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^A-Za-z0-9]+", str(value).lower())
        if token
    }


def _shared_prefix_length(left: list[str], right: list[str]) -> int:
    length = 0
    for left_token, right_token in zip(left, right):
        if left_token != right_token:
            break
        length += 1
    return length


def _common_prefix_tokens(values: list[str]) -> list[str]:
    if len(values) < 2:
        return []

    token_lists = [[token for token in value.split("_") if token] for value in values if value]
    if len(token_lists) < 2:
        return []

    prefix = token_lists[0]
    for tokens in token_lists[1:]:
        shared_length = _shared_prefix_length(prefix, tokens)
        prefix = prefix[:shared_length]
        if not prefix:
            return []

    return prefix


def _join_phrases(phrases: list[str]) -> str:
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"


def _normalize_judge_prompt_object(raw: dict[str, object]) -> AnswerJudgePromptConfig | None:
    system = _first_string(raw, ["system", "system_prompt", "judge_system"])
    context_parts = [
        _first_string(
            raw,
            [
                "context",
                "judge_context",
                "dataset_description",
                "dataset_context",
            ],
        )
    ]
    context_parts.extend(_normalize_text_list(raw.get("judge_notes")))
    context_parts.extend(_normalize_text_list(raw.get("instructions")))
    context_parts.extend(_normalize_text_list(raw.get("notes")))
    context_parts.extend(_normalize_prefix_rules(raw.get("node_prefix_rules")))
    context_parts.extend(_normalize_prefix_rules(raw.get("prefix_rules")))
    context_parts.extend(_normalize_text_list(raw.get("examples")))
    context = "\n".join(part for part in context_parts if part)
    if not system and not context:
        return None
    return AnswerJudgePromptConfig(system=system, context=context)


def _select_prompt_section(raw: object, prompt_key: str | None) -> object:
    if prompt_key is None:
        return raw

    current = raw
    for part in prompt_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"prompt key not found: {prompt_key}")
        current = current[part]
    return current


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
        if not isinstance(value, list):
            continue
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
    if not isinstance(raw, list):
        return []

    strings: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            strings.append(item.strip())
    return strings


def _normalize_prefix_rules(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        rules = []
        for prefix, meaning in raw.items():
            if isinstance(meaning, str) and meaning.strip():
                rules.append(f"Prefix `{prefix}` means {meaning.strip()}")
        return rules
    if not isinstance(raw, list):
        return []

    rules: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            rules.append(item.strip())
            continue
        if not isinstance(item, dict):
            continue
        prefix = item.get("prefix")
        meaning = item.get("meaning")
        if isinstance(prefix, str) and isinstance(meaning, str):
            rules.append(f"Prefix `{prefix}` means {meaning.strip()}")
    return rules


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


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
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temp_path = Path(file.name)
    temp_path.replace(path)

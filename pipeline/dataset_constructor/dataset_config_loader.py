"""Load dataset config files with optional JSON comments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_dataset_config(path: str | Path) -> Any:
    raw_text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return json.loads(_strip_json_comments(raw_text))


def _strip_json_comments(raw_text: str) -> str:
    output: list[str] = []
    in_string = False
    escape = False
    index = 0

    while index < len(raw_text):
        char = raw_text[index]

        if in_string:
            output.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue

        next_char = raw_text[index + 1] if index + 1 < len(raw_text) else ""
        if char == "/" and next_char == "/":
            index += 2
            while index < len(raw_text) and raw_text[index] not in "\r\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(raw_text):
                if raw_text[index] == "*" and raw_text[index + 1] == "/":
                    index += 2
                    break
                index += 1
            continue

        output.append(char)
        index += 1

    return "".join(output)

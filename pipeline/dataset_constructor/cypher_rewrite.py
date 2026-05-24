"""Cypher RETURN rewriting for node-id based dataset answers."""

from __future__ import annotations

import re


_RETURN_PATTERN = re.compile(
    r"\bRETURN\b(?P<distinct>\s+DISTINCT)?\s+(?P<body>.*?)(?P<tail>\s+(?:ORDER\s+BY|SKIP|LIMIT)\b.*)?$",
    re.IGNORECASE | re.DOTALL,
)
_BARE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def rewrite_return_nodes_to_ids(query: str, node_id_key: str = "_node_id") -> str:
    """Rewrite bare node return items to return their `_node_id` property."""
    match = _RETURN_PATTERN.search(query)
    if not match:
        return query

    body = match.group("body").strip()
    if not body:
        return query

    items = _split_return_items(body)
    rewritten_items = [_rewrite_item(item.strip(), node_id_key) for item in items]
    if rewritten_items == items:
        return query

    distinct = match.group("distinct") or ""
    tail = match.group("tail") or ""
    rewritten_return = f"RETURN{distinct} {', '.join(rewritten_items)}{tail}"
    return f"{query[:match.start()]}{rewritten_return}"


def get_node_id_return_aliases(query: str, node_id_key: str = "_node_id") -> set[str]:
    """Return aliases produced by `x._node_id AS x` return items."""
    match = _RETURN_PATTERN.search(query)
    if not match:
        return set()

    aliases: set[str] = set()
    for item in _split_return_items(match.group("body").strip()):
        alias = _node_id_alias(item.strip(), node_id_key)
        if alias:
            aliases.add(alias)
    return aliases


def _rewrite_item(item: str, node_id_key: str) -> str:
    if not _BARE_IDENTIFIER.fullmatch(item):
        return item
    return f"{item}.{node_id_key} AS {item}"


def _node_id_alias(item: str, node_id_key: str) -> str | None:
    pattern = re.compile(
        rf"^([A-Za-z_][A-Za-z0-9_]*)\.{re.escape(node_id_key)}\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)$",
        re.IGNORECASE,
    )
    match = pattern.fullmatch(item)
    if not match:
        return None
    variable, alias = match.groups()
    return alias if alias == variable else alias


def _split_return_items(body: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False

    for char in body:
        if quote:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
            continue
        current.append(char)

    if current:
        items.append("".join(current).strip())
    return items

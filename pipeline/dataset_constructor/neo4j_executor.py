"""Neo4j execution and result serialization."""

from __future__ import annotations

from typing import Any


class Neo4jExecutor:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        node_id_key: str = "_node_id",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.node_id_key = node_id_key
        self.driver = None

    def connect(self) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError(
                "neo4j is required to execute noise graph queries. Install project dependencies first."
            ) from exc

        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        with self.driver.session() as session:
            session.run("RETURN 1").consume()

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            self.driver = None

    def execute(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if self.driver is None:
            raise RuntimeError("Neo4j executor is not connected")

        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [
                {
                    key: serialize_neo4j_value(value, node_id_key=self.node_id_key)
                    for key, value in dict(record).items()
                }
                for record in result
            ]

    def __enter__(self) -> "Neo4jExecutor":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def serialize_neo4j_value(value: Any, node_id_key: str = "_node_id") -> Any:
    try:
        from neo4j.graph import Node, Path, Relationship
    except Exception:  # pragma: no cover
        Node = Relationship = Path = ()  # type: ignore

    if isinstance(value, Node):
        if node_id_key in value:
            return value[node_id_key]
        return getattr(value, "element_id", getattr(value, "id", None))

    if isinstance(value, Relationship):
        rel = {
            key: serialize_neo4j_value(value[key], node_id_key)
            for key in value.keys()
        }
        rel["_type"] = value.type
        rel["_edge_id"] = getattr(value, "element_id", getattr(value, "id", None))
        return rel

    if isinstance(value, Path):
        return {
            "nodes": [serialize_neo4j_value(node, node_id_key) for node in value.nodes],
            "relationships": [
                serialize_neo4j_value(rel, node_id_key) for rel in value.relationships
            ],
        }

    if isinstance(value, list):
        return [serialize_neo4j_value(item, node_id_key) for item in value]
    if isinstance(value, dict):
        return {
            key: serialize_neo4j_value(item, node_id_key)
            for key, item in value.items()
        }
    return value

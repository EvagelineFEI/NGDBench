# Dataset Constructor

`pipeline.dataset_constructor` is the consolidated dataset-building entry point for NGDB benchmark data. It replaces older scattered scripts in `pipeline/handler`, `pipeline/query_module`, and noise execution helpers.

## Install Dependencies

Run from the repository root:

```bash
uv sync
```

Neo4j-backed modes require the `neo4j` package and an accessible Neo4j instance. Translation and answer-judging modes require an OpenAI-compatible API endpoint and key. Do not commit real API keys, service tokens, database passwords, or private absolute paths.

## CLI Overview

Use the formal subcommand style:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind structured \
  --input INPUT.json \
  --output OUTPUT.json \
  --neo4j-uri bolt://<neo4j-host>:<bolt-port> \
  --neo4j-user neo4j \
  --neo4j-password YOUR_NEO4J_PASSWORD \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL
```

The legacy no-subcommand form is still supported:

```bash
uv run python -m pipeline.dataset_constructor.cli \
  --kind structured \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --translate-only
```

Common options:

- `--kind`: one of `structured`, `unstructured`, `management`, or `judge`.
- `--input`: source JSON file.
- `--output`: output dataset JSON file.
- `--api-key`, `--base-url`, `--model`: OpenAI-compatible translation configuration.
- `--dataset-config`: optional JSON file with dataset-specific translation or judging context.
- `--dataset-context`: optional one-line dataset-specific translation hint.
- `--prompt-key`: optional dotted path inside the dataset config JSON.
- `--chunk-size`: translation or judging batch size.
- `--translate-only`: build output records and translate queries without executing Neo4j queries.
- `--limit`: process only the first N records for debugging.
- `--fail-fast`: stop on the first execution, translation, or judging failure.

Neo4j options are required for `structured` and `unstructured` when `--translate-only` is not set:

- `--neo4j-uri`
- `--neo4j-user`
- `--neo4j-password`

`management` does not require Neo4j because it formats existing operation and validation steps. `judge` does not require Neo4j by default; if all three Neo4j options are provided, missing `noise_answer` values can be executed and filled from Neo4j.

## Structured Datasets

Use `--kind structured` for normal no-aggregation and aggregation query result files.

Expected input record shape:

```json
{
  "template_id": "T001",
  "template_type": "basic",
  "query": "MATCH (m:Account) RETURN m",
  "answer": [{"m": {"_node_id": "Account:1", "name": "Alice"}}]
}
```

Behavior:

- Rewrites bare node returns, for example `RETURN m` to `RETURN m._node_id AS m`.
- Executes the rewritten query on the noisy Neo4j graph unless `--translate-only` is used.
- Cleans both clean-graph and noisy-graph answers.
- Keeps ordinary query result multiplicity.
- Adds natural-language `nlp` text through the translation API.

Example:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind structured \
  --input pipeline/query_gen/query/ngdb_data_keephere/query_results_primekg_agg.json \
  --output pipeline/query_gen/query/final/primekg/query_results_agg.json \
  --neo4j-uri bolt://<neo4j-host>:<bolt-port> \
  --neo4j-user neo4j \
  --neo4j-password YOUR_NEO4J_PASSWORD \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL
```

Output fields:

```json
{
  "template_id": "T001",
  "template_type": "basic",
  "query": "MATCH (m:Account) RETURN m._node_id AS m",
  "clean_answer": "Account:1",
  "noise_answer": "Account:1",
  "same_as_cleangraph": true,
  "nlp": "Find the account..."
}
```

## Unstructured Evidence Datasets

Use `--kind unstructured` for records that already contain structured query answers and need evidence snippets from `mention_in` relationships.

Expected input record shape:

```json
{
  "template_id": "chain_T002",
  "template_type": "chain",
  "query": "MATCH (a:entity {id: 'active transportation'})<-[:promote *1..5]-(b:entity) RETURN a.id, b.id",
  "answer": [{"a.id": "active transportation", "b.id": "policies"}],
  "gnd": [{"a.id": "active transportation", "b.id": "policies"}]
}
```

Behavior:

- Extracts entity ids from the Cypher query.
- Extracts answer ids from common id fields.
- Queries Neo4j for `MATCH (n)-[:mention_in]->(m)` using those ids.
- Writes recovered evidence snippets into `mention_in_nodes`.
- Preserves `gnd` when present.
- Adds natural-language `nlp`.

Example:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind unstructured \
  --input INPUT.json \
  --output OUTPUT.json \
  --neo4j-uri bolt://<neo4j-host>:<bolt-port> \
  --neo4j-user neo4j \
  --neo4j-password YOUR_NEO4J_PASSWORD \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json
```

## Management Datasets

Use `--kind management` for operation and validation step datasets. This mode does not connect to Neo4j.

Expected input can be either a single record or a list of records:

```json
{
  "steps": [
    {
      "step": 1,
      "operate_query": "CREATE (n:Post {locationIP: '1.2.0.161'})",
      "valid_query": "MATCH (n:Post) RETURN count(n) AS cnt",
      "answer": [{"cnt": 1121227}]
    }
  ]
}
```

Example:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind management \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL
```

## Judge Datasets

Use `--kind judge` for template and anti-template judgment datasets.

Expected input record shape:

```json
{
  "type": "nested_loop",
  "template_query": "MATCH ... RETURN ...",
  "anti_template_query": "MATCH ... RETURN ...",
  "contains_noise": true,
  "clean_answer": {
    "valid_answer": [{"a": 1, "b": "A", "judge": true}],
    "invalid_answer": [{"a": 2, "b": "B", "judge": false}]
  }
}
```

Example:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind judge \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_econ_nagg.json
```

## Answer-Judge Runs

Use `answer-judge` when you already have an unstructured-query dataset with `query`, `answer`, and `mention_in_nodes`, and you want an LLM to verify whether the answer is correct.

Example:

```bash
uv run python -m pipeline.dataset_constructor.cli answer-judge \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json
```

Useful options:

- `--chunk-size`: number of records sent to the LLM per batch.
- `--limit`: judge only the first N records for debugging.
- `--fail-fast`: stop immediately when one batch fails.
- `--prompt-key`: select a nested section if your config file contains multiple prompt sections.
- `--retry-unknown-only`: keep existing non-`unknown` labels and only rejudge records whose `llm_label` is `unknown` or blank.
- `--retry-label`: keep records with other labels and only rejudge records whose existing `llm_label` matches the given label.

Output fields:

- `query`: original query.
- `gnd`: natural-language judgment grounded in the available evidence.
- `llm_label`: one of `true`, `false`, `incomplete`, or `unknown`.
- `mention_in_nodes`: original evidence snippets.
- `answer`: original answer from the input file.

## MCP Mention Backfill

Use the `mcp-mentions` subcommand when the Neo4j graph does not contain `:mention_in` edges, but you have offline MCP extraction files that map node ids to original text.

Example:

```bash
uv run python -m pipeline.dataset_constructor.cli mcp-mentions \
  --input INPUT.json \
  --output OUTPUT.json \
  --kg-extraction-dir PATH_TO_KG_EXTRACTION_FILES
```

This subcommand does not require Neo4j or translation API credentials.

## Dataset Context Configuration

The translation and judging layers accept dataset-specific context so users can explain custom node prefixes, task naming conventions, or domain-specific graph semantics.

Example config:

```json
{
  "system": "This dataset comes from an MCP tool-trajectory benchmark.",
  "dataset_description": "Node names may contain task-specific prefixes.",
  "node_prefix_rules": {
    "tool_": "generic tool-event nodes when this prefix is present in the source graph"
  },
  "translation_notes": [
    "When a prefix carries task meaning, reflect that in the translation."
  ],
  "judge_notes": [
    "Use mention evidence as the primary source for correctness judgments."
  ]
}
```

Supported config fields:

- `system`
- `dataset_description` or `dataset_context`
- `node_prefix_rules`
- `translation_notes`
- `judge_notes`
- `instructions`, `notes`, or `examples`

For larger JSON files, `--prompt-key` can select a nested section.

## Python API

```python
from pipeline.dataset_constructor import (
    backfill_mcp_mention_in_nodes,
    construct_dataset,
    construct_unstructured_dataset,
    construct_management_dataset,
    construct_judge_dataset,
)
```

The Python functions mirror the CLI options. Tests can pass a mock `translation_client` with a `translate_batch(queries: list[str]) -> list[str]` method.

## Error Handling

- Query execution failures add `error` to the affected record and continue by default.
- Translation failures write `nlp: ""` for that batch and continue by default.
- Use `--fail-fast` to raise the first error immediately.

## Verification

Run:

```bash
uv run python -m unittest discover
uv run python -m pipeline.dataset_constructor.cli --help
uv run python -m pipeline.dataset_constructor.cli mcp-mentions --help
```

The tests cover the documented `case.md` shapes: structured no-aggregation and aggregation records, management records, judge records, and unstructured evidence records.

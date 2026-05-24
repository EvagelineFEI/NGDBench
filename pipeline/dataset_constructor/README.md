# Dataset Constructor

`pipeline.dataset_constructor` is the consolidated dataset-building entry point for NGDB benchmark data. It replaces the older scattered entry points in `pipeline/handler`, `pipeline/query_module`, and noise execution scripts.

## Install Dependencies

The module expects the project dependencies from `pyproject.toml`:

```bash
uv sync
```

At runtime, Neo4j-backed modes require `neo4j`, and translation requires `openai` for OpenAI-compatible APIs.

## CLI

Run from the repository root:

```bash
python -m pipeline.dataset_constructor.cli \
  --kind structured \
  --input pipeline/query_gen/query/ngdb_data_keephere/query_results_ldbcfin_noagg.json \
  --output pipeline/query_gen/query/final/complex_query_agg.json \
  --neo4j-uri bolt://localhost:7693 \
  --neo4j-user neo4j \
  --neo4j-password fei123456 \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL
```

Common options:

- `--kind`: one of `structured`, `unstructured`, `management`, `judge`. Defaults to `structured`.
- `--input`: source JSON file.
- `--output`: output dataset JSON file.
- `--api-key`, `--base-url`, `--model`: required OpenAI-compatible translation config. These are explicit by design; no hidden default key is used.
- `--dataset-config`: optional JSON file with dataset-specific translation context. Supported by `structured`, `unstructured`, `management`, and `judge`.
- `--dataset-context`: optional one-line extra hint for the current run.
- `--prompt-config`: deprecated alias of `--dataset-config`.
- `--prompt-key`: optional dotted path inside the JSON file. Useful when one file contains multiple prompt sections.
- `--chunk-size`: translation batch size. Defaults to `50`.
- `--translate-only`: build output records and translate queries, but skip Neo4j execution.
- `--limit`: process only the first N records for debugging.
- `--fail-fast`: stop on first execution or translation failure.
- `--keep-template-id` / `--no-keep-template-id`: keep source `template_id` where applicable. Defaults to keep.

Neo4j options are required for `structured` and `unstructured` when `--translate-only` is not set:

- `--neo4j-uri`
- `--neo4j-user`
- `--neo4j-password`

`management` does not require Neo4j because it formats existing operation/validation steps.
`judge` also does not require Neo4j by default; if all three Neo4j options are provided, missing `noise_answer` values are executed and filled from Neo4j.

The legacy CLI above is still supported. There is also a formal subcommand style:

```bash
python -m pipeline.dataset_constructor.cli build \
  --kind structured \
  --input INPUT.json \
  --output OUTPUT.json \
  --neo4j-uri bolt://localhost:7689 \
  --neo4j-user neo4j \
  --neo4j-password fei123456 \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL
```

Translation-only example:

```bash
python -m pipeline.dataset_constructor.cli build \
  --kind structured \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL \
  --translate-only
```

Unstructured-answer judging example:

```bash
python -m pipeline.dataset_constructor.cli answer-judge \
  --input pipeline/query_gen/query/final/mcp/complex_query_noagg_with_mentions.json \
  --output pipeline/query_gen/query/final/mcp/complex_query_noagg_judged.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json
```

```bash
python -m pipeline.dataset_constructor.cli \
  --kind judge \
  --input pipeline/query_gen/query/final/econ/econ_nagg_mention_in_results.json \
  --output pipeline/query_gen/query/final/econ/econ_nagg_mention_in_results_judged.json \
  --api-key sk-04f57d2186f2487ea1c9c163376b7345 \
  --base-url https://api.deepseek.com \
  --model deepseek-v4-pro \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_econ_nagg.json
```

deepseek: sk-e6e43500cf1544ef8d23aa00acfbcfb8
poe : sk-poe-1GvoJVpmMTlLxtGjANdDklw9MQXwuNx57yI3JJp-FJU
base_url="https://api.poe.com/v1" gemini-3.1-pro

python -m pipeline.dataset_constructor.cli answer-judge \
    --input pipeline/query_gen/query/final/mcp/complex_query_agg_with_mentions.json \
    --output pipeline/query_gen/query/final/mcp/complex_query_agg_judged.json \
    --api-key sk-e6e43500cf1544ef8d23aa00acfbcfb8 \
    --base-url https://api.deepseek.com \
    --model deepseek-v4-pro \
    --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json \
    --chunk-size 1

python -m pipeline.dataset_constructor.cli answer-judge \
    --input /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/mcp/complex_query_agg_judged.json \
    --output /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/mcp/complex_query_agg_judged_retry.json \
    --api-key sk-04f57d2186f2487ea1c9c163376b7345 \
    --base-url https://api.poe.com/v1 \
    --model gemini-3.1-pro \
    --dataset-config /home/ylivm/ngdb/ngdb_benchmark/pipeline/dataset_constructor/config/dataset_config_mcp.json \
    --retry-label unknown \
    --chunk-size 1

python -m pipeline.dataset_constructor.cli answer-judge \
    --input /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/econ/econ_nagg_mention_in_results.json \
    --output /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/econ/econ_nagg_mention_in_results_judged.json \
    --api-key sk-04f57d2186f2487ea1c9c163376b7345 \
    --base-url https://api.deepseek.com \
    --model deepseek-v4-pro \
    --dataset-config /home/ylivm/ngdb/ngdb_benchmark/pipeline/dataset_constructor/config/dataset_config_econ.json \
    --retry-label unknown \
    --retry-label incomplete \
    --chunk-size 1

python -m pipeline.dataset_constructor.cli answer-judge \
    --input /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/econ/econ_nagg_mention_in_results.json \
    --output /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/econ/econ_nagg_mention_in_results_judged.json \
    --api-key sk-04f57d2186f2487ea1c9c163376b7345 \
    --base-url https://api.deepseek.com \
    --model deepseek-v4-pro \
    --dataset-config /home/ylivm/ngdb/ngdb_benchmark/pipeline/dataset_constructor/config/dataset_config_econ.json \
    --retry-label unknown \
    --retry-label incomplete \
    --chunk-size 1

## Answer-Judge Run Guide

Use `answer-judge` when you already have an unstructured-query dataset with `query`, `answer`, and `mention_in_nodes`, and you want an LLM to verify whether the answer is correct.

Input expectations:

- Each record should contain `query`, `answer`, and `mention_in_nodes`.
- The MCP config file can be reused as the judge prompt config.
- For judging, `translation_notes` are ignored; `system`, `dataset_description`, `node_prefix_rules`, and `judge_notes` are used.

Recommended command for the MCP dataset:

```bash
python -m pipeline.dataset_constructor.cli answer-judge \
  --input /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/mcp/complex_query_noagg_with_mentions.json \
  --output /home/ylivm/ngdb/ngdb_benchmark/pipeline/query_gen/query/final/mcp/complex_query_noagg_judged.json \
  --api-key sk-edc6c171ed524d059e3053b33ea96705 \
  --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --model qwen2.5-32b-instruct \
  --dataset-config /home/ylivm/ngdb/ngdb_benchmark/pipeline/dataset_constructor/config/dataset_config_mcp.json
```

Useful options:

- `--chunk-size`: number of records sent to the LLM per batch. Defaults to `5`.
- `--limit`: judge only the first N records for debugging.
- `--fail-fast`: stop immediately when one batch fails.
- `--prompt-key`: select a nested section if your config file contains multiple prompt sections.
- `--retry-unknown-only`: keep existing non-`unknown` labels and only rejudge records whose `llm_label` is `unknown` or blank. Existing `gnd` values are still normalized into concise answer phrases.
- `--retry-label`: keep records with other labels and only rejudge records whose existing `llm_label` matches the given label. Can be passed multiple times, for example `--retry-label false`.

Output fields:

- `query`: original query
- `gnd`: natural-language judgment grounded in the available evidence
- `llm_label`: one of `true`, `false`, `incomplete`, or `unknown`
- `mention_in_nodes`: original evidence snippets
- `answer`: original answer from the input file

## Dataset Context Configuration

The translation layer accepts dataset-specific context so users can teach the LLM how to interpret custom node prefixes, task naming conventions, or domain-specific graph semantics.

The intended use is not to pass your graph-extraction prompt directly. Instead, create a small config that explains only the dataset characteristics relevant to translation.

The easiest format is a small JSON object like [dataset_config.example.json](/home/ylivm/ngdb/ngdb_benchmark/pipeline/dataset_constructor/dataset_config.example.json:1):

```json
{
  "system": "This dataset comes from an MCP tool-trajectory benchmark.",
  "dataset_description": "Node names may contain task-specific prefixes.",
  "node_prefix_rules": {
    "stellarpay_company_research_": "nodes related to the Stellarpay company research task",
    "tool_": "generic tool-event nodes when this prefix is present in the source graph"
  },
  "translation_notes": [
    "When a prefix carries task meaning, reflect that in the translation."
  ]
}
```

Use it from the CLI:

```bash
uv run python -m pipeline.dataset_constructor.cli \
  --kind unstructured \
  --input pipeline/query_gen/query/ngdb_data_keephere/query_results_ldbcbi_noagg.json \
  --output pipeline/query_gen/query/final/ldbcbi/complex_query_noagg.json \
  --neo4j-uri bolt://localhost:7690 \
  --neo4j-user neo4j \
  --neo4j-password fei123456 \
  --api-key sk-edc6c171ed524d059e3053b33ea96705 \
  --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --model qwen2.5-7b-instruct \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json
```
You can also append a one-off hint without creating a file:

```bash
python -m pipeline.dataset_constructor.cli \
  --kind unstructured \
  --input INPUT.json \
  --output OUTPUT.json \
  --neo4j-uri bolt://localhost:7689 \
  --neo4j-user neo4j \
  --neo4j-password fei123456 \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL \
  --dataset-context "Node prefixes encode which MCP task or tool family a node belongs to."
```

For larger JSON files, `--prompt-key` can still select a nested section. If you already keep translation-relevant notes inside another JSON file, you can point at the specific subsection. Your existing [mcp_custom_prompt.json](/home/ylivm/ngdb/ngdb_benchmark/pipeline/dataset_constructor/mcp_custom_prompt.json:1) can technically be selected, but it is better to create a smaller translation-focused config rather than reuse the full extraction prompt.

Recommended:

- Create a small `dataset_config.json` with only translation-relevant dataset facts.
- Use `node_prefix_rules` to explain prefix semantics directly.
- Use `translation_notes` for short rules the translator should remember.

Supported config fields:

- `system`
- `dataset_description` or `dataset_context`
- `node_prefix_rules`
- `translation_notes`
- `instructions`, `notes`, or `examples`

For `answer-judge`, the loader reads the same dataset config format, supports JSON comments, and ignores `translation_notes`. The relevant fields are:

- `system`
- `dataset_description` or `dataset_context`
- `node_prefix_rules`
- `judge_notes`

Judged output shape:

```json
{
  "query": "MATCH (a:entity {id: 'node_1'}) RETURN a.id",
  "gnd": "The evidence supports node_1 as the answer.",
  "llm_label": "true",
  "mention_in_nodes": ["...evidence text..."],
  "answer": ["node_1"]
}
```

Nested config selection example:

```bash
python -m pipeline.dataset_constructor.cli \
  --kind unstructured \
  --input INPUT.json \
  --output OUTPUT.json \
  --neo4j-uri bolt://localhost:7689 \
  --neo4j-user neo4j \
  --neo4j-password fei123456 \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config my_dataset_config.json \
  --prompt-key mcp.en
```

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
- Executes the rewritten query on the noise Neo4j graph.
- Cleans both clean-graph and noise-graph answers.
- Keeps answer multiplicity; it does not deduplicate ordinary query results.
- Adds English `nlp` through the translation API.
- Translation prompts explicitly preserve labels, property names, and literal values such as ids, balances, counts, and thresholds.

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

Useful command:

```bash
python -m pipeline.dataset_constructor.cli \
  --kind structured \
  --input pipeline/query_gen/query/ngdb_data_keephere/query_results_primekg_agg.json \
  --output pipeline/query_gen/query/final/primekg/query_results_agg.json \
  --neo4j-uri bolt://localhost:7689 \
  --neo4j-user neo4j \
  --neo4j-password fei123456 \
  --api-key sk-e6e43500cf1544ef8d23aa00acfbcfb8 \
  --base-url https://api.deepseek.com \
  --model deepseek-v4-pro
  
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

- Extracts entity ids from the Cypher query, such as `{id: '...'}` and `id = '...'`.
- Extracts answer ids from fields like `id`, `a.id`, `b.id`, `m.id`, and known list-id fields.
- Queries Neo4j for `MATCH (n)-[:mention_in]->(m)` using those ids.
- Writes `mention_in_nodes` as the evidence/context snippets.
- Preserves `gnd` when present.
- Adds English `nlp`.
- Translation prompts explicitly preserve labels, property names, and literal values such as ids, balances, counts, and thresholds.

Command:

```bash
python -m pipeline.dataset_constructor.cli \
  --kind unstructured \
  --input INPUT.json \
  --output OUTPUT.json \
  --neo4j-uri bolt://localhost:7689 \
  --neo4j-user neo4j \
  --neo4j-password fei123456 \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL
```
conda run -n ngdb python -m pipeline.dataset_constructor.cli answer-judge \
  --input pipeline/query_gen/query/final/mcp/complex_query_noagg_judged.json \
  --output pipeline/query_gen/query/final/mcp/complex_query_noagg_judged_retry_false.json \
  --api-key sk-edc6c171ed524d059e3053b33ea96705 \
  --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --model qwen2.5-32b-instruct \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json \
  --chunk-size 5 \
  --retry-label false



Output fields:

```json
{
  "template_id": "chain_T002",
  "template_type": "chain",
  "query": "...",
  "answer": [{"a.id": "active transportation", "b.id": "policies"}],
  "query_node_ids": ["active transportation"],
  "answer_node_ids": ["active transportation", "policies"],
  "mention_in_nodes": ["...evidence text..."],
  "error": null,
  "gnd": [{"a.id": "active transportation", "b.id": "policies"}],
  "nlp": "Starting from active transportation..."
}
```

## MCP Mention Backfill

Use the `mcp-mentions` subcommand when the Neo4j graph does not contain `:mention_in` edges, but you do have offline MCP extraction files that map node ids to the original text.

Behavior:

- Reads the dataset JSON produced earlier, for example an MCP `--kind unstructured` output file.
- Builds a `node id -> original_text` index from the `kg_extraction` files.
- Uses `query_node_ids` and `answer_node_ids` to find matching source texts.
- Falls back to parsing node ids from `query` and `answer` when needed.
- Normalizes tool-call style ids such as `dashboard_design_listlibrarycomponents:0{"library": "dprc"}` so truncated query ids can still be resolved.
- Writes the recovered texts into `mention_in_nodes`.

Command:

```bash
python -m pipeline.dataset_constructor.cli mcp-mentions \
  --input pipeline/query_gen/query/final/mcp/complex_query_agg.json \
  --output pipeline/query_gen/query/final/mcp/complex_query_agg_with_mentions.json \
  --kg-extraction-dir /home/ylivm/AutoSchemaKG/import/mcp_tragectory_40pct/kg_extraction
```

This subcommand does not require Neo4j or translation API credentials.

## Management Datasets

Use `--kind management` for operation/validation step datasets.

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

Behavior:

- Cleans validation `answer`.
- Translates both `operate_query` and `valid_query`.
- Does not connect to Neo4j.

Command:

```bash
python -m pipeline.dataset_constructor.cli \
  --kind management \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL
```
```bash
uv run python -m pipeline.dataset_constructor.cli \
  --kind management \
  --input pipeline/query_gen/query/ngdb_data_keephere/management_query_primekg_noagg.json \
  --output pipeline/query_gen/query/final/primekg/management_query_noagg.json \
  --api-key sk-edc6c171ed524d059e3053b33ea96705 \
  --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --model qwen2.5-7b-instruct 
  
Output fields:

```json
{
  "steps": [
    {
      "step": 1,
      "operate_query": "...",
      "valid_query": "...",
      "answer": 1121227,
      "operate_nlp": "Insert a Post node...",
      "valid_nlp": "How many Post nodes are there?"
    }
  ]
}
```

## Judge Datasets

Use `--kind judge` for template/anti-template judgment datasets.

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

Behavior:

- Preserves existing `clean_answer`.
- If `noise_answer` is already present, preserves it.
- If `noise_answer` is missing and all Neo4j options are provided, executes `template_query` and `anti_template_query` on Neo4j and builds `valid_answer` / `invalid_answer`.
- If Neo4j options are omitted, leaves missing `noise_answer` as `null`.
- Translates `template_query` into `nlp`.
- Supports `--dataset-config` for dataset-specific translation context. In `--kind judge`, both translation-oriented fields such as `dataset_description` / `translation_notes` and judge-oriented `judge_notes` are added to the translation prompt.

Command:

```bash
python -m pipeline.dataset_constructor.cli \
  --kind judge \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_econ_nagg.json
```


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
python -m unittest discover
python -m pipeline.dataset_constructor.cli --help
python -m pipeline.dataset_constructor.cli mcp-mentions --help
```

The current tests cover the documented `case.md` shapes: structured no-agg/agg, management, judge, and unstructured evidence records.

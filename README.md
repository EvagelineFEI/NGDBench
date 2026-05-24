# NGDB Benchmark

NGDB Benchmark is used to generate graph data, create perturbed graphs, load graphs into Neo4j, generate Cypher queries, and assemble the final natural-language QA datasets.


## Repository Layout

- `data_gen/`: source data processing, graph construction, graph perturbation, and perturbation records.
- `pipeline/db_builder/`: imports `.gpickle` / `.graphml` graphs into Neo4j.
- `pipeline/query_gen/`: generates queries from Neo4j schema information and query templates.
- `pipeline/dataset_constructor/`: the consolidated dataset construction entry point. It executes noisy-graph queries, cleans answers, translates Cypher, and builds `judge`, `management`, and `unstructured` datasets.
- `pipeline/query_module/` and `pipeline/handler/`: legacy script area. Some entry points are obsolete; prefer `pipeline.dataset_constructor.cli`.
- `scripts/`: helper scripts for preparing and loading LDBC data.

## Environment Setup

This project uses `uv` for Python environment management:

```bash
cd ngdb_benchmark
uv sync
```

Query generation and dataset construction require an accessible Neo4j 5.x instance. The examples commonly use user `neo4j`; set the password and Bolt port according to your local container or server.

## End-to-End Workflow

### 1. Prepare Graph Data

Query generation and database loading primarily consume NetworkX graph files. The recommended format is `.gpickle`. The conventional output directory is:

```text
data_gen/graph_gen/graph_buffer/
```

Data conversion utilities are concentrated in `data_gen/graph_gen/dataload_toolkit.py`. Each dataset has its own raw file layout, so check the input path and file format before running conversion code. For example, LDBC SNB BI helper scripts are located at:

```bash
scripts/ldbc_snb_bi/ldbc_snb_bi_prepare.sh
scripts/ldbc_snb_bi/load_from_existing_data.sh
```

If you already have a graph file, you can skip directly to the next step.

### 2. Generate Perturbed Graphs

`data_gen/graph_generator.py` reads a clean graph, injects noise or incompleteness, and saves both the perturbed graph and perturbation records.

```bash
uv run python data_gen/graph_generator.py \
  --input data_gen/graph_gen/graph_buffer/ldbc_snb_finbench.gpickle \
  --output-dir data_gen/graph_gen/graph_buffer \
  --records-dir data_gen/perturbation_generator/perturb_record \
  --guide data_gen/perturbation_generator/perturb_guide/general_guid_new.json \
  --dataset-name ldbc_snb_finbench
```

Common options:

- `--input`: input `.gpickle` graph.
- `--output-dir`: output directory for perturbed graph files.
- `--records-dir`: output directory for perturbation records.
- `--guide`: perturbation rule JSON file.
- `--dataset-name`: output filename prefix; defaults to the input filename stem.

Example perturbation guides:

- `data_gen/perturbation_generator/perturb_guide/general_guid_new.json`
- `data_gen/perturbation_generator/perturb_guide/paramkg_test.json`
- `data_gen/perturbation_generator/semantic_perturb_guide/paramkg2.json`

### 3. Load Graphs Into Neo4j

Start Neo4j first, then confirm the Bolt port, username, and password. The graph importer is `Neo4jGraphBuilder` in `pipeline/db_builder/build_base.py`. The example script is:

```bash
uv run python pipeline/db_builder/test_build.py
```

The script contains hard-coded sample graph paths and Neo4j connection settings. Update these values before production use:

- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `GRAPH_PATH`
- `DATASET_NAME`

The importer writes into the default `neo4j` database and creates a shared base label `NGDBNode` plus a unique `_node_id` constraint.

### 4. Generate Queries

The structured query generation entry point is `pipeline/query_gen/qgen_test.py`. It connects to Neo4j, analyzes the schema, samples template parameters, executes queries, and writes results to JSON incrementally.

```bash
cd pipeline/query_gen
uv run python qgen_test.py \
  --uri bolt://<neo4j-host>:<bolt-port> \
  --user neo4j \
  --password YOUR_PASSWORD \
  --dataset primekg \
  --template-path query_template/template_agg.json
```

Common templates:

- `query_template/template.json`: non-aggregation structured queries.
- `query_template/template_agg.json`: aggregation structured queries.
- `query_template/template_agg_unstructured.json`: unstructured or evidence-oriented queries.
- `query_template/template_managemet.json` and `template_managemet_agg.json`: create / update / delete management queries.
- `query_template/template_mcp1.json`: MCP-related query templates.

Schema constraint files are under `pipeline/query_gen/schema/`:

- `ngdbi_schema.yaml`
- `ngdfin_schema.yaml`
- `ngdprime_schema.yaml`

`pipeline/query_gen/qgen_test_noise.py` is no longer a functional entry point. Noisy-graph answer execution and final dataset construction are handled by the dataset constructor in the next step.

### 5. Build Final Datasets

Unified CLI:

```bash
uv run python -m pipeline.dataset_constructor.cli --help
```

Structured dataset example:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind structured \
  --input pipeline/query_gen/query_results_primekg.json \
  --output pipeline/query_gen/query/final/primekg/complex_query_agg.json \
  --neo4j-uri bolt://<neo4j-host>:<bolt-port> \
  --neo4j-user neo4j \
  --neo4j-password YOUR_PASSWORD \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_econ.json
```

Translate and normalize existing answers without executing noisy-graph queries:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind structured \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --translate-only
```

Unstructured dataset:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind unstructured \
  --input INPUT.json \
  --output OUTPUT.json \
  --neo4j-uri bolt://<neo4j-host>:<bolt-port> \
  --neo4j-user neo4j \
  --neo4j-password YOUR_PASSWORD \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json
```

Management dataset:

```bash
uv run python -m pipeline.dataset_constructor.cli build \
  --kind management \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL
```

Answer-judging dataset:

```bash
uv run python -m pipeline.dataset_constructor.cli answer-judge \
  --input INPUT.json \
  --output OUTPUT.json \
  --api-key YOUR_API_KEY \
  --base-url YOUR_OPENAI_COMPATIBLE_BASE_URL \
  --model YOUR_MODEL \
  --dataset-config pipeline/dataset_constructor/config/dataset_config_mcp.json
```

For MCP datasets, use this command to backfill `mention_in_nodes` from KG extraction files:

```bash
uv run python -m pipeline.dataset_constructor.cli mcp-mentions \
  --input INPUT.json \
  --output OUTPUT.json \
  --kg-extraction-dir PATH_TO_KG_EXTRACTION_FILES
```

## Output Conventions

- Clean and perturbed graphs: `data_gen/graph_gen/graph_buffer/`
- Perturbation records: `data_gen/perturbation_generator/perturb_record/`
- Query generation results: usually `pipeline/query_gen/` or `pipeline/query_gen/query/`
- Final datasets: recommended location is `pipeline/query_gen/query/final/<dataset>/`

The released dataset can be downloaded directly from Hugging Face. This repository is mainly for reproducing or extending the data generation pipeline.

## Development And Validation

Run the dataset constructor tests:

```bash
uv run python -m unittest tests.test_dataset_constructor
```

The old top-level benchmark compatibility layer has been removed:

- `run_example.py`
- `ngdb_framework.py`
- `tests/test_basic_functionality.py`

Those files only served the early demo benchmark and are not part of the current data and query generation workflow.

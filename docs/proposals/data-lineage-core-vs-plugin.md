# Data lineage: core vs plugin

**Context:** Companion to [data-lineage-spike.md](data-lineage-spike.md). The spike proposes splitting lineage across Kedro core, an official plugin, and Kedro-Viz. This doc explains why that split matches how other tools work and why it is a good fit for Kedro.

---

## The two layers of lineage

Most data tools distinguish two kinds of lineage:

| Layer | What it answers | Typical source |
|-------|-----------------|----------------|
| **Static / structural** | What depends on what? | Code and config (declared inputs/outputs) |
| **Runtime / operational** | What ran, when, with what inputs/outputs? | Execution hooks, run artifacts, event streams |

The spike maps these layers to different components:

| Layer | Owner in spike proposal |
|-------|-------------------------|
| Static graph | **Kedro core** (`kedro.inspection`, `ProjectSnapshot`) |
| Runtime events | **Official plugin** (OpenLineage emitter) |
| Local visualization | **Kedro-Viz** (flowchart + Workflow view) |
| Long-term storage and org-wide search | **Marquez / DataHub** (external catalog) |

---

## How competitors split the work

### dbt — static in core, OpenLineage mostly outside

**In core:**

- Models declare dependencies via `ref()`.
- Every run produces `manifest.json`, `run_results.json`, and optionally `catalog.json`.
- The dependency graph is a first-class artifact of dbt itself.

**Outside core:**

- [`openlineage-dbt`](https://github.com/OpenLineage/OpenLineage/tree/main/integration/dbt) / `dbt-ol` is a wrapper that reads those JSON artifacts after the run and emits OpenLineage events.
- Lineage transport config stays separate from the dbt project.

**Moving toward core:** [dbt-core PR #11688](https://github.com/dbt-labs/dbt-core/pull/11688) proposes emitting OpenLineage from structured logs during execution. Even if merged, emission remains optional and transport-configurable — dbt core would produce events, not store them in a catalog.

**Takeaway:** dbt keeps the graph in core and treats Marquez/DataHub as an export target. That matches the spike's Phase 0/1 (inspection API) + Phase 2 (emitter) split.

---

### Dagster — lineage is core product; OpenLineage is a bridge

**In core:**

- Assets, materializations, checks, and the lineage UI are central to Dagster.
- Column lineage, schema metadata, and run history are native features.

**Outside core:**

- [`dagster-openlineage`](https://docs.dagster.io/integrations/libraries/openlineage) is a community library that converts Dagster events into OpenLineage for Marquez/DataHub.
- Dagster does not require OpenLineage to have lineage; OpenLineage is for interop with external catalogs.

**Takeaway:** Dagster is the closest analogue to Kedro. Kedro-Viz ≈ Dagster's UI for local dev. External catalog integration ≈ optional plugin.

---

### Airflow — runtime OpenLineage moved into core

**In core (since 2.7):**

- [`apache-airflow-providers-openlineage`](https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/) is an official Airflow provider.
- Listeners hook into scheduler and worker lifecycle automatically.

**Why they went native:** Airflow is the orchestrator — lineage is tightly coupled to task and DAG lifecycle. The external `openlineage-airflow` package was hard to maintain against Airflow internals, so extraction logic moved into each operator provider.

**Takeaway:** Airflow went core because it controls execution end-to-end. Kedro is a pipeline framework/library, closer to dbt/Dagster than Airflow. Native OpenLineage in Kedro core is less obvious.

---

### Others (brief)

| Tool | Static graph | OpenLineage / external catalog |
|------|-------------|--------------------------------|
| **Apache Spark** | Catalyst / logical plan | Separate `openlineage-spark` agent |
| **Prefect** | Flow graph in UI | Integrations / observability layer |
| **Flyte** | Workflow graph in core | External via plugins/adapters |
| **Marquez / DataHub** | N/A — they are the catalog | Consume OpenLineage; do not emit it |

---

## Proposed Kedro architecture

```text
┌─────────────────────────────────────────────────────────┐
│  KEDRO CORE                                             │
│  • Pipeline graph (nodes, inputs, outputs) — already    │
│    there                                                │
│  • kedro.inspection / ProjectSnapshot — Phase 0/1       │
│  • metadata.kedro schema — Phase 1                      │
│  • Stable hook contracts (run_id, pipeline_names…)      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  OFFICIAL PLUGIN (kedro-openlineage)                    │
│  • Listen to hooks at runtime                           │
│  • Map Kedro → OpenLineage                              │
│  • File sink (.viz/…) for Kedro-Viz                     │
│  • HTTP sink for Marquez / DataHub                      │
│  • Optional dep: openlineage-python                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  KEDRO-VIZ (local dev UI)                               │
│  • Flowchart + Workflow view                            │
│  • Reads file sink / inspection API                     │
└─────────────────────────────────────────────────────────┘
```

---

## What belongs in core

| Responsibility | Why core |
|----------------|----------|
| **The graph itself** | Nodes already declare inputs/outputs; this is non-negotiable framework behaviour |
| **Inspection API** | Export structure without running (dbt's `manifest.json` equivalent) |
| **Hook stability** | Consistent `run_params`, one `run_id` per `kedro run` |
| **`metadata.kedro` schema** | Owner, description, and other fields shared by lineage, validation, and catalog publishing |

Core should expose **stable contracts** that any plugin, viz, or enterprise tool can rely on. It should not hard-code Marquez or OpenLineage transport details.

---

## What belongs in the plugin

| Responsibility | Why plugin |
|----------------|------------|
| **OpenLineage emission** | Brings in `openlineage-python` |
| **Transport config** | HTTP to Marquez vs DataHub vs file-only |
| **Enterprise facets** | Column lineage discovery, validation assertions |
| **Production CI/CD** | `kedro run` without Kedro-Viz installed |

The plugin listens to core hooks and maps Kedro concepts (node, catalog dataset, run) to OpenLineage (Job, Run, Dataset). Different teams can choose different sinks without forking Kedro.

---

## Why not put everything in core?

1. **Optional dependency.** Not every Kedro user runs Marquez or DataHub.
2. **Sink flexibility.** Teams pick Marquez, DataHub, OpenMetadata, or file-only for local dev.
3. **Release cadence.** The OpenLineage spec and client evolve faster than Kedro core.
4. **Production footprint.** `kedro run` in CI should not require viz or catalog clients unless explicitly configured.
5. **Precedent.** dbt and Dagster keep external catalog integration outside core; only Airflow (an orchestrator) went fully native.

---

## Why not keep everything in a plugin?

1. **Static lineage is already core data.** Re-deriving the graph in a plugin duplicates `kedro.inspection`.
2. **Kedro-Viz needs a stable core API.** Viz should not depend on plugin-specific JSON formats for structure.
3. **Validation and lineage share metadata.** `metadata.kedro` should live in core/catalog, not a plugin-only namespace.
4. **Hook contracts are framework concerns.** Breaking changes like `pipeline_name` → `pipeline_names` (Kedro 1.5) must be handled at the framework level so all hooks and plugins stay compatible.

---

## Summary: why the spike split is good

| Question | Answer |
|----------|--------|
| Should lineage be core or plugin? | **Both — split by layer** |
| Static graph | **Core** (already exists; extend via inspection API) |
| Runtime OpenLineage → Marquez/DataHub | **Official plugin** (adopt or extend kedro-openlineage) |
| Local dev UI | **Kedro-Viz** (reads core snapshot + plugin file sink) |

The spike's split aligns with **Dagster** (core lineage + `dagster-openlineage`) and **dbt** (core artifacts + `openlineage-dbt`), not **Airflow** (native provider). Airflow went all-in because orchestration is the primary product surface for lineage. Kedro's product surface is the pipeline graph and developer experience; enterprise catalog integration is a bridge.

**Core owns the graph and the contracts. The plugin owns export. Viz owns local dev. The catalog owns persistence.**

That gives:

- **Developers** — flowchart and Workflow view without installing Marquez
- **Platform teams** — standard OpenLineage events to the catalog they already run
- **Kedro maintainers** — one inspection API and one emitter, not parallel custom JSON formats
- **Future work** — validation facets, column lineage, and DataHub publishing all plug into the same OpenLineage stream (Phase 2–4 in the spike)

The main core responsibilities before Phase 2 ships are **hook contract stability** (e.g. `pipeline_names`, `run_id`) and **one run ID per `kedro run`** — framework guarantees that the plugin should not have to patch around.

---

## Related docs

- [Data lineage spike and tech design](data-lineage-spike.md)
- [Local setup: kedro-openlineage → Marquez](kedro-openlineage-marquez-local-setup.md)
- [Kedro inspection API docs](https://docs.kedro.org/en/stable/inspect/inspect-project/)
- [OpenLineage getting started](https://openlineage.io/getting-started/)
- [kedro-openlineage proof of concept](https://github.com/astrojuanlu/kedro-openlineage)

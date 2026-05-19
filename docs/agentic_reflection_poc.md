# Agentic Reflection and Continuous Learning MVP

> Do not build an autonomous agent that silently changes itself. Build a governed reflection system that turns traces into evidence-backed improvement signals and feeds approved learning into future agent runs.

---

# 1. Problem Statement

## 1.1 The Gap

A telco B2B client runs LLM-powered agents across commercial workflows — cross-sell, pricing, digital marketing, sales, account planning, and renewal. These agents reason over customer data, product catalogs, business rules, and prior context. But most agentic systems share one major weakness:

> They execute, but they do not systematically learn from their own traces.

After each run, the organization has no structured way to answer: which recommendations were wrong or commercially poor, which failures repeat across segments, what should change in the next prompt, and whether to update memory, tools, or eval cases. The deeper problem is the absence of a governed continuous learning loop.

## 1.2 Target Problem

> Build a Kedro-native reflection and continuous learning layer that ingests agent traces, evaluates agent behavior, derives improvement signals, stores structured reflections, and feeds approved improvements back into future agent runs.

Kedro provides the pipeline backbone, Data Catalog, and modular project structure for this. New GenAI-oriented features — `LLMContextNode` and Langfuse datasets — bring prompts, traces, and evaluations into the Kedro-native development pattern.

---

# 2. POC Overview

## 2.1 MVP Summary

The MVP is an **Agentic Reflection Control Tower** for a B2B telco cross-sell agent.

**The cross-sell agent will:**

1. Read customer and product context.
2. Generate cross-sell recommendations.
3. Explain each recommendation.
4. Emit traces of prompts, tool calls, reasoning context, outputs, and metadata.
5. Pass its trace and outputs into a reflection pipeline.
6. Receive improvement signals for the next run.

**The reflection system will:**

1. Ingest agent traces.
2. Evaluate the agent's behavior and outputs.
3. Detect failures and improvement opportunities.
4. Generate structured reflection records.
5. Propose updates to prompts, eval sets, memory, skills, tools, and ontology.
6. Route sensitive changes through a human approval step.
7. Feed approved changes into the next agent run.

## 2.2 Cross-Sell as the Demonstration Scenario

The domain example is B2B telco cross-sell.

Example agent task:

> Given a B2B customer profile, product catalog, business rules, and prior learning memory, recommend the next best telco product to cross-sell and explain the recommendation.

Example products: SD-WAN, Managed Firewall, IoT Connectivity, Business Mobile, Cloud Connectivity, Private 5G, Unified Communications.

The MVP does not need to optimize real commercial decisions. It needs to prove the reusable reflection pattern.

## 2.3 What Makes This Agentic

A non-agentic version would simply run a deterministic recommendation pipeline.

The agentic version adds:

- LLM-based reasoning
- Prompt-managed behavior
- Tool use
- Trace capture
- Evaluation of reasoning and output quality
- Reflection over failures
- Memory from previous runs
- Improvement proposals
- Feedback into future inputs

---

# 3. Architecture

## 3.1 High-Level Architecture

The system is organized into six layers. Data flows top-to-bottom from inputs through the agent, into traces, evaluation, reflection, and improvement proposals. Approved changes loop back into the top.

```
INPUTS
──────────────────────────────────────────────────────────
  Customer Context  ──┐
  Product Catalog   ──┤──→ [ Cross-Sell Agent ]
  Business Rules    ──┤
  Prior Memory      ──┘

        ↓ agent outputs flow into:

TRACE CAPTURE
──────────────────────────────────────────────────────────
  Agent Trace | Tool Call Logs | Prompt Metadata | Outputs

        ↓ traces feed into:

EVALUATION
──────────────────────────────────────────────────────────
  Business Rule Check | Output Quality | Explanation | Trajectory
                          (vs. Golden Eval Set)

        ↓ evaluation results feed into:

REFLECTION
──────────────────────────────────────────────────────────
  Diagnose Failures → Mine Patterns → Reflection Record → Improvement Signal

        ↓ signals split into proposals:

IMPROVEMENT PROPOSALS
──────────────────────────────────────────────────────────
  Prompt Update | Eval Set Addition | Memory Update | Tool Change | Skill Proposal

        ↓ all proposals go to:

GOVERNANCE
──────────────────────────────────────────────────────────
  Human Review → Approved Registry  (or)  Rejected / Deferred

        ↓ approved changes feed back into INPUTS for next run
  Prompts | Memory | Eval Sets | Tools
```

## 3.2 Kedro-Native Architecture

Everything lives inside a single Kedro project. Traces, evaluations, and prompts flow into Langfuse through native Kedro-Langfuse dataset types — nodes simply write to catalog outputs and Langfuse receives them automatically. Hooks are scoped only to what datasets cannot handle: failure capture and run-level metadata. The Kedro HTTP service exposes the project to the Streamlit control tower over REST, decoupling the UI from the Kedro filesystem entirely.

```
KEDRO PROJECT
│
├── DATA CATALOG         — versioned datasets; Langfuse datasets handle observability natively
├── MODULAR PIPELINES    — one pipeline per stage, independently runnable
├── KEDRO HOOKS          — scoped to failure capture and run-level metadata only
└── HTTP SERVICE         — REST interface for external systems (Streamlit control tower)
                           GET  /snapshot  → discover pipelines, datasets, parameters
                           POST /run       → trigger a named pipeline with runtime params

Catalog ↔ Pipelines  (nodes read inputs and write outputs via catalog; Langfuse datasets
                      push to Langfuse as a side effect of the normal catalog write)
Streamlit → HTTP Service  (control tower triggers and inspects Kedro over REST, no
                           direct filesystem access needed)
```

### Data Catalog

Langfuse-backed datasets (`LangfusePromptDataset`, `LangfuseTraceDataset`, `LangfuseEvaluationDataset`) replace the need for hooks to manually emit observability events. Reading a prompt pulls the latest approved version from Langfuse. Writing a trace or evaluation score pushes it to Langfuse automatically.

| Dataset | Kedro Type | Data Layer | Contents |
|---|---|---|---|
| `customer_context` | `JSONDataset` | `01_raw` | B2B customer profiles: firmographics, product holdings, usage metrics, support-ticket history |
| `product_catalog` | `YAMLDataset` | `01_raw` | Telco product definitions, eligibility rules, bundle compatibility matrix |
| `business_rules` | `YAMLDataset` | `01_raw` | Pricing policy, compliance constraints, cross-sell eligibility logic |
| `prompt_dataset` | `LangfusePromptDataset` | `conf/base` | Versioned prompt templates fetched directly from Langfuse; loading always retrieves the current approved version |
| `agent_inputs` | `JSONDataset` | `02_intermediate` | Assembled per-customer input package for each run (context + approved memory) |
| `agent_outputs` | `JSONDataset` | `07_model_output` | Raw agent outputs: recommended products and explanations |
| `trace_dataset` | `LangfuseTraceDataset` | `02_intermediate` | Agent trace records written to Langfuse; captures inputs, tool calls, outputs, token usage, latency per run |
| `golden_eval_set` | `JSONDataset` | `03_primary` | Curated reference examples used as ground truth for evaluation |
| `evaluation_dataset` | `LangfuseEvaluationDataset` | `07_model_output` | Evaluation scores pushed to Langfuse; quality scores, issues, and labels per trace |
| `reflection_memory` | `JSONDataset` | `09_reflection_memory` | Approved structured reflections from prior runs, injected into future agent inputs |
| `improvement_signals` | `JSONDataset` | `07_model_output` | Proposed changes pending human approval |
| `approved_learning_registry` | `JSONDataset` | `10_learning_registry` | Approved prompt updates, memory entries, eval additions, and tool changes |

### Kedro Hooks

Hooks are minimal — only two remain relevant once Langfuse datasets handle observability.

**`before_pipeline_run`** — Inject approved learning into the run

Reads `approved_learning_registry` and injects approved memory entries and tool configs into pipeline parameters before execution starts. Also sets the shared `run_id` used to group all traces for this run in Langfuse.

**`on_node_error`** — Capture failures as traceable records

On node failure, writes a structured error record to `trace_dataset` marked `status: failed`. This ensures failed runs still reach Langfuse and remain available to the reflection pipeline rather than being silently dropped.

**`after_pipeline_run`** — Write run summary to catalog

Writes the run summary (customer count, recommendation count, evaluation summary, reflection count) to the local catalog for the Streamlit control tower. This is Kedro-internal metadata not covered by Langfuse datasets.

## 3.3 Pipeline-Level Design

This shows the step-by-step flow across all eight pipelines from input loading through to the feedback loop.

```
STAGE 1 — PREPARE INPUTS
  Load Customer Context → Load Product Catalog → Load Business Rules
  → Load Approved Memory → Build Agent Input

        ↓

STAGE 2 — RUN AGENT
  LLMContextNode → Run Cross-Sell Agent
  → Generate Recommendation → Generate Explanation

        ↓

STAGE 3 — CAPTURE TRACES
  Persist Agent Trace | Persist Agent Output | Persist Explanation

        ↓

STAGE 4 — EVALUATE
  Evaluate Trajectory | Evaluate Recommendation | Evaluate Explanation
  → Compare Against Golden Eval Set
  → Diagnose Failures

        ↓

STAGE 5 — REFLECT
  Mine Recurring Patterns → Generate Structured Reflection
  → Generate Improvement Signals

        ↓

STAGE 6 — PROPOSE IMPROVEMENTS
  Prompt Change | Eval Set Addition | Memory Update
  | Skill Proposal | Ontology Update

        ↓

STAGE 7 — APPROVE AND FEED BACK
  Human Approval Queue → Approved Registry
  → (feeds back into Stage 1 for next run)
```

## 3.4 Agent Trace Schema

The trace is the raw material for reflection. A minimal trace record should include:

```yaml
trace_id: trace_001
run_id: run_2026_05_18_001
agent_id: cross_sell_agent_v1
use_case: cross_sell
customer_id: CUST_001
prompt_version: cross_sell_prompt:v3
model: model_name
inputs:
  customer_context_ref: customer_context.CUST_001
  product_catalog_ref: product_catalog.v1
  business_rules_ref: business_rules.v1
  reflection_memory_refs:
    - refl_001
    - refl_002
tool_calls:
  - tool_name: product_eligibility_checker
    input_summary: SD-WAN eligibility for CUST_001
    output_summary: eligible
    latency_ms: 120
reasoning_summary: Customer has many sites and high usage; SD-WAN is likely relevant.
output:
  recommended_product: SD-WAN
  explanation: Customer has 42 sites and high usage, making SD-WAN suitable.
metadata:
  latency_ms: 2400
  token_usage:
    input_tokens: 1500
    output_tokens: 350
  status: success
```

## 3.5 Evaluation Schema

Evaluation converts traces and outputs into measurable signals.

```yaml
evaluation_id: eval_001
trace_id: trace_001
run_id: run_2026_05_18_001
scores:
  business_rule_pass: true
  recommendation_quality: 0.86
  explanation_quality: 0.72
  groundedness: 0.80
  tool_use_quality: 0.75
  trajectory_quality: 0.70
issues:
  - type: weak_explanation
    severity: medium
    message: Explanation did not mention support-ticket history.
  - type: missed_bundle_opportunity
    severity: low
    message: Managed Firewall could have been bundled with SD-WAN.
labels:
  segment: logistics_mid_market
  product: SD-WAN
  agent_version: cross_sell_agent_v1
```

## 3.6 Reflection Schema

Reflection should be structured, not just prose. Each reflection links its evidence, root cause, and proposed change so the improvement is fully traceable.

```yaml
reflection_id: refl_001
run_id: run_2026_05_18_001
source_trace_ids:
  - trace_001
  - trace_002
  - trace_003
use_case: cross_sell
reflection_type: prompt_improvement
summary: The agent underused support-ticket signals when explaining SD-WAN recommendations.
evidence:
  affected_segment: logistics_mid_market
  affected_product: SD-WAN
  weak_explanation_rate: 0.42
  examples:
    - trace_001
    - trace_003
root_cause_hypothesis: The prompt asks for product fit but does not explicitly require operational pain-point evidence.
improvement_signal:
  target: prompt
  recommended_change: Add instruction to cite operational signals such as support tickets, incident history, and usage trends.
  expected_effect: Improve explanation groundedness and sales usefulness.
confidence: medium
approval_status: pending
created_at: 2026-05-18T12:00:00Z
```

## 3.7 Improvement Signal Types

The reflection system produces multiple kinds of improvement signals targeting different parts of the agent system.

| Improvement target | What it means | MVP support |
|---|---|---|
| Prompt | Change instructions, format, examples, constraints | Yes |
| Eval set | Add new examples or failure cases | Yes |
| Memory | Store reusable lessons | Yes |
| Tool | Recommend a tool change or new tool | Partial |
| Skill | Recommend a new reusable capability | Future |
| Ontology | Recommend changes to domain concepts and relationships | Future |

## 3.8 Feedback Targets

An improvement signal fans out into specific targets. Each approved target feeds directly into the next agent run or evaluation run.

```
              [Improvement Signal]
                       │
   ┌──────┬────────┬───┴────┬────────┬──────────┐
   ↓      ↓        ↓        ↓        ↓          ↓
[Prompt] [Eval] [Memory] [Tools] [Skills] [Ontology]
   │      │        │        │        │          │
   └──────┴────→ [Next Agent Run] ←─┴──────────┘
          └────→ [Next Eval Run]  ←─ [Eval] + [Ontology]
```

---

# 4. Spec Driven Development

## 4.1 Development Philosophy

The POC is developed from specs, not generated ad hoc from prompts. This ensures each component has a clear contract before code is written.

Working pattern:

1. Define the behavior spec.
2. Define data contracts.
3. Define pipeline contracts.
4. Define evaluation rubrics.
5. Define improvement signal schemas.
6. Generate or implement code against the specs.
7. Test each pipeline independently.
8. Demo the end-to-end learning loop.

## 4.2 MVP Functional Requirements

### FR1: Agent Run

The system must run a cross-sell agent that generates product recommendations and explanations from customer context.

### FR2: Trace Ingestion

The system must capture or ingest agent traces containing prompt version, inputs, tool calls, outputs, and metadata.

### FR3: Evaluation

The system must evaluate recommendations, explanations, and trajectory behavior using deterministic rules and optional LLM-as-judge rubrics.

### FR4: Reflection

The system must generate structured reflections based on evaluation results and trace analysis.

### FR5: Improvement Signals

The system must produce proposed improvements targeting prompts, eval sets, memory, tools, skills, or ontology.

### FR6: Approval

The system must separate proposed changes from approved changes.

### FR7: Feedback

The system must feed approved changes into subsequent agent runs.

### FR8: Presentation

The system must present traces, evaluations, reflections, and improvement signals in a simple UI or control tower.

## 4.3 MVP Non-Functional Requirements

- **Traceability:** every reflection must link back to evidence.
- **Reproducibility:** every run should be reproducible from cataloged inputs.
- **Modularity:** agent execution, evaluation, reflection, and feedback should be separate Kedro pipelines.
- **Governance:** high-impact changes require approval.
- **Extensibility:** the same pattern should support pricing and digital marketing later.
- **Observability:** prompt versions, traces, evaluations, and outputs should be inspectable.

## 4.4 Data Contracts

### Agent Input Contract

```yaml
agent_input:
  customer_context: object
  product_catalog: list
  business_rules: list
  approved_memory: list
  prompt_config: object
  tool_config: object
```

### Agent Output Contract

```yaml
agent_output:
  customer_id: string
  recommended_products: list
  explanation: string
  confidence: string
  supporting_evidence: list
  next_best_action: string
```

### Trace Contract

```yaml
agent_trace:
  trace_id: string
  run_id: string
  agent_id: string
  prompt_version: string
  input_refs: object
  tool_calls: list
  output_ref: string
  metadata: object
```

### Evaluation Contract

```yaml
evaluation_result:
  evaluation_id: string
  trace_id: string
  scores: object
  issues: list
  labels: object
```

### Reflection Contract

```yaml
reflection:
  reflection_id: string
  source_trace_ids: list
  summary: string
  evidence: object
  root_cause_hypothesis: string
  improvement_signal: object
  confidence: string
  approval_status: string
```

## 4.5 Suggested Kedro Pipelines

```text
agent_input_pipeline
agent_execution_pipeline
trace_ingestion_pipeline
evaluation_pipeline
reflection_pipeline
improvement_signal_pipeline
approval_pipeline
feedback_pipeline
reporting_pipeline
```

## 4.6 Suggested Repository Structure

```text
telco_agentic_reflection/
  conf/
    base/
      catalog.yml
      parameters.yml
      prompts.yml
      evaluation_rubrics.yml
      reflection.yml
  data/
    01_raw/
    02_intermediate/
    03_primary/
    07_model_output/
    08_reporting/
    09_reflection_memory/
    10_learning_registry/
  src/
    telco_agentic_reflection/
      pipelines/
        agent_input/
        agent_execution/
        trace_ingestion/
        evaluation/
        reflection/
        improvement_signal/
        approval/
        feedback/
        reporting/
      hooks.py
      settings.py
      schemas/
      services/
        reflection_client.py
        evaluation_client.py
        approval_client.py
```

## 4.7 MVP Build Stages

### Stage 1: Synthetic Cross-Sell Agent

Build a small agent that recommends products for synthetic B2B telco customers.

### Stage 2: Trace Capture

Capture agent input, prompt version, tool calls, output, and metadata.

### Stage 3: Deterministic Evaluation

Evaluate output quality with business rules and golden examples.

### Stage 4: LLM-Based Reflection

Use an LLM to generate structured reflections from the evaluation facts.

### Stage 5: Improvement Signal Generation

Convert reflections into proposed changes to prompts, eval sets, and memory.

### Stage 6: Approval Loop

Add a lightweight review mechanism for approving or rejecting proposed changes.

### Stage 7: Feedback Into Next Run

Load approved changes into the next agent run and show improved behavior.

---

# 5. Presentation Plan

## 5.1 Demo Narrative

> We are not just building an agent. We are building a learning system around agents. The agent performs cross-sell recommendations, but the platform observes the agent, evaluates its behavior, generates improvement signals, and feeds approved learning back into future runs.

## 5.2 Control Tower UI: Streamlit + Langfuse + Kedro HTTP Service

The control tower is a **Streamlit app** that talks to two backends: **Langfuse** for trace and evaluation observability, and the **Kedro HTTP service** for triggering pipelines and inspecting project state. Streamlit has no direct filesystem access to the Kedro project — everything goes through these two APIs.

**Responsibility split:**

| What to show / do | How |
|---|---|
| Run overview and run metadata | Streamlit reads from `approved_learning_registry` snapshot |
| Trace details, prompt versions, tool calls, token usage, latency | Langfuse UI (deep link or embed) |
| LLM-as-judge evaluation scores and score breakdowns | Langfuse UI |
| Reflection board (findings, root causes, evidence) | Streamlit |
| Improvement signal queue and approve/reject action | Streamlit → `POST /run` (approval_pipeline + signal IDs as params) |
| Trigger agent run or reflection run on demand | Streamlit → `POST /run` (named pipeline) |
| Discover available pipelines and datasets | Streamlit → `GET /snapshot` |
| Before vs After comparison | Streamlit → `POST /run` (run 2 with updated params) |

## 5.3 Streamlit Layout

```
[Streamlit Control Tower]
        │
        ├── Run Overview          (run metadata, summary counts)
        ├── Trace Explorer        (deep link → Langfuse)
        ├── Evaluation Dashboard  (score summary in Streamlit; detail → Langfuse)
        ├── Reflection Board      (findings, root causes, evidence links)
        ├── Improvement Queue     (proposals + approve/reject → POST /run approval_pipeline)
        └── Before vs After       (trigger Run 2 → POST /run agent_pipeline, compare scores)
```

### Run Overview

Show: Run ID, Agent version, Prompt version, customers processed, recommendations generated, traces captured, evaluation summary, reflection summary. Populated from the Kedro HTTP `GET /snapshot` and the run summary written by the `after_pipeline_run` hook.

### Trace Explorer

Deep link into Langfuse for the run. Langfuse natively shows prompt inputs, model outputs, tool calls, token counts, and latency. No rebuild needed in Streamlit.

### Evaluation Dashboard

Show a summary scorecard in Streamlit (recommendation quality, explanation quality, business-rule pass rate, groundedness). Deep link to Langfuse for per-trace score breakdowns.

### Reflection Board

Show: key findings, root-cause hypotheses, confidence, affected segment and product, evidence trace links (deep-linked into Langfuse).

### Improvement Signal Queue

Show proposed changes grouped by target — Prompt | Eval Set | Memory | Tool | Skill | Ontology — with evidence, expected benefit, risk, and an approve/reject action. Approvals are submitted via `POST /run` to `approval_pipeline` with the selected signal IDs passed as runtime parameters.

### Before vs After

Trigger Run 2 via `POST /run` with updated parameters (approved prompt version, updated memory). Compare Run 1 vs Run 2 scores: explanation quality, business-rule pass rate, groundedness, recommendation relevance.

---

# 6. Next Steps

## 6.1 MVP Build Order

1. Define synthetic cross-sell data, trace schema, and evaluation rubrics.
2. Build a deterministic cross-sell baseline with LLMContextNode.
3. Wire up Langfuse for trace and evaluation capture.
4. Build the reflection and improvement signal pipelines.
5. Add a lightweight approval step.
6. Build the Streamlit control tower.
7. Run a two-pass demo: Run 1 → reflect → approve → Run 2 shows improvement.

## 6.2 Deployment Path

**Local POC:** Kedro project with file-based catalog, Langfuse local/cloud, Streamlit app.

**Internal Demo:** Add Kedro-Viz for pipeline explainability; store run artifacts in object storage.

**Enterprise:** Containerize, add an orchestrator, govern the learning registry, integrate with real telco CRM and product data.

## 6.3 Future Directions

- **More automation:** prompt variant generation, eval case generation from failures, A/B testing of prompt versions, automated rollback.
- **Skills:** reusable agent capabilities proposed by reflection (e.g. bundle comparison, objection handling).
- **Ontology:** reflection-proposed domain concept additions (e.g. linking `network_reliability_pain_point` to SD-WAN and multi-site customers).
- **Other use cases:** same architecture applies to Pricing, Digital Marketing, and Sales Assistant agents.

## 6.4 Target End-State

The long-term vision is a reusable learning layer for enterprise agents. The MVP proves the first version of this loop with cross-sell; the roadmap expands the same pattern to pricing, digital marketing, and other B2B telco workflows.

```
[Agents] → [Traces] → [Evaluations] → [Reflections] → [Improvement Signals]
                                                                ↓
                                           [Approved Learning Registry]
                                                    │
                        ┌──────────┬───────────────┼───────────┬──────────┐
                        ↓          ↓               ↓           ↓          ↓
                    [Prompts] [Eval Sets]       [Memory]   [Skills]  [Ontology]
                        │          │               │           │          │
                        └──────────┴──→ [Agents] ←┘           │          │
                                        [Evals]  ←─────────────┴──────────┘
```

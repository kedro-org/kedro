# Miro board blueprint — Dataset Validation implementation tech design

Build guide for tomorrow's session. Frames go **left → right** in session order. Estimated build time: **2.5–3 hours**. Build order recommendation: Frame 5 (architecture) first while you're fresh — it's the only real drawing; everything else is stickies and text.

**Session shape:** 60 min · Purpose is NOT "should we do this" (KEP accepted, +3) — it's *walk the accepted architecture, then lock the open implementation decisions*. Say that in the first 30 seconds; it frames every discussion as "decide," not "relitigate."

**Colour code (use consistently on every frame):**
- 🟦 Blue = existing Kedro (unchanged)
- 🟩 Green = new in this feature
- 🟨 Amber = lazy / happens at first use
- 🟥 Red = decision needed today
- ⬜ Grey = out of scope for v1 / future

---

## Frame 1 — Title & agenda (2 min)

Big title: **Dataset Validation — implementation tech design**
Subtitle: *KEP accepted ✅ (+3). Today: walk the architecture, lock 7 decisions, agree the PR plan.*

Links block (paste as text, one per line):
- KEP discussion: github.com/kedro-org/kedro/discussions/5602
- Parent initiative: #5390 · Spike: #5391
- Prototype branch: `prototype/kep7-v2-catalog-validation` (tests green, runnable demo)

Agenda stickies with timeboxes:
1. The journey since April (3 min)
2. The proposal in one screen (5 min)
3. Architecture: follow one `catalog.load()` (10 min)
4. The 7 design decisions + why not hooks/wrapper (10 min)
5. Live demo (5 min)
6. 🟥 Decisions to lock today (20 min) ← the point of the session
7. Rollout plan + actions (5 min)

---

## Frame 2 — The journey (3 min)

Horizontal timeline (line + 8 dated stickies):
- **Feb** — #5390 opened: "cohesive validation strategy" (Rashida)
- **Apr 22** — Tech design v1: type-hint approach, Pandera prototype
- **May** — KEP-7 posted (type hints drive validation)
- **May–Jun** — Community feedback pauses the vote *(add 3 mini-quote stickies below the line)*:
  - deepyaman: "if validation is tied to datasets, define the schema ON the dataset" + "last-wins silently is concerning"
  - Adeikalam: "schemas next to nodes bloat pipelines and create cross-pipeline dependencies"
  - noklam: "I need a global disable + an API to validate from the IDE"
- **Jun** — Pivot announced: schema-on-dataset + pluggable protocol
- **Jun** — KEP-10 posted (restructured)
- **Jun** — deepyaman: "+1, much improved, no blockers" → **TSC vote passes (+3)** ✅
- **Today** — implementation tech design

Facilitation note (small sticky, for you): *"The feedback shaped this design — every attendee here will recognise their own fingerprint on it. Point at their quote when they raise the related topic."*

---

## Frame 3 — The proposal in one screen (5 min)

Three code blocks side by side (paste as code-styled text boxes):

**Left — catalog.yml (🟩 the one new thing users learn):**
```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  validator: spaceflights.schemas.companies.CompaniesSchema
```

**Middle — src/spaceflights/schemas/companies.py:**
```python
import pandera.pandas as pa

class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(nullable=False, unique=True)
    company_rating: float = pa.Field(ge=0, le=1)
```

**Right — nodes.py (🟦 unchanged, plain Python):**
```python
def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    ...
```

Below, 4 outcome stickies:
- 🟩 Validates on **load AND save** — invalid data never written
- 🟩 Works in **notebooks / IDE / CI**, not just `kedro run`
- 🟩 One dataset = one validator, **by construction** (kills the v1 last-wins bug)
- 🟩 **Pluggable**: Pandera is the reference backend; anything with `validate(data) -> data` works (GX, Pydantic, custom, non-tabular)

And one error-message text box (this is the emotional sell — make it big):
```
DataValidationError: Validation failed for dataset 'companies' on load
(validator: spaceflights.schemas.companies.CompaniesSchema)
3 check(s) failed — 5 failure case(s):
  - id: field_uniqueness — 2 cases (e.g. 1.0, 1.0)
  - company_rating: greater_than_or_equal_to(0) — 2 cases (e.g. -0.5, -1.2)
  - company_rating: less_than_or_equal_to(1) — 1 case (e.g. 1.7)
```

---

## Frame 4 — "What changed since April" (fast — 1 min, point and move on)

Small 3-row table (this pre-empts "wait, I thought we agreed type hints"):

| April tech design | Accepted KEP | Why |
|---|---|---|
| Type hints on nodes drive validation | `validator:` key in catalog | last-wins conflicts, mypy lies, cross-pipeline coupling |
| `_ValidatingDataset` wrapper | catalog `load()/save()` funnel | wrapper broke isinstance/repr/pickling |
| Pandera-only | pluggable `Validator` protocol | GX/Pydantic/non-tabular (Adeikalam's plots use case) |

---

## Frame 5 — Architecture: follow one load (10 min) — THE drawing

Recreate this as boxes + arrows, colour-coded. Vertical flow:

```
┌──────────────────────────────┐
│ conf/base/catalog.yml        │ 🟦
│   companies:                 │
│     validator: pkg.Schema    │ 🟩 (the key)
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ DataCatalog._add_from_config │ 🟦 box, 🟩 note:
│  captures ValidatorSpec      │ "strings only — NO imports,
│  (single funnel: explicit    │  no pandera, zero build cost;
│  entries AND factory         │  cleaned config copy — resolver
│  patterns)                   │  store never mutated"
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ catalog.load("companies")    │ 🟦
│   └► dataset.load()          │ 🟦 note: "dataset untouched —
│                              │  real type, real repr,
│                              │  picklable as-is. NO WRAPPER"
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ _maybe_validate(data,"load") │ 🟩 THE FUNNEL — guard ladder:
│  1 env var / flag off? ──────┼──► return data (zero cost)
│  2 no spec (dict miss)? ─────┼──► return data (99% path)
│  3 mode/enabled off? ────────┼──► return data
│  4 skip_load_after_save? ────┼──► return data
│  5 resolve_validator(spec)   │ 🟨 "first use only: import +
│     (cached thereafter)      │     adapt + cache"
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ validator.validate(data)     │ 🟩 Pandera adapter or ANY
│                              │    Validator protocol object
└──────┬───────────────┬───────┘
       ▼               ▼
  ✅ valid         ❌ invalid
  node receives    DataValidationError
  (possibly        enriched with dataset
  coerced) data    name + mode + grouped
                   failures
                   (severity: warn → log
                    + pass original)
```

Save-side mini-note under the diagram: *"save is symmetric — `dataset.save(_maybe_validate(data,'save'))` — validation runs BEFORE the write, invalid data never lands on disk."*

Three evidence stickies pinned to the diagram (your live-cite ammunition):
- "Dataset I/O hooks fire only in `kedro/runner/task.py` (seq 151–188, async 222–251) — notebooks fire none" → arrow to why the funnel, not hooks
- "pluggy discards hook return values → a hook can never hand the node coerced data"
- "`_add_from_config` is the single config funnel — factories included, so patterns Just Work"

---

## Frame 6 — The 7 design decisions (10 min) — seven cards

Each card: **DECISION** / *instead of* / because / evidence. Lay out 2 rows.

1. **Funnel, not wrapper** — *instead of `_ValidatingDataset` proxy* — wrapper breaks `isinstance`, must fake `_EPHEMERAL`/`_SINGLE_PROCESS`, breaks pickling for ParallelRunner, pollutes repr (deepyaman's complaint). Funnel: datasets stay exactly what YAML says. ⚠️ Flag openly: *this deviates from the pivot announcement — wrapper turned out strictly worse in build.*
2. **Schema-on-dataset** — *instead of type hints on nodes* — one entry one validator kills last-wins; catalog is the discoverable, grep-able source of truth (Adeikalam's production pattern, now native).
3. **Protocol, not Pandera coupling** — `validate(data) -> data`, any raise == failure — GX/Pydantic/custom/non-tabular all fit; Pandera is ~200 LOC of adapter against public API only.
4. **Lazy resolution + cheap pre-flight** — specs are strings at build (zero startup cost, factories work); import at first use; `find_spec` pre-flight warns on missing packages (same pattern as kedro's optional-rich checks); `kedro catalog validate --resolve-only` is the CI gate.
5. **Validate save AND load; no silent skip** — round-trips aren't identity-preserving (CSV drops dtypes); opt-in `skip_load_after_save` covers "this process wrote it" safely even under partial runs.
6. **Kill switch that actually kills** — `DATASET_VALIDATION` setting + `KEDRO_DATASET_VALIDATION` env var read inside `kedro.io` → governs every catalog instance incl. plugin-rebuilt ones (the telemetry case). Explicit API calls always validate (noklam's IDE case needs no flag).
7. **Funnel members NOT on `CatalogProtocol`** — adding members to a runtime_checkable protocol breaks every existing custom catalog at settings-load; instead a `hasattr` warning when a custom catalog would silently ignore validators.

---

## Frame 7 — Why not hooks / wrapper (5 min) — comparison table

| | Hooks | Wrapper (v1 proto) | **Funnel (chosen)** |
|---|---|---|---|
| Covers notebooks / IDE / CI | ❌ dataset hooks fire only in Task | ✅ | ✅ |
| Can coerce (`validate(data)->data`) | ❌ pluggy discards returns | ✅ | ✅ |
| Dataset repr / `isinstance` honest | ✅ | ❌ | ✅ |
| ParallelRunner pickling | ✅ | ❌ fragile | ✅ |
| `after_dataset_loaded` sees validated data deterministically | ❌ registration order | ✅ | ✅ |
| Core surface | none | medium | ~25 LOC in `kedro/io` (benchmarked no-op path) |

One honesty sticky (pre-empts Elena): *"The one real hooks advantage: Task fires hooks regardless of catalog class. A custom DATA_CATALOG_CLASS loses the funnel → hence the hasattr warning (decision 7)."*

---

## Frame 8 — Live demo (5 min)

Sticky: `python examples/demo_catalog_validation.py` (run in terminal, screen-share).
Checklist of the 5 money shots (tick live as you show them):
- [ ] Coerced dtypes on load (float64 id → int64)
- [ ] The grouped error report on invalid data
- [ ] Failed save → `file written? False`
- [ ] Non-tabular MetricsValidator (no pandera involved)
- [ ] `validate_catalog_dataset` → JSON-safe result + opt-out via env var

Backup sticky (in case of demo gremlins): screenshot of the demo output pasted on the frame beforehand. **Do this — take the screenshot tonight.**
Stats sticky: *"Prototype: 208 validation + 282 io tests green, ruff clean, 27 files +4643/−857, branch `prototype/kep7-v2-catalog-validation`."*

---

## Frame 9 — 🟥 DECISIONS TO LOCK TODAY (20 min) — the interactive core

Seven decision cards. Each: the question / options A|B / **my recommendation** pre-marked / a dot-vote zone / an empty "DECIDED:" sticky you fill in live. Timebox ~3 min each; anything that runs over → Parking Lot.

1. **Extras naming** — A: `kedro[validation]` = `pandera[pandas]` · B: per-backend `kedro[pandera-pandas]` / `[pandera-polars]` / `[pandera-pyspark]` forwarding 1:1 to pandera's own. **Rec: B** (deepyaman's review; base pandera ships NO backend since 0.24; mirrors kedro-datasets `ibis-duckdb` → `ibis-framework[duckdb]`). ⚠️ Own it upfront: the branch still ships `kedro[validation]` + two `pip install kedro[validation]` hint strings in core.py — "prototype predates this decision; the sweep is in PR 1." Bonus ammo: the `all` extra already excludes `validation` anyway (pyproject.toml:103).
2. **API name** — A: `validate_catalog_dataset` · B: `validate_dataset`. **Rec: B** (deepyaman's nit; unambiguous next to batch `validate_catalog`).
3. **pyspark** — A: ship experimental (adapter reads `df.pandera.errors`, since the backend never raises) · B: exclude from advertised matrix until Narwhals-backed pandera 0.32 ships. **Rec: B advertise / A code** — keep the accessor branch (it prevents silent false-greens) but market pandas+Polars only.
4. **Pandera floor** — `>=0.24` (first release with `pandera.pandas` namespace + per-backend extras). Action item: verify `failure_cases` shape stability 0.24→0.31.
5. **`ContextAwareValidator`** — A: ship `validate(data, *, context)` in v1 · B: reserve the name, ship later. **Rec: B** (funnel enrichment already covers error messages; don't widen the protocol before third parties use it).
6. **CLI default** — A: `kedro catalog validate` runs full data by default · B: resolve-only by default, `--all-data` explicit. **Rec: B** (unbounded CI cost otherwise). Sub-question: `severity: warn` findings → exit 0 by default, `--strict-warnings` flips.
7. **Entry-point group `kedro.validators`** — A: v1 · B: v1.x when a second backend actually exists. **Rec: B**.

Facilitation sticky: *"If a decision stalls >4 min: capture both positions on the card, assign an owner + deadline, move on. Locked > perfect."*

---

## Frame 10 — Risks register (reference — walk only if asked)

Top 6 as stickies (full 12 in the KEP):
- Raw-access bypass **by design**: `catalog.get(name).load()`, dataset `preview()` (Viz) skip validation — documented contract
- Coercion changes data identity (`coerce=True`) — docs + release-notes callout
- Hooks see pre-coercion data on save (task.py:183–188) — documented asymmetry
- Env-overlay validator loss (`local` redeclares entry without `validator:`) — CLI reports which validator resolved from where
- Spark/lazy backends: load-side validation triggers actions — guidance: `on: [save]` / sampling
- Generator nodes validate per-chunk — cross-chunk invariants not enforced; use `on: [load]`

---

## Frame 11 — Rollout plan (5 min)

Swimlane of 5 stickies with arrows:
**PR 1 core** (`kedro.validation` pkg + Pandera adapter + funnel + settings, ~1.5 wk) → **PR 2 surfaces** (API + CLI + warnings, ~1 wk) → **PR 3 docs** (validation page, pandera.md rewrite, release notes, ~0.5 wk) → **kedro-starters PR** (schemas/ scaffold, release-coupled) → **Outreach** (deepyaman on PRs — he asked; Niels/Neeraj on the adapter contract).

Note sticky: *"Prototype exists and is green — PRs 1–2 are productionise + review, not greenfield."*
Tracking sticky: *"Parent issue + 7 sub-issues structure ready to file after this session (decisions feed sub-issue 1)."*

---

## Frame 12 — Parking lot & actions

Empty frame, two columns: **Parking lot** (off-track topics land here alive, not dismissed) · **Actions** (owner + date). Pre-seed one action: *"Post decisions summary to #5390 — Sajid, tomorrow."*

---

## Facilitation crib (keep on a sticky near Frame 1)

- Open with: *"KEP is accepted — today is architecture walkthrough + locking 7 implementation decisions. Everything else → parking lot."*
- Frames 2–4 are momentum: don't take questions until Frame 5 ("hold that — the architecture frame answers it").
- Elena's questions will target Frame 5–6; deepyaman's target Frame 9 items 1–4; Nok's target Frame 8's API bits. Let the frames do the answering.
- When a question maps to a Frame 9 card, say: *"That's exactly decision N — let's lock it there in ten minutes."* This is a strength, not a dodge.
- End with reading the 7 "DECIDED:" stickies aloud. That's the artifact of the session.

# Tech design session script — Dataset Validation (KEP-10)

Directional script, not verbatim. Times are cumulative from session start. Target runtime: **~45 min of content in the 60-min slot** — the buffer is deliberate; decisions (Frame 9) absorb overruns, and ending early is a gift. Sentences in **bold** are worth saying close to verbatim.

---

## Before anyone joins (10 min prior)

- [ ] Terminal 1: `cd ~/GitHub/spaceflights-validation-demo && source .venv/bin/activate && export KEDRO_DISABLE_TELEMETRY=1` → sanity: `which kedro` shows `.venv`, `kedro --version` shows 1.2.0
- [ ] Terminal 2: `cd ~/GitHub/kedro` (must be on `prototype/kep7-v2-catalog-validation`), conda env activated for the encore
- [ ] `./demo_restore.sh` run once (in case last rehearsal left data corrupted)
- [ ] Miro open on Frame 1; backup screenshots pinned to Frame 8; editor tabs: `catalog.yml`, `schemas/companies.py`
- [ ] Recording on; ask someone to co-note decisions as backup

---

## 0:00 — Opening (Frame 1, 2 min)

> Thanks everyone. Quick framing before we start, because it changes how today works: **the KEP is accepted — plus-three from the TSC — so today is not "should we do this." It's an architecture walkthrough of the working prototype, and then locking seven implementation decisions so PRs can start.**
>
> Rough shape: fifteen minutes of story and architecture, five of demo, and then the biggest block is the decisions — that's the actual point of the session. If a question comes up that maps to one of the seven decisions, I'll ask to hold it for that section rather than dodge it. Anything off-track goes to the parking lot with an owner — nothing gets lost.

[Point at the agenda stickies. Move on briskly — momentum matters in the first 10 minutes.]

---

## 0:02 — The journey (Frame 2, 3 min)

[Walk the timeline left to right. This section's real job: make the room feel authorship of the design.]

> Quick recap of how we got here, because the path *is* the design rationale.
>
> February — Rashida opened the initiative: one cohesive validation strategy. April — first tech design, we prototyped the type-hint approach: Pandera schemas on node signatures, discovered by walking pipelines, enforced by a wrapper dataset. It worked, and then review found the cracks — [point at each quote sticky]:
>
> deepyaman: if two pipelines annotate the same dataset, **the last one silently wins** — and if validation is tied to datasets, the schema should live *on the dataset*. Adeikalam, from real production use: schemas next to nodes bloat pipelines and couple them. Nok: needs a global off-switch and an API his VSCode extension can call.
>
> So we paused the vote and pivoted: **schema on the dataset, in the catalog, with a pluggable validator protocol.** Reposted as KEP-10, deepyaman came back with "much improved, no blockers," and the vote passed.
>
> **Everyone in this room has a fingerprint on this design.** What I'm showing today is your feedback, built.

---

## 0:05 — The proposal in one screen (Frame 3, 4 min)

> Here's the entire user experience. [Point at the three code blocks in turn.]
>
> One new line in the catalog — `validator:` pointing at a schema. The schema is plain Pandera, living in `src/<package>/schemas/` — that's a *convention*, mirroring how parameters work; any importable path is fine. And the node? **Completely unchanged. Plain Python, plain DataFrame. Zero validation machinery in user pipeline code.**
>
> What that one line buys: [outcome stickies] validation on load *and* save — invalid data never gets written; it works in notebooks and the IDE and CI, not just `kedro run`; one dataset has exactly one validator, so the silent-conflict bug from v1 isn't mitigated — **it's structurally impossible**; and the backend is a protocol — `validate(data) in, data out, raise on failure` — so Pandera is just the reference implementation. Great Expectations, Pydantic, custom checks on matplotlib plots — same key.
>
> And this [the error block — read two lines of it aloud] is what failure looks like. Every failed check, grouped, with examples, naming the dataset and whether it failed on load or save. **Bounded output even on a ten-million-row frame** — the full Pandera report stays attached underneath.

[Frame 4, 30 seconds, don't linger:]

> One slide of honesty for anyone who remembers April: three things changed since that session — declaration moved from type hints to the catalog, the wrapper became a funnel, and Pandera-only became a protocol. Each was driven by the review feedback you just saw. I'll show why the wrapper died in the architecture.

---

## 0:10 — Architecture: follow one load (Frame 5, 8 min + Q&A)

[This is the deep frame — slow down. Walk the diagram top to bottom. This is where Elena's questions will land; that's by design.]

> Let's follow one `catalog.load("companies")` through the system.
>
> **Catalog build.** Every entry — explicit or dataset-factory pattern — passes through one method, `_add_from_config`. That's where the `validator:` key is captured into a spec. Key property: **at build time this is strings only. No imports, no pandera, zero cost.** A 500-entry catalog builds exactly as fast as before. And because factory patterns resolve through the same funnel at materialisation, patterns just work — which, Elena, is the answer to your April concern about wrapping datasets a run never touches: nothing heavier than string parsing happens until a dataset is actually used.
>
> **The load.** The dataset loads *untouched* — real class, real repr, picklable, no wrapper anywhere. On the way out, data passes through `_maybe_validate` — the funnel. It's a guard ladder ordered cheapest-first: kill switch off? return. No spec for this name? — that's a dictionary miss, **the 99% path, effectively free**. Wrong mode, disabled? return. Only then, on *first use*, does the validator resolve: import, hand to the Pandera adapter or protocol-check, cache.
>
> **The outcome.** Pass — the node gets the frame, possibly dtype-coerced, and that's a documented contract. Fail — the funnel enriches the error with the dataset name and mode — the schema itself is deliberately dataset-agnostic, so the same schema can guard `X_train` and `X_test` — and raises the grouped report you saw. Or, with `severity: warn`, logs it and passes the original data through — the adoption knob.
>
> Save is symmetric with one bonus: **validation runs before the write, so invalid data never lands on disk.**
>
> Why here and not hooks? Two mechanical facts: [evidence stickies] **dataset I/O hooks only fire inside the runner's Task** — a notebook load fires none — **and pluggy discards hook return values**, so a hook can never hand the node coerced data. The protocol is unimplementable as a hook. And hook users lose nothing: they still fire in the same places, and now `after_dataset_loaded` deterministically sees *validated* data instead of depending on plugin registration order.

> [Open the floor deliberately:] **Questions on the mechanics — this is the right frame for them.** [Budget ~3 min. If a question is decision-shaped — extras, naming, pyspark — "that's exactly decision N, let's lock it there in ten minutes." If it's a deep-dive — spec lifecycle, pickling, custom catalogs — answer from the crash-course material, cite the file, keep each under 90 seconds.]

---

## 0:18 — Decisions already made + the honest trade-offs (Frames 6–7, 5 min)

[Don't read all seven cards. Headline them, then spend the time on one card and the table.]

> Seven design decisions are locked in the accepted KEP — they're on this frame with their rejected alternatives, I won't read them all. The one I want to flag openly is the first: **the funnel deviates from what I announced in the pivot** — I said the wrapper would carry over. Building it proved the wrapper strictly worse: it breaks `isinstance` in version handling, fakes runner flags, breaks pickling under ParallelRunner, and pollutes the repr — which was deepyaman's original complaint. Deleting it resolved that complaint by construction. The funnel costs about 25 lines in `kedro/io` — yes, the hottest path, and the no-op benchmark ships with PR 1 to defend that.
>
> [Frame 7 table, briefly:] The comparison in one view — hooks fail the coverage and coercion rows for mechanical reasons, the wrapper fails the identity rows. And one honest concession [the sticky]: **the single genuine hooks advantage is that Task fires them regardless of catalog class.** A fully custom `DATA_CATALOG_CLASS` loses the funnel — so the context warns loudly when that happens rather than degrading silently. That's decision 7's design.

---

## 0:23 — Live demo (Frame 8, 6 min)

[Switch to Terminal 1. Narrate over the run; the one-liners are in the run book. Compressed sequence:]

> Enough slides — this is a real spaceflights project running this branch.
>
> [Show `catalog.yml` + schema file, 20s] One line on `companies`, long form with `on: [save]` on the preprocessed output. Schemas in `src/<pkg>/schemas/`.
>
> [`kedro run --pipeline data_processing`] Both contracts active — green, six seconds.
>
> [`./demo_break.sh` → rerun → scroll to the bottom] The supplier broke the file overnight. **Three checks failed, grouped, with examples, at the I/O boundary — before any node ran. Nothing was written.**
>
> [`KEDRO_DATASET_VALIDATION=0` → rerun] And here's the same broken file with validation switched off — **this is what today's Kedro gives you: `ValueError: could not convert string to float` somewhere inside a node.** That contrast is the whole KEP. And that env var is the 3am kill switch — reaches every catalog instance, no redeploy.
>
> [`./demo_restore.sh`. If time, the API snippet:] From a notebook: `catalog.load` validates — note the id column came back int64, coerced by the contract, and the node still gets a plain DataFrame — annotations stay documentation, per Ravi's thread question. And `validate_catalog_dataset` **never raises** — status, structured failures, JSON-safe — Nok, that's the extension contract, I want your eyes on it in PR 2.
>
> [30s, Terminal 2 — only if running well on time:] The script encore shows the non-tabular case — a metrics dict validated with no pandera anywhere. Otherwise: "the non-tabular and opt-out cases are in a script I'll link in the notes."
>
> Behind this: **208 validation tests, 282 io tests, green.**

[If the demo misbehaves: don't debug on camera — "here's last night's run" → pinned screenshots, keep narrating.]

---

## 0:29 — DECISIONS TO LOCK (Frame 9, ~18 min — the point of the session)

[Mechanics: per card — 30s framing, recommendation, ask "objections or alternatives?", capture DECIDED on the sticky, move. If one stalls past 4 min: both positions on the card, owner + deadline, parking lot. Take them in this order — quick wins first:]

**D2 — API name (2 min).**
> Two accepted docs drifted on this — `validate_catalog_dataset` versus `validate_dataset`. deepyaman suggested the short form, Nok's the main consumer and prefers it, the catalog is already the first argument. **Recommend `validate_dataset`. Nothing has shipped, so the rename is free today and a deprecation cycle later.** Objections? → DECIDED.

**D1 — Extras naming (3 min).**
> Current branch ships `kedro[validation]` = `pandera[pandas]`. deepyaman pushed back and Ravi +1'd: named-backend extras. The forcing fact: **since 0.24, base pandera ships no dataframe backend — a generic extra silently picks one for the user.** Recommend per-backend: `kedro[pandera-pandas]`, `[pandera-polars]`, `[pandera-pyspark]` — thin 1:1 forwarders, exactly the kedro-datasets ibis convention. Owning it upfront: the prototype predates this — pyproject and two install-hint strings say `kedro[validation]`; the sweep is a named PR-1 item. → DECIDED.

**D6 — CLI default (3 min).**
> `kedro catalog validate` in CI: full-data by default, or resolve-only by default with `--all-data` explicit? **Recommend resolve-only — unbounded data loads should never be the default in CI**; resolve-only catches typo'd paths and missing deps in milliseconds, which is also the fail-fast answer for lazy resolution. Sub-call: `severity: warn` findings exit 0 by default, `--strict-warnings` flips. → DECIDED.

**D3 — pyspark (3 min).**
> Pandera's pyspark backend is genuinely different: it never raises — errors land on an accessor — and it lacks element-wise checks and sampling. deepyaman said deprioritize; I agree. **Recommend: keep the adapter code — it exists purely so invalid Spark data can't silently pass — but advertise pandas + Polars only, revisit when the Narwhals-backed backend ships.** → DECIDED.

**D4 — Pandera floor (2 min).**
> `>=0.24` — first release with the `pandera.pandas` namespace and per-backend extras. One action item attached: verify the `failure_cases` shape is stable from 0.24 to current per backend — that's part of the Pandera-maintainer review. → DECIDED + action.

**D5 — ContextAwareValidator (2 min).**
> Optional richer protocol — `validate(data, context)` with dataset name and mode. **Recommend: reserve the name, don't ship it** — funnel enrichment already puts dataset and mode on every error, and I don't want to widen a protocol before a single third party implements it. → DECIDED.

**D7 — Entry-point group (1 min).**
> `kedro.validators` for pip-installable adapters: v1 or v1.x? **Recommend v1.x — when a second backend actually exists.** Custom validators already work today via the class path; this is only about *distribution*. → DECIDED.

[If ahead of time here, invite: "anything anyone expected on this list that isn't?"]

---

## 0:47 — Rollout + actions (Frames 11–12, 4 min)

> The plan from here — and the key fact: **the prototype is built and green, so PRs 1 and 2 are productionise-and-review, not greenfield.** PR 1: the validation package, adapter, funnel, settings — plus today's decisions swept through it — about a week and a half. PR 2: the API and CLI. PR 3: docs, including rewriting the pandera page to lead with `validator:`. A small release-coupled starters PR — one example schema, commented-out catalog line. And outreach: deepyaman, you asked to be in the Pandera review — you're named on it; I'll also reach out to Niels and Neeraj, and credit kedro-pandera as the inspiration in the launch write-up.
>
> Asks before we close: **a reviewer for PR 1 from the catalog side** [look at Elena], **Nok on PR 2 for the extension contract**, and I'll post today's decisions to the KEP thread and the parent initiative by tomorrow. Anything for the parking lot before we wrap?

## 0:51 — Close (1 min)

> [Read the seven DECIDED stickies aloud, one breath each.] That's the artifact of this session. Thanks all — this design is genuinely better because of the review it got. PRs start this week.

[Done — ~52 min worst case, likely under 45. Do not fill remaining time; end.]

---

## Contingencies

- **Running hot at 0:20** (architecture Q&A overran): compress Frames 6–7 to 2 min ("the cards are on the board, the table says why not hooks — read at leisure") and cut the script encore. **Never compress Frame 9.**
- **A decision deadlocks:** capture both positions, name an owner and a 48h async deadline in the thread, move on. Locked > perfect, but six locked + one owned beats seven rushed.
- **Demo gremlin:** screenshots, keep narrating. Never debug live.
- **Three things NOT to say** (fact-checked traps): don't cite "hooks fire only at lines 151–188" (async paths fire them too — say "only in Task"); don't quote a benchmark number (none exists yet — "ships with PR 1"); don't claim the pre-flight runs at catalog build (it exists but isn't wired — "wiring is PR-1 scope").
- **Deep technical challenge you can't place:** "Good catch — let me take that as a PR-1 review item rather than improvise an answer now." (Concede fast; the Q&A bank shows this wins with this room.)

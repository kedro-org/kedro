# Verbatim script, in my words

Read-aloud version. Matches the Miro board as built (4 open decision cards). Square brackets are stage directions, everything else is literally what to say. Don't worry about matching it exactly on the day, it's a safety net not a cage.

---

## Opening [Frame 1]

Right, thanks everyone for joining. Quick bit of framing before we start because it changes how today works.

The KEP is accepted, we got plus three from the TSC, so today isn't about whether we should do this. What I want to do is walk you through how the working prototype is actually built, show it running, and then spend the biggest chunk of the session locking the open implementation decisions so I can start splitting the PRs.

If a question comes up that's one of those decisions, I'll ask to hold it for that section. I'm not dodging it, we'll lock it properly there. Anything off topic goes in the parking lot with an owner so nothing gets lost.

## The journey [Frame 2]

Quick recap of how we got here, because the history basically explains the design.

Rashida opened the parent initiative back in February, one cohesive validation story for Kedro, parameters and datasets. In April we did the first tech design, that was the type hints approach. Pandera schemas on node signatures, discovered by walking the pipelines, enforced through a wrapper dataset. The prototype worked, but when KEP-7 went up for review it got some really good pushback.

[point at the quotes]

deepyaman pointed out that if two pipelines annotate the same dataset with different schemas, the last one silently wins, which is a genuinely nasty bug. And that if validation is about datasets, the schema should live on the dataset. Adeikalam, whose team actually runs this pattern in production, said schemas next to nodes bloat the pipelines and couple them together, and his team already keeps schemas in a dedicated folder with a validate method. And Nok said he needs a global off switch, plus an API his VSCode extension can call.

So we paused the vote and pivoted. Schema goes on the catalog entry, enforcement moves into the catalog itself, and the backend becomes a pluggable protocol. That went back up as KEP-10, deepyaman came back with much improved, no blockers, and it passed.

So honestly, everyone in this room shaped this design. What I'm showing you today is your feedback, built.

## The new way of validating [Frame 3]

This is the whole user experience, three files.

[point left to right]

One new line in the catalog. A validator key pointing at a schema. The schema itself is plain Pandera, it lives in a schemas folder under src, and that's a convention not a requirement, any importable path works, same idea as how parameters have a conventional home. And the node, completely unchanged. Plain Python, plain DataFrame, no validation machinery anywhere in pipeline code.

What that one line buys you. Validation on load and on save, and save validation runs before the write so invalid data never lands on disk. It works everywhere the catalog works, notebooks, the IDE, CI, not just kedro run. One dataset has exactly one validator, so that silent conflict bug from the first design isn't mitigated, it literally can't happen. And the backend is a small protocol, validate data in, data out, raise on failure. Pandera is the reference implementation, but Great Expectations, Pydantic, or a custom check on a matplotlib figure all fit the same key.

And this is what failure looks like. [read two lines off the error block] Every failed check at once, grouped, with examples, naming the dataset and whether it failed on load or save. That output stays this size on a ten million row frame, and the full Pandera report is still attached underneath if you want to dig.

## What changed since April [Frame 4]

For anyone whose mental model is still the April session, one slide of honesty. Three things changed. Declaration moved from type hints to the catalog. The wrapper became validation inside catalog load and save. And Pandera-only became a protocol. Each of those came straight from the review feedback you just saw. I'll show you why the wrapper died in a second.

## Architecture [Frame 5]

Before we go into the internals I want to be upfront about one thing, since we're about to read code together. I used Claude pretty heavily building this. The prototype implementation, the test suite, a lot of the design exploration, all AI assisted. The design decisions came out of the KEP review process, your feedback drove the pivot, and I own every call in here. And everything you're about to see I've reviewed, run and tested myself, the demo is a real project I've broken and fixed with my own hands. So same deal as any code with my name on it, the PRs get full review rigour and I'd ask you to judge it exactly that way.

[straight into the diagram, no pause]

Okay, let's follow one catalog dot load of companies through the system.

Catalog build first. Every entry, whether it's written explicitly or comes from a dataset factory pattern, goes through one method, add from config. That's where the validator key gets captured into a spec. And the important property here, at build time this is strings only. No imports, no pandera, nothing. A five hundred entry catalog builds exactly as fast as it does today. Factory patterns resolve through the same method when they materialise, so patterns just work. And Elena, that's also the answer to your question from April about doing work for datasets a run never touches. Nothing heavier than string parsing happens until a dataset is actually used.

Then the load. The dataset loads completely untouched. Real class, real repr, picklable, there is no wrapper anywhere. On the way out the data passes through maybe validate, which is a guard ladder ordered cheapest first. Kill switch off, return. No spec for this name, that's a dictionary miss, that's the ninety nine percent path, basically free. Wrong mode or disabled, return. And only then, on first use, does the validator actually resolve. Import it, hand it to the Pandera adapter or protocol check it, cache it.

Then the outcome. If it passes, the node gets the frame, possibly with dtypes coerced, and that's a documented contract. If it fails, the funnel adds the dataset name and the mode to the error, because the schema itself deliberately doesn't know about datasets, the same schema can guard X train and X test. And you get that grouped report. Or, with severity warn, it logs the same report and passes the original data through, which is the adoption knob for legacy pipelines.

Save is the mirror image with one bonus, validation runs before the write, so bad data never touches disk.

And the obvious question, why here and not hooks. Two mechanical facts. Dataset IO hooks only fire inside the runner's Task, so a notebook load fires nothing, the funnel covers both. And pluggy throws hook return values away, so a hook can raise but it can never hand the node coerced data, which means this protocol simply can't be built as a hook. Hooks lose nothing by the way, they keep firing in the same places, and after dataset loaded now always sees validated data instead of depending on plugin registration order.

Right, questions on the mechanics, this is the frame for them.

[take about 3 minutes. decision shaped questions: "that's exactly one of the open decisions, let's lock it there in a few minutes". deep dives: answer, cite the file, keep each under 90 seconds]

## Design decisions already made [Frame 6, brief]

Seven decisions are already locked in the accepted KEP, they're on the board with the reasoning, I won't read them out. The one I want to flag openly is the funnel itself, because it deviates from what I said in the pivot announcement. I said the wrapper would carry over. Building it proved it strictly worse. It breaks isinstance in the version handling, it has to fake runner flags, it breaks pickling under ParallelRunner, and it pollutes the repr, which was deepyaman's original complaint. Deleting the wrapper fixed that complaint outright. The cost is about twenty five lines in kedro io, and yes that's the hottest path, the no op benchmark ships with PR 1 to back that up.

[if the hooks comparison table is useful here, pull it up: "same story in one table, hooks fail on coverage and coercion for mechanical reasons, the wrapper fails on identity. And one honest concession, the single real hooks advantage is that Task fires them whatever catalog class you use, so a fully custom catalog class loses the funnel, which is exactly why we warn loudly in that case instead of failing silently."]

## Demo

Enough slides. This is a real spaceflights project running this branch.

[terminal 1]

One line on companies in the catalog, long form with on save for the preprocessed output, schemas in the schemas folder. That's the whole diff from a stock spaceflights project.

[run: kedro run --pipeline data_processing]

Both contracts active. Green, about six seconds.

[run: ./demo_break.sh, then kedro run again, scroll to the bottom]

Now the supplier has broken the file overnight. Three checks failed, grouped, with the actual bad values, at the IO boundary, before any node ran. And nothing was written.

[run: KEDRO_DATASET_VALIDATION=0 kedro run --pipeline data_processing]

And here's the same broken file with validation switched off. This is what today's Kedro gives you. ValueError, could not convert string to float, somewhere inside a node. That contrast is basically the whole KEP. And that env var doubles as the emergency kill switch, reaches every catalog instance, no redeploy.

[run: ./demo_restore.sh]

[if time, the notebook bit]

From a notebook, catalog load validates too, and notice the id column came back as int64, the contract coerced it, and the node still gets a plain DataFrame. Ravi, that's your question from the thread, annotations stay as documentation. And validate catalog dataset never raises, it returns status and structured failures, JSON safe. Nok, that's the extension contract, I want your eyes on it in PR 2.

Behind all this, two hundred and eight validation tests and two hundred and eighty two io tests, green.

[if the demo misbehaves: "I've got last night's run here", switch to screenshots, keep talking]

## Open decisions [pink cards, the point of the session]

Okay, the actual point of today. Four decisions to lock. For each one I'll give you the options and my recommendation, tell me if I'm wrong.

First, the API name. Two names floating around the docs, validate catalog dataset versus validate dataset. deepyaman suggested the short one, Nok as the main consumer prefers it, and the catalog is already the first argument so the long prefix is redundant. My recommendation is validate dataset. Nothing has shipped so the rename is free today and a deprecation cycle later. Objections?

[write it on the sticky]

Second, extras naming. The branch currently ships kedro validation equals pandera pandas. deepyaman pushed back on that and Ravi agreed, and the forcing fact is that since pandera 0.24 the base package ships no dataframe backend at all, so a generic extra silently picks one for you. Recommendation is per backend extras, kedro pandera pandas, pandera polars, pandera pyspark, thin one to one forwarders, exactly the convention kedro datasets already uses for ibis. And owning the gap, the prototype predates this decision, pyproject and a couple of install hints still say kedro validation, that sweep is a named PR 1 item.

Third, the CLI default. When someone types kedro catalog validate in CI, does it load and validate all the data by default, or does it resolve only by default with all data as an explicit flag. Resolve only means it imports and constructs every declared validator without loading anything, so it catches typo'd paths and missing packages in milliseconds. My recommendation is resolve only as the default, because unbounded data loads should never be a CI default, and this also buys back the fail fast that lazy resolution gives up. Small sub call while we're here, severity warn findings exit zero by default with a strict warnings flag to change that.

Fourth, the entry point group. kedro dot validators for pip installable adapters, do we ship it in v1 or wait. Custom validators already work today through the class path, this only changes distribution. Recommendation is wait until a second backend actually exists, and just reserve the group name in the docs.

[if pyspark or the pandera version floor come up, and they probably will:]

On pyspark, pandera's pyspark backend is genuinely different, it never raises, errors accumulate on an accessor, and it's missing element wise checks and sampling. deepyaman said deprioritise and I agree. The adapter code stays, it exists purely so invalid Spark data can't silently pass, but the advertised support matrix is pandas and Polars, and we revisit when the Narwhals backed backend ships.

On the version floor, greater or equal 0.24, that's the first release with the pandera dot pandas namespace and per backend extras. One action item on it, verify the failure cases shape is stable from 0.24 to current, that folds into the Pandera maintainer review.

[if a decision stalls more than about 4 minutes: "let me capture both positions on the card, I'll take an owner and we close it async in 48 hours in the thread. Locked beats perfect."]

## Rollout

The plan from here. The key thing is the prototype already works and it's green, so the PRs are about productionising, not building from scratch.

PR 1 is the core. The validation package, the Pandera adapter, the catalog funnel, settings, plus everything we just decided swept through it. PR 2 is the API and the CLI. Tests come in alongside those PRs, the funnel, runners, factories, lifecycle, CLI. Then docs, a new data validation page and rewriting the pandera page to lead with the validator key. And a small starter example showing the validator key.

Two asks before we wrap. I need a catalog side reviewer for PR 1, it touches the hottest path in kedro io and deserves that scrutiny. [look at Elena] And Nok, I'd like you on PR 2, the ValidationResult payload is your extension's contract so it should be reviewed by its consumer.

I'll post today's decisions to the KEP thread and the parent initiative, and file the tracking issues right after this.

## Close

[read the DECIDED stickies out loud, one breath each]

That's the artifact of today. Thanks everyone, this design is genuinely better because of the review it got. PRs start this week.

---

## Pocket lines

- Hooks precision, if quoted back: "only in the runner's Task", never "only lines 151 to 188", the async path fires them too.
- Benchmark numbers: "not measured yet, the benchmark ships with PR 1", never quote a number.
- Pre flight: "implemented but not wired yet, the wiring is PR 1 scope."
- AI question pushed further: "the KEP doc says the same thing, deepyaman spotted it and plus one'd anyway. What matters is the verification, the test suite, a real demo project, normal PR review. Happy to talk tooling after, parking lot."
- Anything I can't place: "Good catch, let me take that as a PR 1 review item rather than improvise now."

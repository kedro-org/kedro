# Kedro documentation style guide

A synthesised reference for anyone writing Kedro docs. Rules here draw from the [Kedro wiki style guide](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide), the [Microsoft Writing Style Guide](https://learn.microsoft.com/en-gb/style-guide/welcome/), and the [Google inclusive documentation guide](https://developers.google.com/style/inclusive-documentation).

When this guide is silent on something, defer to the Microsoft Writing Style Guide.

---

## Voice and tone

Kedro docs have three qualities: **simple**, **friendly**, and **functional**.

- **Simple**: clear and direct. No vagueness, no jargon, no unnecessary words.
- **Friendly**: approachable, never negative or condescending. Write like a knowledgeable colleague explaining something, not a manual.
- **Functional**: get to the point. Tell the reader what they need to do or know, then stop.

---

## Language

### UK English

Kedro uses UK English. Common differences from US English:

| UK (use this) | US (not this) |
|---|---|
| customise | customize |
| initialise | initialize |
| colour | color |
| behaviour | behavior |
| centre | center |
| catalogue | catalog (exception: see [Kedro terms](#kedro-specific-terms)) |
| licence (noun) | license (noun) |
| organise | organize |

### Contractions

Use contractions to keep the tone friendly: _it's, you'll, you're, we're, let's, don't, can't_. They make text sound like a real person wrote it.

### Active voice

Write in active voice. The "by zombies" test: if you can add "by zombies" after the verb and the sentence still makes sense, rewrite it.

| Passive (avoid) | Active (use) |
|---|---|
| The pipeline is run by the runner. | The runner executes the pipeline. |
| Parameters can be configured in `parameters.yml`. | Configure parameters in `parameters.yml`. |
| Credentials should not be committed to version control. | Don't commit credentials to version control. |

### Imperative mood

Start instructions with a verb. Remove "you can" and "you should" — they add length and weaken the instruction.

| Weak | Strong |
|---|---|
| You can run the pipeline with `kedro run`. | Run the pipeline with `kedro run`. |
| There is a way to create custom datasets. | Create a custom dataset by … |
| You should avoid storing credentials in `base`. | Avoid storing credentials in `base`. |

---

## Structure and length

### Sentence length

Keep sentences to 30 words or fewer. If a sentence is longer, split it. Shorter sentences are easier to scan and easier to translate.

### Get to the point first

Lead with the most important information. Don't bury the key fact or action in the middle of a paragraph.

| Back-loaded | Front-loaded |
|---|---|
| If you want to run only part of your pipeline, there is a flag you can use called `--to-nodes`. | Use `--to-nodes` to run a subset of your pipeline. |

### Paragraphs

One idea per paragraph. Three to five sentences maximum.

### Be brief

Prune every excess word. Ask: does this word or sentence add information the reader needs? If not, delete it.

---

## Headings

- Use sentence case: "Create a custom dataset" not "Create A Custom Dataset".
- Don't add end punctuation to headings.
- Use imperative mood for how-to headings: "Configure credentials" not "Configuring credentials".
- Use noun phrases for concept and reference headings: "Pipeline slicing" not "How to slice a pipeline".
- Capitalise proper nouns and Kedro-specific terms that are always capitalised (see [Kedro terms](#kedro-specific-terms)).

---

## Lists

- Capitalise the first word of each item.
- Omit trailing full stops unless items are complete sentences.
- Use **numbered** lists only for sequential steps or when you refer back to items by number.
- Use **unordered** lists for everything else — options, features, related items.
- Use the Oxford (serial) comma in running prose: "nodes, pipelines, and datasets" not "nodes, pipelines and datasets".

---

## Punctuation

- Use one space after full stops, not two.
- Use em dashes without spaces on either side: "the pipeline—or any subset of it—can be run independently". Not " — " (spaced).
- Use a colon to introduce a list or a code block, not a semicolon.
- Skip end punctuation on list items of three or fewer words.

---

## Code and commands

- Always specify a language lexer on code blocks: `python`, `bash`, `yaml`, `json`, `toml`.
- Use `bash` for terminal commands. Do **not** include a shell prompt (`$` or `>`).
- For Kedro CLI examples, follow the pattern: `kedro <command> --<flag>=<value>`.
- Use inline code formatting for: file names, directory names, class names, method names, parameters, config keys, and CLI flags.
- Do not use inline code for general concepts: write "the data catalog", not "`the data catalog`".

---

## Links

- Embed links in descriptive text. The link text should make sense when read alone.
- Don't use "here", "this", "click here", or "read more" as link text.
- For internal links, use relative paths from the current file.
- For Kedro API cross-references, use MkDocs autorefs syntax: `[kedro.io.AbstractDataset][]`.

| Avoid | Use |
|---|---|
| Download the starter [here](link). | [Download the starter](link). |
| See [this page](link) for more information. | See [configuration basics](link) for more information. |

---

## Admonitions

Use MkDocs admonition blocks sparingly. Only use them when the information is genuinely important enough to interrupt the reading flow.

```markdown
!!! note
    Useful information that is not critical to the task.

!!! warning
    Information that could cause data loss or unexpected behaviour if missed.

!!! important
    A prerequisite or constraint the reader must know before proceeding.
```

Do not use plain bold text as a substitute for a `!!! note` block, and don't use `Note that` as a sentence opener — it is flagged by Vale. Use the admonition or rephrase.

---

## Kedro-specific terms

Use these terms consistently. Inconsistency confuses readers and breaks docs search.

| Write | Not |
|---|---|
| `dataset` | `data set` |
| data catalog | Data Catalog (the concept) |
| `DataCatalog` | `Data Catalog` (the class — use inline code) |
| `Hooks` | `hooks` (the Kedro Hooks system, capitalised following React convention) |
| `pipeline` | `Pipeline` (the concept — use lowercase; reserve `Pipeline` for the class in code) |
| backend | back end |
| frontend | front end |
| runtime | run time |
| Kedro | kedro (always capitalise the product name) |
| Kedro-Viz | KedroViz, kedro-viz |

### Terms from the Vale word list

The following substitutions are enforced by Vale. Apply them in prose:

| Use | Not |
|---|---|
| acknowledgment | acknowledgement |
| autocomplete | auto-complete |
| few, several, or many | a number of |
| and / or | and/or |
| examine, investigate, or analyse | drill down, drill into |
| determine | figure out |
| customise, optimise, or refine | fine-tune |
| generally or usually | for the most part |
| consider | keep in mind |
| use | leverage, utilize |
| after | once (when meaning "after") |
| select or click | hit |
| to | in order to |
| real-time | on the fly |
| see or read | refer to, visit |
| trade-off | tradeoff |
| use | leverage |
| with or through | via |

---

## Capitalisation reference

Always capitalise:

- Kedro, Kedro-Viz
- Product and service names: Python, GitHub, AWS, Docker, Spark, Databricks, Airflow, etc.
- Acronyms: API, CLI, YAML, JSON, IDE, CI/CD, SSH, IAM, URLs
- `Hooks` (Kedro Hooks system)

Never capitalise:

- pipeline, node, dataset (the concepts)
- cloud, internet, machine learning, analytics
- General terms: catalog, configuration, parameter, environment

---

## Inclusive language

### Gender

- Use gender-neutral language. Avoid "he", "she", "his", "hers" in generic references.
- Use "they", "their", or "them" for a generic singular person.
- Rewrite to use second person ("you") wherever possible — it is cleaner and more direct.
- Use role-based terms instead of gendered ones.

| Avoid | Use |
|---|---|
| man-hours | person-hours |
| mankind | people, humanity |
| manpower | workforce, staff |
| chairman | chair, moderator |
| salesman | sales representative |

### Disability

- Focus on the person, not the disability: "readers who are blind or have low vision" not "the blind".
- Don't imply pity: avoid "suffering from", "stricken with", "victim of", "wheelchair-bound".
- Don't use disability as a metaphor: avoid "blind to", "crippled by", "dumb" (meaning unclear).
- Don't call non-disabled people "normal" or "healthy" as a contrast.
- Avoid euphemisms: "differently abled" and "special needs" are considered patronising by many disability advocates.

| Avoid | Use |
|---|---|
| The blind | People who are blind or have low vision |
| Suffers from | Has |
| Blind to the problem | Unaware of the problem |
| Crippled by legacy code | Slowed by legacy code |
| Dumb variable name | Unclear variable name |

### Non-inclusive technical terms

These terms have problematic historical associations. Use the replacements in all new documentation.

| Avoid | Use |
|---|---|
| whitelist | allowlist |
| blacklist | denylist |
| master / slave | primary / replica, primary / secondary, controller / worker |
| sanity check | check, verify, validate |
| dummy value | placeholder value, example value |
| native speaker | (rephrase to discuss the feature directly) |

When a Kedro API or third-party tool still uses these terms in its interface, format them in code (`master`, `whitelist`) and use the preferred term in surrounding prose.

### Cultural inclusivity

- Avoid US-centric references, examples, and holidays unless the content is specifically about the US.
- Use varied names in examples — include names from multiple cultural backgrounds.
- Don't generalise about countries, regions, or cultures.
- Avoid slang, especially idioms that may not translate or that could be considered cultural appropriation.

### Violent language

Avoid figurative violent language in prose.

| Avoid | Use |
|---|---|
| kill the process | stop the process, terminate the process |
| hit the endpoint | call the endpoint, send a request to the endpoint |
| nuke the database | delete the database, drop all tables |
| hang (as in "the process hangs") | stop responding, become unresponsive |

---

## What not to write

These are common patterns that make docs harder to read. Vale flags most of them.

| Pattern | Why | Fix |
|---|---|---|
| "simply", "easily", "quickly", "just" | Implies the task is trivial — alienating when it isn't | Delete |
| "please" | Unnecessary in instructions | Delete |
| "obviously", "of course", "clearly" | Condescending | Delete |
| "Note that" | Verbose opener | Use `!!! note` or rephrase |
| "in order to" | Verbose | Replace with "to" |
| "utilize" | Bureaucratic | Replace with "use" |
| "leverage" | Jargon | Replace with "use" |
| "allows" | Incorrect | Replace with "enables" |
| "via" | Ambiguous | Replace with "with" or "through" |
| "once" (meaning "after") | Ambiguous | Replace with "after" |
| Weasel adverbs: "absolutely", "basically", "arguably" | Hedge without adding meaning | Delete |
| Too-wordy phrases: "a number of", "due to the fact that" | Verbose | Use shorter equivalents |

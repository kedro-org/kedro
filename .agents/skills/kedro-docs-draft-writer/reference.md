# Kedro docs draft writer — Reference

Detailed reference for the `kedro-docs-draft-writer` skill. Use section headers to find what you need.

The full style guide is in [style-guide.md](style-guide.md). The sections below are quick-lookup summaries used during drafting and Vale triage.

______________________________________________________________________

## Directory map

Use this to pick the right `docs/` subdirectory.

| Topic area                                                 | Directory                        |
| ---------------------------------------------------------- | -------------------------------- |
| First steps, installation, project concepts                | `docs/getting-started/`          |
| Creating projects, starters, project structure             | `docs/create/`                   |
| Configuration, environments, credentials, parameters       | `docs/configure/`                |
| Data Catalog, datasets, factories                          | `docs/catalog-data/`             |
| Nodes, pipelines, pipeline registry                        | `docs/build/`                    |
| Development: logging, debugging, testing, linting          | `docs/develop/`                  |
| Deployment: packaging, Docker, cloud platforms             | `docs/deploy/`                   |
| Extending Kedro: custom datasets, plugins, Hooks, sessions | `docs/extend/`                   |
| Inspecting pipelines, Kedro-Viz                            | `docs/inspect/`                  |
| IDE setup                                                  | `docs/ide/`                      |
| Third-party integrations                                   | `docs/integrations-and-plugins/` |
| Step-by-step tutorials (learning-oriented)                 | `docs/tutorials/`                |

When the topic spans two areas, prefer the more specific one. If in doubt, check the existing MkDocs nav in `docs/meta/` or `mkdocs.yml`.

______________________________________________________________________

## Style rules (quick reference)

Full rules are in [style-guide.md](style-guide.md). These are the most commonly needed points when drafting.

- **UK English**: "customise", "initialise", "behaviour", "catalogue" (but see [Kedro terms](#kedro-specific-terms-quick-reference)).
- **Active voice**: apply the "by zombies" test — if "by zombies" fits after the verb, rewrite.
- **Imperative mood**: start instructions with a verb. Cut "you can" and "there is/are".
- **Sentence length**: 30 words maximum. Split longer sentences.
- **Headings**: sentence case. No end punctuation.
- **Lists**: numbered only for sequential steps; unordered for everything else. Oxford comma in prose.
- **Code blocks**: always include a language lexer. No `$` prompt in `bash` blocks.
- **Links**: descriptive anchor text. MkDocs autorefs (`[kedro.io.AbstractDataset][]`) for API links.
- **Admonitions**: `!!! note`, `!!! warning`, `!!! important` — not plain bold.

______________________________________________________________________

## Kedro-specific terms (quick reference)

| Write        | Not                                                         |
| ------------ | ----------------------------------------------------------- |
| `dataset`    | `data set`                                                  |
| data catalog | Data Catalog (concept); `DataCatalog` in code               |
| `Hooks`      | `hooks` (Kedro Hooks system)                                |
| `pipeline`   | `Pipeline` (concept; `Pipeline` only for the class in code) |
| backend      | back end                                                    |
| runtime      | run time                                                    |
| Kedro        | kedro                                                       |

______________________________________________________________________

## Common Vale fixes

| Rule                   | Finding                                         | Fix                                  |
| ---------------------- | ----------------------------------------------- | ------------------------------------ |
| `Kedro.words`          | "data set"                                      | "dataset"                            |
| `Kedro.words`          | "in order to"                                   | "to"                                 |
| `Kedro.words`          | "utilize", "leverage"                           | "use"                                |
| `Kedro.words`          | "simply", "easily", "quickly", "just", "please" | delete                               |
| `Kedro.words`          | "via"                                           | "with" or "through"                  |
| `Kedro.words`          | "Note that"                                     | `!!! note` or rephrase               |
| `Kedro.words`          | "once" (meaning "after")                        | "after"                              |
| `Kedro.headings`       | Title case heading                              | Convert to sentence case             |
| `Kedro.sentencelength` | Sentence > 30 words                             | Split into two sentences             |
| `Kedro.weaselwords`    | "absolutely", "basically", etc.                 | delete or rewrite                    |
| `Kedro.ukspelling`     | "customize", "initialize", etc.                 | add a `u`: "customise", "initialise" |
| `Vale.Passive`         | Passive construction                            | Rewrite in active voice              |

______________________________________________________________________

## Manual style checklist

Use this when Vale is not installed. Work through every item before declaring the draft done.

- [ ] All headings use sentence case
- [ ] No "simply", "easily", "quickly", "just", "please"
- [ ] No "in order to" — replaced with "to"
- [ ] No "utilize" or "leverage" — replaced with "use"
- [ ] No "via" — replaced with "with" or "through"
- [ ] No "Note that" — replaced with `!!! note` or rephrased
- [ ] No "data set" — replaced with "dataset"
- [ ] No passive voice without an active subject
- [ ] All sentences ≤ 30 words
- [ ] UK spelling throughout
- [ ] All code blocks have a language lexer
- [ ] All links have descriptive anchor text
- [ ] Numbered lists used only for sequential steps
- [ ] `Hooks` capitalised when referring to the Kedro Hooks system
- [ ] `pipeline`, `node`, `dataset`, `catalog` in lowercase (as concepts)
- [ ] No non-inclusive terms: "whitelist/blacklist", "master/slave", "sanity check", "dummy" (see [style-guide.md](style-guide.md) inclusive language section)
- [ ] No condescending hedges: "you might want to", "it's worth noting that", "as you may know", "obviously", "of course"
- [ ] Scope is tight — no background context that isn't directly needed; broader context is linked, not inlined
- [ ] All gaps are marked with `<!-- TODO: verify — <what's unclear> -->` rather than filled with plausible content
- [ ] Config/manifest examples use clear placeholder markers (`# replace with your value`) for values the reader must supply

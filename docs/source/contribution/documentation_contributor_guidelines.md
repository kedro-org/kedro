# Contribute to the Kedro documentation

You are welcome to contribute to the Kedro documentation if you find something incorrect or missing, or have other improvement suggestions.

You can tell us what we should change or by make a PR to change it yourself.

Before you contribute any documentation changes, please read this page so you are familiar with the [Kedro documentation style guidelines](#kedro-documentation-style-guide).

## How do I rebuild the documentation after I make changes to it?

Our documentation is written in Markdown and built from by Sphinx, coordinated by a [build script](https://github.com/kedro-org/kedro/blob/main/docs/build-docs.sh).

If you make changes to the markdown for the Kedro documentation, you can rebuild it within a Unix-like environment (with `pandoc` installed).

If you are a Windows user, you can still contribute to the documentation, but you cannot rebuild it. This is fine! As long as you have made an effort to verify that your Markdown is rendering correctly, and you have followed our basic guidelines, we will be happy to take your final draft as a pull request and rebuild it for you.

The following instructions are specifically for people working with documentation who may not already have a development setup. If you are comfortable with virtual environments, cloning and branching from a git repo and using `make` you don't need them and can probably jump to the section called [Build the documentation](#build-the-documentation).

### Set up to build Kedro documentation

Follow the setup instructions in the [developer contributor guide](./developer_contributor_guidelines.md#before-you-start-development-set-up)
to fork the Kedro repo, create and activate a Python virtual environment and install the dependencies necessary to build the documentation.


### Build the documentation

**MacOS users** can use `make` commands to build the documentation:

```bash
make build-docs
```

The build will take a few minutes to finish, and a successful result is a set of HTML documentation in `docs/build/html`, which you can review by navigating to the following file and opening it: `docs/build/html/index.html`.


## Extend Kedro documentation

### Add new pages

All Kedro documentation is collated and built from a single index file, [`index.rst`](https://github.com/kedro-org/kedro/blob/main/docs/source/index.rst) found in the `docs/source` folder.

If you add extra pages of documentation, you should always include them within `index.rst` file to include them in the table of contents and let Sphinx know to build them alongside the rest of the documentation.

### Move or remove pages

To move or remove a page of documentation, first locate it in the repo, and also locate where it is specified in the `index.rst` or `.rst` for the relevant section within the table of contents.

### Create a pull request

You need to submit any changes to the documentation via a branch.

[Find out more about the process of submitting a PR to the Kedro project](./developer_contributor_guidelines.md).

### Help!

There is no shame in breaking the documentation build. Sphinx is incredibly fussy and even a single space in the wrong place will sometimes cause problems. A range of other issues can crop up and block you, whether you're technically experienced or less familiar with working with git, conda and Sphinx.

Ask for help over on [GitHub discussions](https://github.com/kedro-org/kedro/discussions).

## Kedro documentation style guide

This is the style guide we have used to create [documentation about Kedro](../index).

When you are writing documentation for your own project, you may find it useful to follow these rules. We also ask anyone kind enough to contribute to the Kedro documentation to follow our preferred style to maintain consistency and simplicity.

We prefer to think of the following list as guidelines rather than rules because have made them lightweight to encourage you to contribute.

Where it's not obvious what the style should be, it's worth consulting the [Microsoft style guide](https://docs.microsoft.com/en-gb/style-guide/welcome/). We also use the [INCITS Inclusive Terminology Guidelines](https://standards.incits.org/apps/group_public/download.php/131246/eb-2021-00288-001-INCITS-Inclusive-Terminology-Guidelines.pdf).

```eval_rst
.. note:: If you are unsure of our preferred style, just do what you can in your documentation contribution, and note any queries. We can always iterate the submission with you when you create a pull request.
```

### Language
* Use UK English

### Formatting
* Use Markdown formatting
* Mark code blocks with the appropriate language to enable syntax highlighting
* We use a `bash` lexer for all codeblocks that represent the terminal, and we don't include the prompt

### Links
* Make hyperlink descriptions as descriptive as you can. This is a good description:

```text
Learn how to [update the project pipeline](../tutorial/create_pipelines.html#update-the-project-pipeline)
```

This is less helpful:

```text
Learn how to update the [project pipeline](../tutorial/create_pipelines.html#update-the-project-pipeline)
```

Don't write this:

```text
To learn how to update the project pipeline, see [here](../tutorial/create_pipelines.html#update-the-project-pipeline)
```

### Capitalisation
* Only capitalise proper nouns e.g. names of technology products, other tools and services. See the [Kedro lexicon section](#kedro-lexicon) below for additional guidance.
* Don't capitalise cloud, internet, machine learning, advanced analytics etc. as per the [Microsoft style guide](https://docs.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/term-collections/accessibility-terms).
* Follow sentence case, which capitalises only the first word of a title/subtitle. We prefer this:

```text
## An introduction to pipelines
```

Don't write this:

```text
## An Introduction to Pipelines
```

### Bullets
* Capitalise the first word.
* Don't put a period at the end unless it's a full sentence. Aim for consistency within a block of bullets if you have some bullets with full sentences and others without, you'll need to put a period at the end of each of them. Like in this set.
* Don't use numbered bullets except for a sequence of activities or where you have to refer back to one of them in the text (or a diagram).

### Notes
We use callout sections formatted in `.rst` to bring attention to key points. For example:

```eval_rst
.. note::  Do not pass "Go", do not collect £200.
```

* You will need to use restructured text formatting within the box. Aim to keep the formatting of the callout text plain, although you can include bold, italic, code and links.
* Keep the amount of text (and the number of callouts used) to a minimum.
* Prefer to use `note`, `warning` and `important` only, rather than a number of different colours/types of callout.
    * Use `note` for notable information
    * Use `warning` to indicate a potential `gotcha`
    * Use `important` when highlighting a key point that cannot be ignored

### Kedro lexicon
* Name of our product: Kedro and Kedro-Viz (note capitalisation).
* Use pipeline as this isn't a proper noun. Tend to lower case except if there is a precedent (see next bullet).
* Use Hooks (not hooks, except where it's a necessary part of your code example). We are taking our lead from React here, so capitalising despite it not seeming consistent with other rules.
* Use dataset (not data set, or data-set) for a generic dataset.
 * Use capitalised DataSet when talking about a specific Kedro dataset class e.g. CSVDataSet.
* Use data catalog for a generic data catalog.
 * Use Data Catalog to talk about the [Kedro Data Catalog](../data/data_catalog.md).

### Style
* Keep your sentences short and easy to read.
* Do not plagiarise other authors. Link to their text and credit them.
* Avoid colloquialisms that may not translate to other regions/languages.
* Avoid technical terminology, particularly acronyms, that do not pass the "Google test", which means it is not possible to find their meaning from a simple Google search.
* Use imperatives to make instructions, or second person.
  * For example "Complete the configuration steps" or "You should complete the configuration steps". Don't use the passive "The configuration steps should be completed" (see next bullet).
* Avoid passive tense. What is passive tense? If you can add "by zombies" to the end of any sentence, it is passive.
  * For example: "The configuration steps should be completed." can also be read as: "The configuration should be completed BY ZOMBIES".
  * Instead, you'd write this: "You should complete the configuration steps" or better still, "Complete the configuration steps".

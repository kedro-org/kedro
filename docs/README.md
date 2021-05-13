![Kedro Logo Banner](https://github.com/quantumblacklabs/kedro/blob/develop/static/img/kedro_banner.png)

# Kedro documentation style guide

This is the style guide we have used to create [documentation about Kedro](https://kedro.readthedocs.io/en/stable/).

When you are writing documentation for your own project, you may find it useful to follow these rules. We will also ask anyone kind enough to contribute to the Kedro documentation to follow our preferred style to maintain consistency and simplicity. However, we are not over-proscriptive and are happy to take contributions regardless, as long as you are happy if we edit your text to follow these rules.

## Style guidelines

Please follow these simple rules. Where it's not obvious what the style should be, it's worth consulting the [Microsoft style guide](https://docs.microsoft.com/en-gb/style-guide/welcome/).

>If you are unsure of something, just do what you can in your documentation
>contribution, and note any queries. We can always iterate the submission
>with you when you create a pull request.:

### Language
* Use [UK English](https://www.britishcouncilfoundation.id/en/english/articles/british-and-american-english)

### Formatting
* Use Markdown formatting. If you are unsure of this, here is a useful [Cheatsheet and sandbox](https://daringfireball.net/projects/markdown/dingus)
* Mark code blocks with the appropriate language to enable [syntax highlighting](https://support.codebasehq.com/articles/tips-tricks/syntax-highlighting-in-markdown)
* We use a `bash` lexer for all codeblocks that represent the terminal, and we don't include the prompt

### Links
* Make hyperlink descriptions descriptive. [Musings on vegan cookery](LINK) is good. [Musings](LINK) is less helpful. Don't write "For musings on vegan cookery, see [here](LINK).

### Capitalisation
* Only capitalise proper nouns e.g. names of QuantumBlack products, other tools and services. See Kedro lexicon, below, for additional guidance.
* Don't capitalise cloud, internet, machine learning, advanced analytics etc. as per the [Microsoft style guide](https://docs.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/i/internet-intranet-extranet and https://docs.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/term-collections/cloud-computing-terms).
* Follow sentence case, which capitalises only the first word of a title/subtitle. We prefer this, _"Sentence case only has one capital except for names like Kedro"_ and not this, _"Title Case Means Capitalise Every Word"_

### Bullets
* Capitalise the first word.
* Don't put a period at the end unless it's a full sentence. Aim for consistency within a block of bullets if you have some bullets with full sentences and others without, you'll need to put a period at the end of each of them.
* Don't use numbered bullets except for a sequence of activities or where you have to refer back to one of them in the text (or a diagram).

### Notes
We use callout sections formatted in `.rst` to bring attention to key points. For example:

```eval_rst
    .. note::  Do not pass "Go", do not collect £200.
```

* You will need to use [restructured text formatting](https://thomas-cokelaer.info/tutorials/sphinx/rest_syntax.html) within the box. Aim to keep the formatting of the callout text plain, although you can include bold, italic, code and links.
* Keep the amount of text (and the number of callouts used) to a minimum.
* Prefer to use `note`, `warning` and `important` only, rather than a number of different colours/types of callout.
    * Use `note` for notable information
    * Use `warning` to indicate a potential `gotcha`
    * Use `important` when highlighting a key point that cannot be ignored

### Kedro lexicon

* Name of our product: Kedro and Kedro-Viz (note capitalisation).
* We are QuantumBlack Labs.
* Use journal and pipeline as these aren't proper nouns. Tend to lower case except if there is a precedent (see next bullet).
* Use Hooks (not hooks, except where it's a necessary part of your code example). We are taking our lead from React here, so capitalising despite it not seeming consistent with other rules.
* Use dataset (not data set, or data-set) for a generic dataset.
 * Use capitalised DataSet when talking about a specific Kedro dataset class e.g. CSVDataSet.
* Use data catalog for a generic data catalog.
 * Use Data Catalog to talk about the [Kedro Data Catalog](https://github.com/quantumblacklabs/private-kedro/blob/develop/docs/source/04_user_guide/04_data_catalog.md).

### Style
* Keep your sentences short and easy to read
* Do not plagiarise other authors. Link to their text and credit them
* Avoid colloquialisms that may not translate to other regions/languages.
* Avoid technical terminology, particularly acronyms, that do not pass the "Google test", which means it is not possible to find their meaning from a simple Google search.
* Use imperatives to make instructions, or second person.
  * For example "Complete the configuration steps" or "You should complete the configuration steps". Don't use the passive "The configuration steps should be completed" (see next bullet).
* Avoid passive tense. What is passive tense? If you can add "by zombies" to the end of any sentence, it is passive.
  * For example: "The configuration steps should be completed." will also read OK as "The configuration should be completed BY ZOMBIES". Instead, you'd write "You should complete the configuration steps" or simply "Complete the configuration steps".


## How do I build the Kedro documentation?

If you have installed Kedro, you can build the documentation by running the following from the command line:

```bash
kedro docs
```

The resulting HTML files can be found in `docs/build/html/`.

You can also find the [Kedro documentation online](https://kedro.readthedocs.io/en/stable/).

If you make changes to the markdown for the Kedro documentation, which is stored in the `docs/` folder of the Kedro repository, you can rebuild it within a Unix-like environment (with `pandoc` installed) from the top-level Kedro installation folder:

```bash
make build-docs
```

If you are a Windows user, you can still contribute to the documentation, but you cannot rebuild it. This is fine! As long as you have made an effort to verify that your Markdown is rendering correctly, and you have followed our basic guidelines above, we will be happy to take your final draft as a pull request and rebuild it for you.

## Can I contribute to Kedro documentation?

Yes! If you want to fix or extend our documentation, you'd be welcome to do so. When you are ready to submit, please read the full guide to [contributing to Kedro](../CONTRIBUTING.md).

Before you contribute any documentation, please do read the above rules for styling your Markdown. If there's something you think is missing or incorrect, and you'd like to get really meta and contribute to our style guide, please branch this file and submit a PR!

## What licence do you use?

Kedro is licensed under the [Apache 2.0](../LICENSE.md) License.

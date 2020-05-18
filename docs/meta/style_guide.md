# Style guide

This is a very high-level guide to remind contributors to the documentation, of the 'rules' we are using to ensure consistency.

Where it's not obvious what the style should be, it's worth consulting the [Microsoft style guide](https://docs.microsoft.com/en-gb/style-guide/welcome/).

## Basics
* Use UK English.
* Name of our product: Kedro and Kedro-Viz (note capitalisation).
* We are QuantumBlack Labs.

## Links
* Make hyperlink descriptions descriptive. [Musings on vegan cookery](LINK) is good. [Musings](LINK) is less helpful. Don't write "For musings on vegan cookery, see [here](LINK).

## Capitalisation
* Only capitalise proper nouns e.g. names of QB products, other tools and services. See Kedro lexicon, above, for additional guidance.
* Don't capitalise cloud, internet, machine learning, advanced analytics etc. as per Microsoft style guide https://docs.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/i/internet-intranet-extranet and https://docs.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/term-collections/cloud-computing-terms.
* Follow sentence case, capitalise only the first word of a title/subtitle, unless it is a proper noun.

## Bullets
* Capitalise the first word.
* Don't put a period at the end unless it's a full sentence and go for consistency within a block of bullets, if you have some bullets with full sentences and others without.
* Don't use numbered bullets except for a sequence of activities or where you have to refer back to one of them in the text (or a diagram).

## Kedro lexicon

* Use journal and pipeline as these aren't proper nouns. Tend to lower case except if there is a precedent (see next bullet).
* Use Hooks (not hooks, except where it's a necessary part of your code example). We are taking our lead from React here, so capitalising despite it not seeming consistent with other rules.
* Use dataset (not data set, or data-set) for a generic dataset.
 * Use capitalised DataSet when talking about a specific Kedro dataset class e.g. CSVDataSet.
* Use data catalog for a generic data catalog.
 * Use Data Catalog to talk about the [Kedro Data Catalog](../source/04_user_guide/04_data_catalog.html).

## Style
* Avoid colloquialisms that may not translate to other regions/languages.
* Use imperatives to make instructions, or second person.
  * For example "Complete the configuration steps" or "You should complete the configuration steps". Don't use the passive "The configuration steps should be completed" (see next bullet).
* Avoid passive tense. What is passive tense? If you can add "by zombies" to the end of any sentence, it is passive.
  * For example: "The configuration steps should be completed." will also read OK as "The configuration should be completed BY ZOMBIES". Instead, you'd write "You should complete the configuration steps" or simply "Complete the configuration steps".

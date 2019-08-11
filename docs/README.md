![Kedro Logo Banner](https://github.com/quantumblacklabs/kedro/blob/master/img/kedro_banner.jpg)

# Kedro documentation style guide

This is the style guide we have used to create [documentation about Kedro](https://kedro.readthedocs.io/en/latest/).

When you are writing documentation for your own project, you may find it useful to follow these rules. We will also ask anyone kind enough to contribute to the Kedro documentation to follow our preferred style to maintain consistency and simplicity. However, we are not over-proscriptive and are happy to take contributions regardless, as long as you are happy if we edit your text to follow these rules.

## Guidelines

Please follow these simple rules:

* Use [UK English](https://www.britishcouncilfoundation.id/en/english/articles/british-and-american-english)
* Use Markdown formatting. If you are unsure of this, here is a useful [Cheatsheet and sandbox](https://daringfireball.net/projects/markdown/dingus)
* Use sentence case in titles. We prefer this, _"Sentence case only has one capital except for names like Kedro"_ and not this, _"Title Case Means Capitalise Every Word"_
* Mark code blocks with the appropriate language to enable [syntax highlighting](https://support.codebasehq.com/articles/tips-tricks/syntax-highlighting-in-markdown)
* We use a `bash` lexer for all codeblocks that represent the terminal, and we don't include the prompt
* Bullet points start with capitals and do not end with full-stops
* Prefer to use symbols for bullets instead of numbers unless you are specifically giving a sequence of instructions
* Keep your sentences short and easy to read
* Do not plagiarise other authors. Link to their text and credit them

If you are in doubt, take a look at how we've written the Kedro documentation. If you are unsure of something, just do what you can in your documentation contribution, and note any queries. We can always iterate the submission with you when you create a pull request.

## How do I build your documentation?

If you have installed Kedro, the documentation can be found by running `kedro docs` from the command line or following [this link](https://kedro.readthedocs.io/en/latest/).

If you make changes to our documentation, which is stored in the `docs/` folder of your Kedro installation, you can rebuild them within a Unix-like environment (with `pandoc` installed) with:

```bash
make build-docs
```

We use the [Sphinx](https://www.sphinx-doc.org) framework to build our documentation. The resulting HTML files can be found in `docs/build/html/`.

If you are a Windows user, you can still contribute to the documentation, but you cannot rebuild it. This is fine! As long as you have made an effort to verify that your Markdown is rendering correctly, and you have followed our basic guidelines above, we will be happy to take your final draft as a pull request and rebuild it for you.

## Can I contribute to Kedro documentation?

Yes! If you want to fix or extend our documentation, you'd be welcome to do so. When you are ready to submit, please read the full guide to [contributing to Kedro](../CONTRIBUTING.md).

Before you contribute any documentation, please do read the above rules for styling your Markdown. If there's something you think is missing or incorrect, and you'd like to get really meta and contribute to our style guide, please branch this file and submit a PR!

## What licence do you use?

Kedro is licensed under the [Apache 2.0](../LICENSE.md) License.

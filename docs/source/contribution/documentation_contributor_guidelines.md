# Contribute to the Kedro documentation

You are welcome to contribute to the Kedro documentation if you find something incorrect or missing, or have other improvement suggestions.

You can tell us what we should change or make a PR to change it yourself.

Before you contribute any documentation changes, please read the [Kedro documentation style guidelines](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide) on the GitHub wiki.

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

There is a lightweight [documentation style guide](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide) on Kedro's GitHub wiki.

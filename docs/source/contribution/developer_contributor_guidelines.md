# Guidelines for contributing developers

This page explains the principles and development process that we ask contributing developers to follow.

**Any contributions you make will be under the [Apache 2.0 Software License](https://github.com/kedro-org/kedro/blob/main/LICENSE.md).**

In short, when you submit code changes, your submissions are understood to be under the same the [Apache 2.0 License](https://github.com/kedro-org/kedro/blob/main/LICENSE.md) that covers the Kedro project. You should have permission to share the submitted code.

```{note}
You don't need to contribute code to help the Kedro project. See our list of other ways [you can contribute to Kedro](https://github.com/kedro-org/kedro/blob/main/CONTRIBUTING.md).
```

## Introduction

This guide is a practical description of:

* How to set up your development environment to contribute to Kedro.
* How to prepare a pull request against the Kedro repository.


## Before you start: development set up

To work on the Kedro codebase, you will need to be set up with Git, and Make.

```{note}
If your development environment is Windows, you can use the `win_setup_conda` and `win_setup_env` commands from [Circle CI configuration](https://github.com/kedro-org/kedro/blob/main/.circleci/config.yml) to guide you in the correct way to do this.
```

You will also need to create and activate virtual environment. If this is unfamiliar to you, read through our [pre-requisites documentation](../get_started/prerequisites.md).

Next, you'll need to fork the [Kedro source code from the Github repository](https://github.com/kedro-org/kedro):

* Fork the project by clicking **Fork** in the top-right corner of the [Kedro GitHub repository](https://github.com/kedro-org/kedro)
* Choose your target account

If you need further guidance, consult the [Github documentation about forking a repo](https://docs.github.com/en/get-started/quickstart/fork-a-repo#forking-a-repository).

You are almost ready to go. In your terminal, navigate to the folder into which you forked the Kedro code.

Run these commands to install everything you need to work with Kedro:

```
make install-test-requirements
make install-pre-commit
```

Once the above commands have executed successfully, do a sanity check to ensure that `kedro` works in your environment:

```
make test
```

```{note}
If the tests in `tests/extras/datasets/spark` are failing, and you are not planning to work on [Spark](https://spark.apache.org) related features, then you can run a reduced test suite that excludes them. Do this by executing `make test-no-spark`.
```

## Get started: areas of contribution

Once you are ready to contribute, a good place to start is to take a look at the `good first issues` and `help wanted issues` on [GitHub](https://github.com/kedro-org/kedro/issues).

We focus on three areas for contribution: `core`, `extras` and `plugin`:

- `core` refers to the primary Kedro library. Read the [`core` contribution process](#core-contribution-process) for details.
- `extras` refers to features that could be added to `core` that do not introduce too many dependencies or require new Kedro CLI commands to be created e.g. [adding a new dataset](../extend_kedro/custom_datasets.md) to the `kedro.extras.dataset` data management module. All the datasets are placed under `kedro.extras.datasets` to separate heavy dependencies (e.g Pandas) from Kedro `core` components. Read the [`extras` contribution process](#extras-contribution-process) for more information.
- [`plugin`](../extend_kedro/plugins.md) refers to new functionality that requires a Kedro CLI command e.g. adding in Airflow functionality. The [`plugin` development documentation](../extend_kedro/plugins.md) contains guidance on how to design and develop a Kedro `plugin`.


### `core` contribution process

Typically, we only accept small contributions to the `core` Kedro library but we accept new features as plugins or additions to the [`extras`](https://github.com/kedro-org/kedro/tree/main/kedro/extras) module.

To contribute:

1. Create a feature branch on your forked repository and push all your local changes to that feature branch.
2. Is your change [non-breaking and backwards-compatible](./backwards_compatibility.md)? Your feature branch should branch off from:
   <ol type="a">
     <li><code>main</code> if you intend for it to be a non-breaking, backwards-compatible change.</li>
     <li><code>develop</code> if you intend for it to be a breaking change.</li>
   </ol>
3. Before you submit a pull request (PR), please ensure that unit tests, end-to-end (E2E) tests and linters are passing for your changes by running `make test`, `make e2e-tests` and `make lint` locally; see the [development set up](#before-you-start-development-set-up) section above.
4. Open a PR:
   <ol type="a">
     <li>For backwards compatible changes, open a PR against the <code>kedro-org:main</code> branch from your feature branch.</li>
     <li>For changes that are NOT backwards compatible, open a PR against the <code>kedro-org:develop</code> branch from your feature branch.</li>
   </ol>

5. Await reviewer comments.
6. Update the PR according to the reviewer's comments.
7. Your PR will be merged by the Kedro team once all the comments are addressed.

```{note}
We will work with you to complete your contribution, but we reserve the right to take over abandoned PRs.
```

### `extras` contribution process

You can add new work to `extras` if you do not need to create a new Kedro CLI command:

1. Create an [issue](https://github.com/kedro-org/kedro/issues) describing your contribution.
2. Work in [`extras`](https://github.com/kedro-org/kedro/tree/main/kedro/extras) and create a feature branch on your forked repository and push all your local changes to that feature branch.
3. Before you submit a pull request, please ensure that unit tests, end-to-end (E2E) tests and linters are passing for your changes by running `make test`,`make e2e-tests` and `make lint` locally, have a look at the section [development set up](#before-you-start-development-set-up) section above.
4. Include a `README.md` with instructions on how to use your contribution.
5. Is your change [non-breaking and backwards-compatible](./backwards_compatibility.md)?
   <ol type="a">
     <li>For backwards compatible changes, open a PR against the <code>kedro-org:main</code> branch from your feature branch.</li>
     <li>For changes that are NOT backwards compatible, open a PR against the <code>kedro-org:develop</code> branch from your feature branch.</li>
   </ol>

6. Reference your issue in the PR description (e.g., `Resolves #<issue-number>`).
7. Await review comments, then update the PR according to the reviewer's comments.
8. Your PR will be merged by the Kedro team once all the comments are addressed.

```{note}
We will work with you to complete your contribution, but we reserve the right to take over abandoned PRs.
```

```{note}
There are two special considerations when contributing a dataset:

   1. Add the dataset to :code:`kedro.extras.datasets.rst` so it shows up in the API documentation.
   2. Add the dataset to :code:`static/jsonschema/kedro-catalog-X.json` for IDE validation.

```

## Create a pull request

Create your pull request with [a descriptive title](#pull-request-title-conventions). Before you submit it, consider the following:

* You should aim for cross-platform compatibility on Windows, macOS and Linux
* We use [SemVer](https://semver.org/) for versioning
* We have designed our code to be compatible with Python 3.6 onwards and our style guidelines are (in cascading order):
     * [PEP 8 conventions](https://www.python.org/dev/peps/pep-0008/) for all Python code
     * [Google docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for code comments
     * [PEP 484 type hints](https://www.python.org/dev/peps/pep-0484/) for all user-facing functions / class methods e.g.

```
def count_truthy(elements: List[Any]) -> int:
    return sum(1 for elem in elements if element)
```

Ensure that your PR builds cleanly before you submit it, by running the CI/CD checks locally, as follows:
* `make lint`: PEP-8 Standards (`pylint`, `flake8`)
* `make test`: unit tests, 100% coverage (`pytest`, `pytest-cov`)
* `make e2e-tests`: end-to-end tests (`behave`)

```{note}
If Spark/PySpark/Hive tests for datasets are failing it might be due to the lack of Java>8 support from Spark. You can try using `export JAVA_HOME=$(/usr/libexec/java_home -v 1.8)` which [works under macOS or other workarounds](https://stackoverflow.com/questions/53583199/spark-error-unsupported-class-file-major-version).
```

```{note}
We place [conftest.py](https://docs.pytest.org/en/latest/reference/fixtures.html) files in some test directories to make fixtures reusable by any tests in that directory. If you need to see which test fixtures are available and where they come from, you can issue the following command `pytest --fixtures path/to/the/test/location.py`.
```

### Pull request title conventions

The Kedro repository requires that you [squash and merge your pull request commits](https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/about-pull-request-merges#squash-and-merge-your-pull-request-commits), and, in most cases, the [merge message for a squash merge](https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/about-pull-request-merges#merge-message-for-a-squash-merge) then defaults to the pull request title.

For clarity, your pull request title should be descriptive, and we ask you to follow some guidelines suggested by [Chris Beams](https://github.com/cbeams) in his post [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/#seven-rules). In particular, for your pull request title, we suggest that you:

* [Limit the length to 50 characters](https://chris.beams.io/posts/git-commit/#limit-50)
* [Capitalise the first letter of the first word](https://chris.beams.io/posts/git-commit/#capitalize)
* [Omit the period at the end](https://chris.beams.io/posts/git-commit/#end)
* [Use the imperative tense](https://chris.beams.io/posts/git-commit/#imperative)

### Hints on `pre-commit` usage
[`pre-commit`](https://pre-commit.com) hooks run checks automatically on all the changed files on each commit but can be skipped with the `--no-verify` or `-n` flag:

```bash
git commit --no-verify <...>
```

All checks will run during CI build, so skipping checks on commit will not allow you to merge your code with failing checks. You can uninstall the `pre-commit` hooks by running:

```bash
make uninstall-pre-commit
```
`pre-commit` will still be used by `make lint`, but will not install the git hooks.

### Developer Certificate of Origin
We require that all contributions comply with the [Developer Certificate of Origin (DCO)](https://developercertificate.org/). This certifies that the contributor wrote or otherwise has the right to submit their contribution.

All commits must be signed off by including a `Signed-off-by` line in the commit message:
```
This is my commit message

Signed-off-by: Random J Developer <random@developer.example.org>
```

The sign-off can be added automatically to your commit message using the `-s` option:
```bash
git commit -s -m "This is my commit message"
```

To avoid needing to remember the `-s` flag on every commit, you might like to set up a [git alias](https://git-scm.com/book/en/v2/Git-Basics-Git-Aliases) for `git commit -s`. Alternatively, run `make sign-off` to setup a [`commit-msg` Git hook](https://git-scm.com/docs/githooks#_commit_msg) that automatically signs off all commits (including merge commits) you make while working on the Kedro repository.

If your PR is blocked due to unsigned commits, then you must follow the instructions under "Rebase the branch" on the GitHub Checks page for your PR. This will retroactively add the sign-off to all unsigned commits and allow the DCO check to pass.

## Need help?

Working on your first pull request? You can learn how from these resources:

* [First timers only](https://www.firsttimersonly.com/)
* [How to contribute to an open source project on GitHub](https://egghead.io/courses/how-to-contribute-to-an-open-source-project-on-github)

Please check the Q&A on [GitHub discussions](https://github.com/kedro-org/kedro/discussions) and ask any new questions about the development process there too!

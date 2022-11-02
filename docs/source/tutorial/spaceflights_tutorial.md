# Kedro spaceflights tutorial

In this tutorial, we construct nodes and pipelines for a price-prediction model to illustrate the steps of a typical Kedro workflow.

In the text, we assume you have created an empty Kedro project; we show the steps necessary to convert it into a working project. The tutorial guides you to copy and paste example code into the Kedro project. It takes approximately **one hour** to complete.

```{note}
You may prefer to get up and running more swiftly. We also provide the example as a [Kedro starter](../get_started/starters.md) you can follow along without copy/pasting.
```

## Scenario

*It is 2160, and the space tourism industry is booming. Globally, thousands of space shuttle companies take tourists to the Moon and back. You have been able to source data that lists the amenities offered in each space shuttle, customer reviews, and company information.*

***Project***: *You want to construct a model that predicts the price for each trip to the Moon and the corresponding return flight.*

![](../meta/images/moon-rocket.gif)

## Get help
If you hit an issue with the tutorial, the Kedro community can help!

Things you can do:

* check the [Spaceflights tutorial FAQ](spaceflights_tutorial_faqs.md) to see if we have answered the question already
* search the [archive of Discord discussions](https://linen-discord.kedro.org/)
* use the [#questions channel](https://kedro-org.slack.com/archives/C03RKP2LW64) on our Slack channel (which replaces our Discord server) to ask the community for help

## Terminology

We will explain any Kedro-specific terminology we use in the tutorial as we introduce it. We use additional terminology that may not be familiar to some readers, such as the concepts below.

### Project root directory
Also known as the "root directory", this is the parent folder for the entire project. It is the top-level folder that contains all other files and directories associated with the project.

### Dependencies
These are Python packages or libraries that an individual project depends upon to complete a task. For example, the Spaceflights tutorial project depends on the [scikit-learn](https://scikit-learn.org/stable/) library.

### Standard development workflow
When you build a Kedro project, you will typically follow a [standard development workflow](../faq/faq.md#what-is-the-typical-kedro-project-development-workflow):

1. Set up the project template

    * Create a new project` and install project dependencies.
    * Configure credentials and any other sensitive/personal content, and logging

2. Set up the data

    * Add data to the `data` folder
    * Reference all datasets for the project

3. Create the pipeline

    * Construct nodes to make up the pipeline
    * Choose how to run the pipeline: sequentially or in parallel

4. Package the project
    * Build the project documentation
    * Package the project for distribution


### Source control with `git`

We recommend that you use `git` for source control. If you are unfamiliar with a typical `git` workflow but want to learn more, we suggest you look into [Gitflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow).

Navigate to the project root directory and create a `git` repository on your machine (a local repository) for the project:

```bash
git init
git remote add origin https://github.com/<your-repo>
```

### Submit your changes to GitHub

If you work on a project as part of a team, you will share the `git` repository via GitHub, which stores a shared copy of the repository. You should periodically save your changes to your local repository and merge them into the GitHub repository.

Within your team, we suggest that you each develop your code on a branch and create pull requests to submit it to the `develop` or `main` branches:

```bash
# create a new feature branch called 'feature/project-template'
git checkout -b feature/project-template
# stage all the files you have changed
git add .
# commit changes to git with an instructive message
git commit -m 'Create project template'
# push changes to remote branch
git push origin feature/project-template
```

It isn't necessary to branch, but if everyone in a team works on the same branch (e.g. `main`), you might have to resolve merge conflicts more often. Here is an example of working directly on `main`:

```bash
# stage all files
git add .
# commit changes to git with an instructive message
git commit -m 'Create project template'
# push changes to remote main
git push origin main
```

# Frequently asked questions

The following lists a set of questions that we have been asked about Kedro in the past. If you have a different
 question which isn't answered here, check out [GitHub Discussions](https://github.com/quantumblacklabs/kedro/discussions) or talk to the community on the [Discord Server](https://discord.gg/akJDeVaxnB).
## What is Kedro?

Kedro is an open-source Python framework for creating reproducible, maintainable and modular data science code. It
 borrows concepts from software engineering and applies them to machine-learning code; applied concepts include
  modularity, separation of concerns and versioning.

For the source code, take a look at the [Kedro repository on Github](https://github.com/quantumblacklabs/kedro).

## Who maintains Kedro?

Kedro was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) to solve challenges they faced in their project work.

Their work was later turned into an internal product by [Peteris Erins](https://github.com/Pet3ris), [Ivan Danov](https://github.com/idanov), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae) and [Nikolaos Tsaousis](https://github.com/tsanikgr).

Currently, the core Kedro team consists of
[Yetunde Dada](https://github.com/yetudada),
[Ivan Danov](https://github.com/idanov),
[Richard Westenra](https://github.com/richardwestenra),
[Lorena Balan](https://github.com/lorenabalan),
[Lim Hoang](https://github.com/limdauto),
[Jo Stichbury](https://github.com/stichbury),
[Merel Theisen](https://github.com/MerelTheisenQB),
[Gabriel Comym](https://github.com/GabrielComymQB),
[Liam Brummitt](https://github.com/bru5),
[Susanna Wong](https://github.com/studioswong),
[Rashida Kanchwala](https://github.com/rashidakanchwala),
[Joel Schwarzmann](https://github.com/datajoely),
[Antony Milne](https://github.com/AntonyMilneQB),
[Jiri Klein](https://github.com/jiriklein),
[Ignacio Paricio](https://github.com/ignacioparicio) and
[Hamza Oza](https://github.com/hamzaoza).

Former core team members with significant contributions include:
[Gordon Wrigley](https://github.com/tolomea),
[Nasef Khan](https://github.com/nakhan98),
[Anton Kirilenko](https://github.com/Flid),
[Zain Patel](https://github.com/mzjp2),
[Laís Carvalho](https://github.com/laisbsc),
[Kiyohito Kunii](https://github.com/921kiyo),
[Dmitrii Deriabin](https://github.com/dmder),
[Andrii Ivaniuk](https://github.com/andrii-ivaniuk).

And last, but not least, all the open-source contributors whose work went into all Kedro [releases](https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md).

## What are the primary advantages of Kedro?

If you're a Data Scientist, then you should be interested in Kedro because it enables you to:

- **Write cleaner code,** so that your Python code is easy to maintain and re-run in future; it does this by applying standardisation and software-engineering best practices
- **Make a seamless transition from development to production,** as you can write quick, throw-away exploratory code and
 transition to maintainable, easy-to-share, code experiments quickly
- **Stay current in machine learning operations [(MLOps)](https://en.wikipedia.org/wiki/MLOps),** as Kedro takes care
 of the principles you need to create data science code that lasts; you'll always be two steps in front of industry standards
- **Integrate with your data science workflow,** and use tools in the data science ecosystem, like Tensorflow, SciKit-Learn or Jupyter notebooks for experimentation. You can also take advantage of tools to produce for producing
  quality code like Sphinx (documentation); `black`, `isort` and `flake8` (code linting and formatting); and,`pytest` (unit tests)

If you're a Machine-Learning Engineer or Data Engineer, then you should be interested in Kedro because:

- **Standardisation creates efficiency,** establishing proper analytics code foundations can save up to 80% of your hours down the road when putting models in production
- **You can focus on solving problems, not setting up projects,** Kedro provides the scaffolding to build more
 complex data and machine-learning pipelines. There's a focus on spending less time on the tedious "plumbing" required to maintain analytics code; this means that you have more time to solve new problems
- **A data-driven framework makes pipelines easy,** by permitting data versioning, incremental computing and automatic pipeline running order resolution
- **It is platform-agnostic,** allowing you to choose what compute or platform to run your Kedro workflow; Databricks
 and products like Kubeflow, Argo, Prefect and Airflow are deployment targets
- **It is easy to extend**, by using Hooks to add in tools like [MLFlow](https://mlflow.org/) (experiment tracking), [Great Expectations](https://greatexpectations.io/) (data validation and profiling) and [Grafana](https://grafana.com/) (pipeline monitoring)

If you're a Project Lead, then you should be interested in Kedro because:

- **It allows for effortless teamwork and an ability to scale analytics across an organisation.** Kedro standardises team workflows; the modular structure of Kedro facilitates a higher level of collaboration when teams solve problems together
- We stand for **no more fire drills.**  You can remove long delays created because you have to refactor a data
 science proof of concept into production
- **You don't need to start from scratch,** standardisation and separation of concerns makes it possible to reuse analytics code
- **See your project like never before,** Kedro’s pipeline visualization plugin lets you see a blueprint of your team's developing workflows and better collaborate with business stakeholders

## How does Kedro compare to other projects?

Some of our open-source users have called Kedro, the [React](https://medium.com/quantumblack/beyond-the-notebook-and-into-the-data-science-framework-revolution-a7fd364ab9c4) or Django for data science code and we think it's a
 suitable framing for who we are. We exist to standardise how data science code is created.

Everyone sees the pipeline abstraction in Kedro and gets excited, thinking that we're similar to orchestrators like
 Airflow, Luigi, Prefect, Dagster, Flyte, Kubeflow and more. We focus on a different problem, which is the process of
  _authoring_ pipelines, as opposed to _running, scheduling and monitoring_ them.

The responsibility of _"What time will this pipeline run?"_, _"How do I manage my compute?"_ and _"How will I know if it
 failed?"_ is left to the orchestrators. We also have deployment guidelines for using orchestrators as deployment
  targets and are working in collaboration with the maintainers of some of those tools to make the deployment experience as enjoyable as possible.

## What is data engineering convention?

[Bruce Philp](https://github.com/bruceaphilp) and [Guilherme Braccialli](https://github.com/gbraccialli-qb) at
[QuantumBlack](https://github.com/quantumblacklabs) are the brains behind this model of managing data. To see which data layer to use, refer to the following table.

```eval_rst
.. note:: The data layers don’t have to exist locally in the ``data`` folder within your project, but we recommend that you structure your S3 buckets or other data stores in a similar way.
```

![](../meta/images/data_engineering_convention.png)

```eval_rst
+----------------+---------------------------------------------------------------------------------------------------+
| Folder in data | Description                                                                                       |
+================+===================================================================================================+
| Raw            | Initial start of the pipeline, containing the sourced data model(s) that should never be changed, |
|                | it forms your single source of truth to work from. These data models are typically un-typed in    |
|                | most cases e.g. csv, but this will vary from case to case.                                        |
+----------------+---------------------------------------------------------------------------------------------------+
| Intermediate   | Optional data model(s), which are introduced to type your :code:`raw` data model(s), e.g.         |
|                | converting string based values into their current typed representation.                           |
+----------------+---------------------------------------------------------------------------------------------------+
| Primary        | Domain specific data model(s) containing cleansed, transformed and wrangled data from either      |
|                | :code:`raw` or :code:`intermediate`, which forms your layer that you input into your feature      |
|                | engineering.                                                                                      |
+----------------+---------------------------------------------------------------------------------------------------+
| Feature        | Analytics specific data model(s) containing a set of features defined against the :code:`primary` |
|                | data, which are grouped by feature area of analysis and stored against a common dimension.        |
+----------------+---------------------------------------------------------------------------------------------------+
| Model input    | Analytics specific data model(s) containing all :code:`feature` data against a common dimension   |
|                | and in the case of live projects against an analytics run date to ensure that you track the       |
|                | historical changes of the features over time.                                                     |
+----------------+---------------------------------------------------------------------------------------------------+
| Models         | Stored, serialised pre-trained machine learning models.                                           |
+----------------+---------------------------------------------------------------------------------------------------+
| Model output   | Analytics specific data model(s) containing the results generated by the model based on the       |
|                | :code:`model input` data.                                                                         |
+----------------+---------------------------------------------------------------------------------------------------+
| Reporting      | Reporting data model(s) that are used to combine a set of :code:`primary`, :code:`feature`,       |
|                | :code:`model input` and :code:`model output` data used to drive the dashboard and the views       |
|                | constructed. It encapsulates and removes the need to define any blending or joining of data,      |
|                | improve performance and replacement of presentation layer without having to redefine the data     |
|                | models.                                                                                           |
+----------------+---------------------------------------------------------------------------------------------------+
```

## How do I upgrade Kedro?

We use [Semantic Versioning](https://semver.org/). The best way to safely upgrade is to check our [release notes](https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md) for any notable breaking changes. Follow the steps in the migration guide included for that specific release.

Once Kedro is installed, you can check your version as follows:

```
kedro --version
```

To later upgrade Kedro to a different version, simply run:

```
pip install kedro -U
```

When migrating an existing project to a newer Kedro version, make sure you also update the `project_version` in your `pyproject.toml` file from the project root directory or, for projects generated with Kedro<0.17.0, in your `ProjectContext`, which is found in `src/<package_name>/run.py`.

## How can I use a development version of Kedro?

> *Important:* The development version of Kedro is not guaranteed to be bug-free and/or compatible with any of the [stable versions](https://pypi.org/project/kedro/#history). We do not recommend that you use a development version of Kedro in any production systems. Please install and use with caution.

If you want to try out the latest, most novel functionality of Kedro which has not been released yet, you can run the following installation command:

```console
pip install git+https://github.com/quantumblacklabs/kedro.git@develop
```

This will install Kedro from the `develop` branch of the GitHub repository, which is always the most up to date. This command will install Kedro from source, unlike `pip install kedro` which installs from PyPI.

If you want to rollback to the stable version of Kedro, execute the following in your environment:

```console
pip uninstall kedro -y
pip install kedro
```

## How can I find out more about Kedro?

There are a host of articles, podcasts, talks and Kedro showcase projects in the [`kedro-community`](https://github.com/quantumblacklabs/kedro-community) repository.

Our preferred Kedro-community channel for feedback is through [GitHub issues](https://github.com/quantumblacklabs/kedro/issues). We update the codebase regularly; you can find news about updates and features in the [RELEASE.md file on the Github repository](https://github.com/quantumblacklabs/kedro/blob/develop/RELEASE.md).

## How can I cite Kedro?

If you're an academic, Kedro can also help you, for example, as a tool to solve the problem of reproducible research. Find our citation reference on [Zenodo](https://zenodo.org/record/4336685).

## How can I get my question answered?

If your question isn't answered above, check out [GitHub Discussions](https://github.com/quantumblacklabs/kedro/discussions) or talk to the community on the [Discord Server](https://discord.gg/akJDeVaxnB).

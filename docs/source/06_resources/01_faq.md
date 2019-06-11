# Frequently asked questions

> *Note:* This documentation is based on `Kedro 0.14.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

## What is Kedro?

[Kedro](https://github.com/quantumblacklabs/kedro) is a workflow development tool that helps you build data pipelines that are robust, scaleable, deployable, reproducible and versioned. It was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) at [QuantumBlack](https://github.com/quantumblacklabs/) to solve the challenges they faced in their project work.

### Philosophy

Kedro is a Python library and lightly opinionated framework. This means that we give you the flexibility and extensibility of a standard Python library and make very few assumptions on the _best_ way to do things. We have created independent but friendly modules – modules that understand each others' defaults and are compatible. You can use alternative methods and choose to use one or all of the modules but it is understood that using Kedro in its entirety is the best thing that you can do for your projects.

### Principles

The Kedro design principles are:

-   Declarative definitions
-   Composability
-   Flexibility
-   Extensibility
-   Simplicity

## What version of Python does Kedro use?

Kedro is built for Python 3.5+.

## What are the primary advantages of Kedro?

It is important to consider the primary advantages of Kedro over existing tools. As we see it, Kedro:

- Is designed to assist both during development and production, allowing quick iterations
- Enforces separation of concerns between data processing and data storing
- Does the heavy lifting for dependency resolution
- Passes data between nodes for faster iterations during development


## How does Kedro compare to other projects?

Data pipelines consist of extract-transform-load (ETL) workflows. If we understand that data pipelines must be scaleable, monitored, versioned, testable and modular then this introduces us to a spectrum of tools that can be used to construct such data pipelines. `Pipeline` abstraction is implemented in workflow schedulers like Luigi and Airflow, as well as in ETL frameworks like Bonobo ETL and Bubbles.

### Kedro vs workflow schedulers

We see Airflow and Luigi as complementary frameworks: Airflow and Luigi are tools that handle deployment, scheduling, monitoring and alerting. Kedro is the _worker_ that should execute a series of tasks, and report to the Airflow and Luigi _managers_. We are building integrations for both tools and intend these integrations to offer a faster prototyping time and reduce the barriers to entry associated with moving pipelines to both workflow schedulers.

### Kedro vs other ETL frameworks

The primary differences to Bonobo ETL and Bubbles are related to the following features of Kedro:

 - **Ability to support big data operations**. Kedro supports big data operations by allowing you to use PySpark on your projects. We also look at processing dataframes differently to both tools as we consider entire dataframes and do not make use of the slower line-by-line data stream processing. 
 - **Project structure**. Kedro provides a built-in project structure from the beginning of your project configured for best-practice project management.
 - **Automatic dependency resolution for pipelines**. The `Pipeline` module also maps out dependencies between nodes and displays the results of this in a sophisticated but easy to understand directed acyclic graph.
 - Extensibility

## What is data engineering convention?

[Bruce Philp](https://github.com/bruceaphilp) and [Guilherme Braccialli](https://github.com/gbraccialli-qb) at [QuantumBlack](https://github.com/quantumblacklabs) are the brains behind this model of managing data. To see which data layer to use, you can refer to the following table.

> *Note:* The data layers don’t have to exist locally in the `data` folder within your project. It is recommended that you structure your S3 buckets or other data stores in a similar way.

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


## What best practice should I follow to avoid leaking confidential data?

* Avoid committing data to version control (data folder is by default ignored via `.gitignore`)
* Avoid committing data to notebook output cells (data can easily sneak into notebooks when you don't delete output cells)
* Don't commit sensitive results or plots to version control (in notebooks or otherwise)
* Don't commit credentials in `conf/`. There are two default folders for adding configuration - `conf/base/` and `conf/local/`. Only the `conf/local/` folder should be used for sensitive information like access credentials. To add credentials, please refer to the `conf/base/credentials.yml` file in the project template.
* By default any file inside the `conf/` folder (and its subfolders) containing `credentials` in its name will be ignored via `.gitignore` and not commited to your git repository.
* To describe where your colleagues can access the credentials, you may edit the `README.md` to provide instructions.

## Where do I store my custom editor configuration?

You can use `conf/local` to describe your custom editor configuration.

## How do I look up an API function?

Every Kedro function or class has extensive help, so please do take advantage of this capability, example of this is presented below:

```python
help(MemoryDataSet)
```

## How do I build documentation for my project?

Project-specific documentation can be generated by running `kedro build-docs` in the project root directory. This will create documentation based on the code structure. Documentation will also include the [`docstrings`](https://www.datacamp.com/community/tutorials/docstrings-python) defined in the project code.

HTML files for the project documentation will be built to `docs/build/html`.

## How do I build documentation about Kedro?

A local copy of documentation about Kedro can be generated by running `kedro docs` from the command line. The documentation is also available [online](https://kedro.readthedocs.io). 

## How can I find out more about Kedro?

Kedro is on GitHub, and our preferred community channel for feedback is through [GitHub issues](https://github.com/quantumblacklabs/kedro/issues). We will be updating the codebase regularly, and you can find news about updates and features we introduce by heading over to [RELEASE.md](https://github.com/quantumblacklabs/kedro/blob/develop/RELEASE.md).


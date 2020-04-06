# Frequently asked questions

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

## What is Kedro?

[Kedro](https://github.com/quantumblacklabs/kedro) is a workflow development tool that helps you build data pipelines that are robust, scaleable, deployable, reproducible and versioned. It was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) at [QuantumBlack](https://github.com/quantumblacklabs/) to solve the challenges they faced in their project work.

This work was later turned into a product thanks to the following contributors:
[Ivan Danov](https://github.com/idanov), [Dmitrii Deriabin](https://github.com/DmitryDeryabin), [Gordon Wrigley](https://github.com/tolomea), [Yetunde Dada](https://github.com/yetudada), [Nasef Khan](https://github.com/nakhan98), [Kiyohito Kunii](https://github.com/921kiyo), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae), [Peteris Erins](https://github.com/Pet3ris), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra) and [Anton Kirilenko](https://github.com/Flid).

## What are the primary advantages of Kedro?

It is important to consider the primary advantages of Kedro over existing tools.

As we see it, Kedro emphasises a seamless transition from development to production without slowing the pace of the experimentation stage, because it:

- **Simplifies data access,** using YAML configuration to define a single-source of truth for all data sources that your workflow requires
- **Uses a familiar data interface,** by borrowing arguments from Pandas and Spark APIs meaning you do not have to learn a new API
- **Has a minimal pipeline syntax,** that uses Python functions
- **Makes datasets 1st-level citizens,**  resolving task running order according to what each task produces and consumes, meaning you do not need to explicitly define dependencies between tasks
- **Has built-in runner selection,** choosing sequential or parallel runner functionality is a `kedro run` argument
- **Has a low-effort setup,** that does not need a scheduler or database
- **Starts with a project template,** which has built-in conventions and best practices from 50+ analytics engagements
- **Is flexible,** simplifying your extension or replacement of core functionality e.g. the whole Data Catalog could be replaced with another mechanism for data access like [`Haxl`](https://github.com/facebook/Haxl)

## How does Kedro compare to other projects?

Data pipelines consist of extract-transform-load (ETL) workflows. If we understand that data pipelines must be scaleable, monitored, versioned, testable and modular then this introduces us to a spectrum of tools that can be used to construct such data pipelines. `Pipeline` abstraction is implemented in workflow schedulers like Luigi and Airflow, as well as in ETL frameworks like Bonobo ETL and Bubbles.

### Kedro vs workflow schedulers

Kedro is not a workflow scheduler like Airflow and Luigi. Kedro makes it easy to prototype your data pipeline, while Airflow and Luigi are complementary frameworks that are great at managing deployment, scheduling, monitoring and alerting. A Kedro pipeline is like a machine that builds a car part. Airflow and Luigi tell the different Kedro machines to switch on or off in order to work together to produce a car. We have built a [Kedro-Airflow](https://github.com/quantumblacklabs/kedro-airflow/) plugin, providing faster prototyping time and reducing the barriers to entry associated with moving pipelines to Airflow.

### Kedro vs other ETL frameworks

The primary differences to Bonobo ETL and Bubbles are related to the following features of Kedro:

 - **Ability to support big data operations**. Kedro supports big data operations by allowing you to use PySpark on your projects. We also look at processing dataframes differently to both tools as we consider entire dataframes and do not make use of the slower line-by-line data stream processing.
 - **Project structure**. Kedro provides a built-in project structure from the beginning of your project configured for best-practice project management.
 - **Automatic dependency resolution for pipelines**. The `Pipeline` module also maps out dependencies between nodes and displays the results of this in a sophisticated but easy to understand directed acyclic graph.

## How can I find out more about Kedro?

You have three sources of community-generated content:
 - Articles, podcasts and talks
 - Kedro used on real-world use cases
 - Community interaction

We'll be updating links to community-generated content when we come across them.

### Articles, podcasts and talks

```eval_rst
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Title                                                   | Author                      | Audience                      | Format    | URL                                                                                                                               |
+=========================================================+=============================+===============================+===========+===================================================================================================================================+
| Using Kedro and MLflow                                  | Tom Goldenberg & Musa Bilal | QuantumBlack Medium           | Article   | https://medium.com/@QuantumBlack/deploying-and-versioning-data-pipelines-at-scale-942b1d81b5f5                                    |
| Deploying and versioning data pipelines at scale        |                             |                               |           |                                                                                                                                   |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Kedro: A New Tool For Data Science                      | Jo Stichbury                | Towards Data Science          | Article   | https://towardsdatascience.com/kedro-prepare-to-pimp-your-pipeline-f8f68c263466                                                   |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Building a Pipeline with Kedro for an ML Competition    | Masaaki Hirotsu             | Medium                        | Article   | https://medium.com/mhiro2/building-pipeline-with-kedro-for-ml-competition-63e1db42d179                                            |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Kedro in Jupyter Notebooks On Google GCP Dataproc       | Zhong Chen                  | Zhong Chen                    | Article   | https://medium.com/@zhongchen/kedro-in-jupyter-notebooks-on-google-gcp-dataproc-31d5f45ad235                                      |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Ship Faster With An Opinionated Data Pipeline Framework | Tom Goldenberg              | Data Engineering Podcast      | Podcast   | https://www.dataengineeringpodcast.com/kedro-data-pipeline-episode-100/                                                           |
| Episode 100                                             |                             |                               |           |                                                                                                                                   |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Production-level data pipelines that make everyone      | Yetunde Dada                | PyData Berlin 2019            | Recording | https://youtu.be/OFObles2CJs                                                                                                      |
| happy using Kedro                                       |                             |                               |           |                                                                                                                                   |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Data Science Best Practices con Kedro                   | Carlos Gimenez              | PyData Córdoba Argentina 2019 | Recording | https://youtu.be/_0kMmRfltEQ                                                                                                      |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Kedro - Nubank ML Meetup                                | Carlos Barreto              | Nubank On the Stage           | Recording | https://youtu.be/clBgxmDsSjI                                                                                                      |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Comparison of Python pipeline packages: Airflow, Luigi, | Yusuke Minami               | Medium                        | Article   | https://medium.com/@Minyus86/comparison-of-pipeline-workflow-packages-airflow-luigi-gokart-metaflow-kedro-pipelinex-5daf57c17e7   |
| Metaflow, Kedro & PipelineX                             |                             |                               |           |                                                                                                                                   |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| A story using the Kedro pipeline library                | Kien Y. Knot                | Hatena Blog                   | Article   | http://socinuit.hatenablog.com/entry/2020/02/08/210423                                                                            |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Understanding best-practice Python tooling by comparing | Jonas Kemper                | Medium                        | Article   | https://medium.com/@jonas.r.kemper/understanding-best-practice-python-tooling-by-comparing-popular-project-templates-6eba49229106 |
| popular project templates                               |                             |                               |           |                                                                                                                                   |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
| Transparent data flow with Kedro                        | Nick Doiron                 | Medium                        | Article   | https://medium.com/@mapmeld/transparent-data-flow-with-kedro-eba842de4eb2                                                         |
+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------+
```

### Kedro used on real-world use cases

You can find a list of Kedro projects in the [`kedro-examples`](https://github.com/quantumblacklabs/kedro-examples) repository.

### Community interaction

 Kedro is also on GitHub, and our preferred community channel for feedback is through [GitHub issues](https://github.com/quantumblacklabs/kedro/issues). We will be updating the codebase regularly, and you can find news about updates and features we introduce by heading over to [RELEASE.md](https://github.com/quantumblacklabs/kedro/blob/develop/RELEASE.md).

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

## What version of Python does Kedro use?

Kedro is built for Python 3.5, 3.6 and 3.7.

## How do I upgrade Kedro?

We use [Semantic Versioning](http://semver.org/). The best way to safely upgrade is to check our [release notes](https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md) for any notable breaking changes. Please also follow the steps in the migration guide if one is included for a particular release.

Once Kedro is installed, you can check your version as follows:

```
kedro --version
```

To later upgrade Kedro to a different version, simply run:

```
pip install kedro -U
```

When migrating an existing project to a newer Kedro version, make sure you also update the `project_version` in your `ProjectContext`, which is found in `src/<package_name>/run.py`.

## What best practice should I follow to avoid leaking confidential data?

* Avoid committing data to version control (data folder is by default ignored via `.gitignore`)
* Avoid committing data to notebook output cells (data can easily sneak into notebooks when you don't delete output cells)
* Don't commit sensitive results or plots to version control (in notebooks or otherwise)
* Don't commit credentials in `conf/`. There are two default folders for adding configuration - `conf/base/` and `conf/local/`. Only the `conf/local/` folder should be used for sensitive information like access credentials. To add credentials, please refer to the `conf/base/credentials.yml` file in the project template.
* By default any file inside the `conf/` folder (and its subfolders) containing `credentials` in its name will be ignored via `.gitignore` and not committed to your git repository.
* To describe where your colleagues can access the credentials, you may edit the `README.md` to provide instructions.

## What is the philosophy behind Kedro?

Kedro is a Python library and lightly opinionated framework. This means that we give you the flexibility and extensibility of a standard Python library and make very few assumptions on the _best_ way to do things. We have created independent but friendly modules – modules that understand each others' defaults and are compatible. You can use alternative methods and choose to use one or all of the modules but it is understood that using Kedro in its entirety is the best thing that you can do for your projects.

The Kedro design principles are:

-   Declarative definitions
-   Composability
-   Flexibility
-   Extensibility
-   Simplicity

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

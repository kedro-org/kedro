# Frequently asked questions

The following lists a set of questions that we have been asked about Kedro in the past. If you have a different question which isn't answered here, please consider asking it over on [Stack Overflow](https://stackoverflow.com/questions/tagged/kedro).

## What is Kedro?

[Kedro](https://github.com/quantumblacklabs/kedro) is an open-source Python framework that applies software engineering best-practice to data and machine-learning pipelines.  You can use it, for example, to optimise the process of taking a machine learning model into a production environment. You can use Kedro to organise a single user project running on a local environment, or collaborate in a team on an enterprise-level project.

For the source code, take a look at the [Kedro repository on Github](https://github.com/quantumblacklabs/kedro).

Kedro helps you build data pipelines that are robust, scaleable, deployable, reproducible and versioned. It was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) at [QuantumBlack](https://github.com/quantumblacklabs/) to solve the challenges they faced in their project work.

This work was later turned into a product thanks to the following contributors:

[Ivan Danov](https://github.com/idanov), [Dmitrii Deriabin](https://github.com/DmitryDeryabin), [Gordon Wrigley](https://github.com/tolomea), [Yetunde Dada](https://github.com/yetudada), [Nasef Khan](https://github.com/nakhan98), [Kiyohito Kunii](https://github.com/921kiyo), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae), [Peteris Erins](https://github.com/Pet3ris), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra) and [Anton Kirilenko](https://github.com/Flid).

## What are the primary advantages of Kedro?

It is important to consider the primary advantages of Kedro over existing tools.

As we see it, Kedro emphasises a seamless transition from development to production without slowing the pace of the experimentation stage, because it:

- **Simplifies data access,** using YAML configuration to define a single-source of truth for all data sources that your workflow requires
- **Uses a familiar data interface,** by borrowing arguments from Pandas and Spark APIs meaning you do not have to learn a new API
- **Has a minimal pipeline syntax,** that uses Python functions
- **Makes datasets 1st-level citizens,**  resolving task running order according to what each task produces and consumes, meaning you do not need to explicitly define dependencies between tasks
- **Has built-in runner selection,** choosing sequential, parallel or thread runner functionality is a `kedro run` argument
- **Has a low-effort setup,** that does not need a scheduler or database
- **Starts with a project template,** which has built-in conventions and best practices from 140+ analytics engagements
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


## What is the philosophy behind Kedro?

Kedro is a Python library and lightly opinionated framework. This means that we give you the flexibility and extensibility of a standard Python library and make very few assumptions on the _best_ way to do things. We have created independent but friendly modules – modules that understand each others' defaults and are compatible. You can use alternative methods and choose to use one or all of the modules but it is understood that using Kedro in its entirety is the best thing that you can do for your projects.

The Kedro design principles are:

-   Declarative definitions
-   Composability
-   Flexibility
-   Extensibility
-   Simplicity

## What is data engineering convention?

[Bruce Philp](https://github.com/bruceaphilp) and [Guilherme Braccialli](https://github.com/gbraccialli-qb) at [QuantumBlack](https://github.com/quantumblacklabs) are the brains behind this model of managing data. To see which data layer to use, refer to the following table.

> *Note:* The data layers don’t have to exist locally in the `data` folder within your project, but we recommend that you structure your S3 buckets or other data stores in a similar way.

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

## What version of Python does Kedro support?

Kedro is built for Python 3.6, 3.7 and 3.8.

## How do I upgrade Kedro?

We use [Semantic Versioning](http://semver.org/). The best way to safely upgrade is to check our [release notes](https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md) for any notable breaking changes. Follow the steps in the migration guide included for that specific release.

Once Kedro is installed, you can check your version as follows:

```
kedro --version
```

To later upgrade Kedro to a different version, simply run:

```
pip install kedro -U
```

When migrating an existing project to a newer Kedro version, make sure you also update the `project_version` in your `ProjectContext`, which is found in `src/<package_name>/run.py`.

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

### Articles, podcasts and talks

```eval_rst
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| Date       | Title                                                   | Author                      | Audience                      | Format    | Language   | URL                                                                                                                               |
+============+=========================================================+=============================+===============================+===========+============+===================================================================================================================================+
| N/A        | DataEngineerOne Kedro Youtube channel                   | Tam-Sanh Nguyen             | Youtube                       | Recording | English    | https://youtube.com/c/DataEngineerOne                                                                                             |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 01/06/2020 | Start small and grow big MLOps2020                      | @chck                       | CyberAgent AI tech studio     | Article   | Japanese   | https://cyberagent.ai/blog/research/12898/                                                                                        |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 28/05/2020 | Improved Machine Learning with Kedro & MLflow           | Michael Bloem               | Big Data Ignite               | Recording | English    | https://youtu.be/fCWGevB366g                                                                                                      |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 20/05/2020 | Make Notebook Pipeline with Kedro+Papermill             | Takumi Hirata               | Qitta                         | Article   | Japanese   | https://qiita.com//hrappuccino/items/584c22c3cd5a2f0247d8                                                                         |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 14/05/2020 | 25 Hot New Data Tools and What They DON'T do            | Pete Soderling              | Towards Data Science          | Article   | English    | https://towardsdatascience.com/25-hot-new-data-tools-and-what-they-dont-do-31bf23bd8e56                                           |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 24/02/2020 | What is Kedro (The Parts)                               | Waylon Walker               | DEV Community                 | Article   | English    | https://dev.to/waylonwalker/what-is-kedro-lob                                                                                     |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 10/02/2020 | Understanding best-practice Python tooling by comparing | Jonas Kemper                | Medium                        | Article   | English    | https://medium.com/@jonas.r.kemper/understanding-best-practice-python-tooling-by-comparing-popular-project-templates-6eba49229106 |
|            | popular project templates                               |                             |                               |           |            |                                                                                                                                   |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 08/02/2020 | A story using the Kedro pipeline library                | Kien Y. Knot                | Hatena Blog                   | Article   | Japanese   | http://socinuit.hatenablog.com/entry/2020/02/08/210423                                                                            |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 07/02/2020 | Transparent data flow with Kedro                        | Nick Doiron                 | Medium                        | Article   | English    | https://medium.com/@mapmeld/transparent-data-flow-with-kedro-eba842de4eb2                                                         |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 02/02/2020 | Comparison of Python pipeline packages: Airflow, Luigi, | Yusuke Minami               | Medium                        | Article   | Japanese   | https://medium.com/@Minyus86/comparison-of-pipeline-workflow-packages-airflow-luigi-gokart-metaflow-kedro-pipelinex-5daf57c17e7   |
|            | Metaflow, Kedro & PipelineX                             |                             |                               |           |            |                                                                                                                                   |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 23/12/2019 | Kedro in Jupyter Notebooks On Google GCP Dataproc       | Zhong Chen                  | Zhong Chen                    | Article   | English    | https://medium.com/@zhongchen/kedro-in-jupyter-notebooks-on-google-gcp-dataproc-31d5f45ad235                                      |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 19/12/2019 | Production-level data pipelines that make everyone      | Yetunde Dada                | PyData Berlin 2019            | Recording | English    | https://youtu.be/OFObles2CJs                                                                                                      |
|            | happy using Kedro                                       |                             |                               |           |            |                                                                                                                                   |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 18/12/2019 |  Building a Pipeline with Kedro for an ML Competition   | Masaaki Hirotsu             | Medium                        | Article   | Japanese   | https://medium.com/mhiro2/building-pipeline-with-kedro-for-ml-competition-63e1db42d179                                            |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 18/12/2019 | Kedro - Nubank ML Meetup                                | Carlos Barreto              | Nubank On the Stage           | Recording | Portuguese | https://youtu.be/clBgxmDsSjI                                                                                                      |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 16/12/2019 | Data Science Best Practices con Kedro                   | Carlos Gimenez              | PyData Córdoba Argentina 2019 | Recording | Spanish    | https://youtu.be/_0kMmRfltEQ                                                                                                      |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 18/11/2019 | Using Kedro and MLflow                                  | Tom Goldenberg & Musa Bilal | QuantumBlack Medium           | Article   | English    | https://medium.com/@QuantumBlack/deploying-and-versioning-data-pipelines-at-scale-942b1d81b5f5                                    |
|            | Deploying and versioning data pipelines at scale        |                             |                               |           |            |                                                                                                                                   |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 01/10/2019 | Ship Faster With An Opinionated Data Pipeline Framework | Tom Goldenberg              | Data Engineering Podcast      | Podcast   | English    | https://www.dataengineeringpodcast.com/kedro-data-pipeline-episode-100/                                                           |
|            | Episode** 100                                           |                             |                               |           |            |                                                                                                                                   |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
| 04/06/2019 | Kedro: A New Tool For Data Science                      | Jo Stichbury                | Towards Data Science          | Article  | English     | https://towardsdatascience.com/kedro-prepare-to-pimp-your-pipeline-f8f68c263466                                                   |
+------------+---------------------------------------------------------+-----------------------------+-------------------------------+-----------+------------+-----------------------------------------------------------------------------------------------------------------------------------+
```

### Kedro used in real-world use cases

You can find a list of Kedro projects in the [`kedro-examples`](https://github.com/quantumblacklabs/kedro-examples) repository.

### Community interaction

Our preferred Kedro-community channel for feedback is through [GitHub issues](https://github.com/quantumblacklabs/kedro/issues). We update the codebase regularly; you can find news about updates and features in the [RELEASE.md file on the Github repository](https://github.com/quantumblacklabs/kedro/blob/develop/RELEASE.md).

## How can I get my question answered?

If your question isn't answered above, please consider asking it over on [Stack Overflow](https://stackoverflow.com/questions/tagged/kedro).

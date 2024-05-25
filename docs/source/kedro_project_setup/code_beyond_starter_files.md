# Adding code beyond starter files

After you [create a Kedro project](../get_started/new_project.md) and
[add a pipeline](../tutorial/create_a_pipeline.md), you notice that Kedro generates a
few boilerplate files: `nodes.py`, `pipeline.py`, `pipeline_registry.py`...

While those may be sufficient for a small project, they quickly become large, hard to
read and collaborate on as your codebase grows.
Those files also sometimes make new users think that Kedro requires code
to be located only in those starter files, which is not true.

This section elaborates what are the Kedro requirements in terms of organising code
in files and modules.
It also provides examples of common scenarios such as sharing utilities between
pipelines and using Kedro in a monorepo setup.

## Where does Kedro look for code to be located

The only technical constraint for arranging code in the project is that `pipeline_registry.py`
and `settings.py` files must be located in `<your_project>/src/<your_project>` directory, which is where
they are created by default.

`pipeline_registry.py` must have a `register_pipelines()` function that returns a `dict[str, Pipeline]`
mapping from pipeline name to a corresponding `Pipeline` object.

Other than that, **Kedro does not impose any constraints on where you should keep files with
`Pipeline`s, `Node`s, or functions wrapped by `node`**.

This being the only constraint means that you can, for example:
* Add `utils.py` file to a pipeline folder and import utilities used by multiple
  functions in `nodes.py` from there.
* [Share modules between pipelines](#sharing-modules-between-pipelines).
  Those could be utility functionalities, or a standalone module responsible for
  the domain-specific logic.
* [Use Kedro in a monorepo setup](#kedro-project-in-a-monorepo-setup) if there are
  software components independent of Kedro that you want to keep together in the version control system.
* Delete or rename a default `nodes.py` file, split it into multiple files or modules.
* If you have multiple large `Pipeline` objects defined in a single `pipeline.py`,
  split them into separate `.py` files. For example, in `data_processing` pipeline
  you may want to have `cleaning_pipeline.py` and `merging_pipeline.py`.
* Instead of registering many pipelines in `register_pipelines()` function one by one,
  create a few `dict[str, Pipeline]` objects in different places of the project
  and then make `register_pipelines()` return a union of those.

  ```{note}
  While Kedro features a [`find_pipelines()` functionality for autodiscovery of pipelines](../nodes_and_pipelines/pipeline_registry.md#pipeline-autodiscovery),
  for large projects you may want a finer control and register pipelines manually.
  ```

## Common codebase extension scenarios

This section provides examples of how you can handle some common cases of adding more
code to or around your Kedro project.
The provided examples are by no means the only ways to achieve the target scenarios,
and serve only as illustrative purposes.

### Sharing modules between pipelines

Oftentimes you have machinery that has to be imported by multiple `pipelines`.
To keep them as part of a Kedro project, **create a module (for example, `utils`) at the same
level as the `pipelines` folder**, and organise the functionalities there:

```text
├── conf
├── data
├── notebooks
└── src
    ├── my_project
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── pipeline_registry.py
    │   ├── settings.py
    │   ├── pipelines
    │   └── utils                       <-- Create a module to store your utilities
    │       ├── __init__.py             <-- Required to import from it
    │       ├── pandas_utils.py         <-- Put a file with utility functions here
    │       ├── dictionary_utils.py     <-- Or a few files
    │       ├── visualisation_utils     <-- Or sub-modules to organise even more utilities
    └── tests
```

Example of importing a function `find_common_keys` from `dictionary_utils.py` would be:

```python
from my_project.utils.dictionary_utils import find_common_keys
```

```{note}
For imports like this to be displayed in IDE properly, it is required to perform an editable
installation of the Kedro project to your virtual environment.
This is done via `pip install -e <root-of-kedro-project>`, the easiest way to achieve
this is to `cd` to the root of your Kedro project and run `pip install -e .`.
```

### Kedro project in a monorepo setup

The way a Kedro project is generated may build an impression that it should
only be acting as a root of a `git` repo. This is not true: just like you can combine
multiple Python packages in a single repo, you can combine multiple Kedro projects.
Or a Kedro project with other parts of your project's software stack.

```{note}
A practice of combining multiple, often unrelated software components in a single version
control repository is not specific to Python and called [_**monorepo design**_](https://monorepo.tools/).
```

A common use case of Kedro is that a software product built by a team has components that
are well separable from the Kedro project.

Let's use **a recommendation tool for production equipment operators** as an example.
This example consists of three parts:

| **#** | **Part**                                                                                                     | **Considerations**                                                                                                                                                                                                                                                                                                                                                                                               |
|-------|--------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1     | An ML model, or more precisely, a workflow to prepare the data, train an estimator, ship it to some registry | <ul> <li>Here Kedro fits well, as it allows to develop those pipelines in a modular and extensible way.</li> </ul>                                                                                                                                                                                                                                                                                               |
| 2     | An optimiser that leverages the ML model and implements domain business logic to derive recommendations      | <ul> <li>A good design consideration might be to make it independent of the UI framework.</li> </ul>                                                                                                                                                                                                                                                                                                             |
| 3     | User interface (UI) application                                                                              | <ul> <li>This can be a [`plotly`](https://plotly.com/python/) or [`streamlit`](https://streamlit.io/) dashboard.</li> <li>Or even a full-fledged front-end app leveraging JS framework like [`React`](https://react.dev/).</li> <li>Regardless, this component may know how to access the ML model, but it should probably not know anything about how it was trained and was Kedro involved or not.</li> </ul>  |

A suggested solution in this case would be a **monorepo** design. Below is an example:

```text
└── repo_root
    ├── packages
    │   ├── kedro_project          <-- A Kedro project for ML model training.
    │   │   ├── conf
    │   │   ├── data
    │   │   ├── notebooks
    │   │   ├── ...
    │   ├── optimizer              <-- Standalone package.
    │   └── dashboard              <-- Standalone package, may import `optimizer`, but should not know anything about model training pipeline.
    ├── ...
    ├── ... Examples of what you may want in the repo root:
    ├── requirements.txt           <-- Linters, code formatters... Not dependencies of packages.
    ├── ruff.toml                  <-- Or configs for other tools that you want to share between packages.
    └── ...
```

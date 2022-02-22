```eval_rst
.. warning::  `kedro pipeline package/pull` will be deprecated in 0.18.0. We recommend using `kedro micropkg package/pull` instead.
```

# Micro-packaging

Micro-packaging allows users to share Kedro micro-packages across codebases, organisations and beyond. A micro-package can be any part of Python code in a Kedro project including pipelines and utility functions.

## Package a micro-package

You can package a micro-package by executing: `kedro micropkg package <micropkg_name>`

* This will generate a new [wheel file](https://pythonwheels.com/) for this micro-package.
* By default, the wheel file will be saved into `dist/` directory inside your project.
* You can customise the target with the `--destination` (`-d`) option.

When you package your micro-package, such as a modular pipeline for example, Kedro will also automatically package files from 3 locations:

```text
├── conf
│   └── base
│       └── parameters
│           └── {{pipeline_name*}}  <-- All parameter file(s)
└── src
    ├── my_project
    │   ├── __init__.py
    │   └── pipelines
    │       └── {{pipeline_name}}    <-- Pipeline folder
    └── tests
        ├── __init__.py
        └── pipelines
            └── {{pipeline_name}}    <-- Pipeline tests
```

Kedro will also include any requirements found in `src/<python_package>/pipelines/<micropkg_name>/requirements.txt` in the micro-package wheel file. These requirements will later be taken into account when pulling a micro-package via `kedro micropkg pull`.

```eval_rst
.. note::  Kedro will not package the catalog config files even if those are present in ``conf/<env>/catalog/<micropkg_name>.yml``.
```

If you plan to publish your packaged micro-package to some Python package repository like [PyPI](https://pypi.org/), you need to make sure that your micro-package name doesn't clash with any of the existing packages in that repository. However, there is no need to rename any of your source files if that is the case. Simply alias your package with a new name by running `kedro micropkg package --alias <new_package_name> <micropkg_name>`.

In addition to [PyPI](https://pypi.org/), you can also share the packaged wheel file directly, or via a cloud storage such as AWS S3.

## Package multiple micro-packages

To package multiple micro-packages in bulk, run `kedro micropkg package --all`. This will package all micro-packages specified in the `tool.kedro.micropkg.package` manifest section of the project's `pyproject.toml` file:

```toml
[tool.kedro.micropkg.package]
cleaning_utils = {alias = "aliased_util", destination = "somewhere/else", env = "uat"}
second_pipeline = {}
```

* The keys (`first_pipeline`, `second_pipeline`) are the names of the micro-package folders within the codebase.
* The values are the options accepted by the `kedro micropkg package <micropkg_name>` CLI command.

```eval_rst
.. note::  Make sure `destination` is specified as a POSIX path even when working on a Windows machine.
```

## Pull a micro-package

You can pull a micro-package from a wheel file by executing `kedro micropkg pull <package_name>`.

* The `<package_name>` must either be a package name on PyPI or a path to the wheel file.
* Kedro will unpack the wheel file, and install the files in following locations in your Kedro project:
  * All the micro-package code in `src/<python_package>/pipelines/<micropkg_name>/`
  * Configuration files in `conf/<env>/parameters/<micropkg_name>.yml`, where `<env>` defaults to `base`.
  * To place parameters from a different config environment, run `kedro micropkg pull <micropkg_name> --env <env_name>`
  * Unit tests in `src/tests/pipelines/<micropkg_name>`
* Kedro will also parse any requirements packaged with the micro-package and add them to project level `requirements.in`.
* It is advised to do `kedro build-reqs` to compile the updated list of requirements after pulling a micro-package.

```eval_rst
.. note::  If a micro-package has embedded requirements and a project ``requirements.in`` file does not already exist, it will be generated based on the project ``requirements.txt`` before appending the micro-package requirements.
```

You can pull a micro-package from different locations, including local storage, PyPI and the cloud:

```eval_rst
+--------------------------------+--------------------------------------------------------------------------------------+
| Operation                      | Command                                                                              |
+================================+======================================================================================+
| Pulling from a local directory | ``kedro micropkg pull <project-root>/dist/<micropkg_name>-0.1-py3-none-any.whl``     |
+--------------------------------+--------------------------------------------------------------------------------------+
| Pull from cloud storage        | ``kedro micropkg pull s3://my_bucket/<micropkg_name>-0.1-py3-none-any.whl``          |
+--------------------------------+--------------------------------------------------------------------------------------+
| Pull from PyPI like endpoint   | ``kedro micropkg pull <pypi-package-name>``                                          |
+--------------------------------+--------------------------------------------------------------------------------------+
```

### Providing `fsspec` arguments

* If you are pulling the micro-package from a location that isn't PyPI, Kedro uses [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to locate and pull down your micro-package.
* You can use the `--fs-args` option to point to a YAML that contains the required configuration.

```bash
kedro micropkg pull https://<url-to-pipeline.whl> --fs-args micropkg_pull_args.yml
```

```yaml
# `micropkg_pull_args.yml`
client_kwargs:
  headers:
    Authorization: token <token>
```

## Pull multiple micro-packages

* To pull multiple micro-packages in bulk, run `kedro micropkg pull --all`.
* This will pull and unpack all micro-packages specified in the `tool.kedro.micropkg.pull` manifest section of the project's `pyproject.toml` file:

```toml
[tool.kedro.micropkg.pull]
"dist/first-pipeline-0.1-py3-none-any.whl" = {}
"https://www.url.to/second-pipeline.whl" = {alias = "aliased_pipeline", fs-args = "pipeline_pull_args.yml"}
```

* The keys (wheel references in this case) are the package paths
* The values are the options that `kedro micropkg pull <package_path>` CLI command accepts.

```eval_rst
.. attention:: As per the `TOML specification <https://toml.io/en/v1.0.0#keys>`_, a key that contains any character outside ``A-Za-z0-9_-`` must be quoted.
```

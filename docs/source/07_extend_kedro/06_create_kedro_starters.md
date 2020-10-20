
# Create a Kedro starter

Kedro starters are used to create projects that contain code to run as-is, or to adapt and extend. A good example is the Iris dataset example of basic Kedro project layout, configuration and initialisation code. A team may find it useful to build Kedro starters to create reusable projects that bootstrap a common base and can be extended.

A Kedro starter is a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template that contains the boilerplate code for a Kedro project.

## How to create a Kedro starter

To create a Kedro starter, you need a base project to convert to a Cookiecutter template, which forms the boilerplate for all projects that use the Kedro starter.

Install Cookiecutter as follows:

```bash
pip install cookiecutter
```

You then need to decide which are:

* the common, boilerplate parts of the project
* the configurable elements, which need to be replaced by Cookiecutter strings.

## Configuration variables

By default, when you create a new project using a Kedro starter, `kedro new` launches in interactive mode. The user is prompted for just three variables, which we have seen used in the previous example. No additional configuration information can be submitted at the time the project is created:

* `project_name` - A human readable name for the new project
* `repo_name` - A name for the directory that holds the project repository
* `python_package` - A Python package name for the project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names)

Kedro also allows you to [specify a configuration file](../02_get_started/04_new_project.md) to create a project, which means that additional variables can be passed in. This is not the default way to use `kedro new`, so an additional `--config` flag is needed:

```bash
kedro new --config=my_config.yml --starter=<path-to-starter>
```

As the creator of the Kedro starter, if you need to ask for additional configuration variables, you will need to explain to your users that they must specify them in a file and use the file when they create a new project.

### Example Kedro starter

To review an example Kedro starter, clone [`pandas-iris`](https://github.com/quantumblacklabs/kedro-starter-pandas-iris) from Github.

When you create an Iris dataset example project by calling `kedro new`, you supply three configuration variables as the documentation in [Create a new project](../02_get_started/04_new_project.md) describes. These variables are `project_name`, `repo_name` and `python_package` and they are supplied interactively or by means of a configuration file. You can see how these variables are used by inspecting the template:

**`project_name`**
The human-readable `project-name` variable is used in the [README.md](https://github.com/quantumblacklabs/kedro-starter-pandas-iris/blob/master/%7B%7B%20cookiecutter.repo_name%20%7D%7D/README.md) for the new project and within [`run.py`](https://github.com/quantumblacklabs/kedro-starter-pandas-iris/blob/master/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/run.py) to initialise the `ProjectContext`.

**`repo_name`**
The project structure contains a folder labelled [`{{ cookiecutter.repo_name }}`](https://github.com/quantumblacklabs/kedro-starter-pandas-iris/tree/master/%7B%7B%20cookiecutter.repo_name%20%7D%7D), which forms the top-level folder to contain the Iris dataset example when it is created. The folder storing the example project is represented by `cookiecutter.repo_name`, which is a customisable variable, as you would expect.

**`python_package`**
Within the parent folder, inside the `src` subfolder, is another configurable variable [{{ cookiecutter.python_package }}](https://github.com/quantumblacklabs/kedro-starter-pandas-iris/tree/master/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D) which contains the source code for the example pipelines.

Here is the layout of the project as a Cookiecutter template:

```
    {{ cookiecutter.repo_name }}     # Parent directory of the template
    ├── conf                         # Project configuration files
    ├── data                         # Local project data (not committed to version control)
    ├── docs                         # Project documentation
    ├── logs                         # Project output logs (not committed to version control)
    ├── notebooks                    # Project related Jupyter notebooks (can be used for experimental code before moving the code to src)
    ├── README.md                    # Project README
    ├── setup.cfg                    # Configuration options for tools e.g. `pytest` or `flake8`
    └── src                          # Project source code
        └── {{ cookiecutter.python_package }}
           └── __init.py__
           └── cli.py                # A collection of Kedro command line interface (CLI) commands
           └── hooks.py
           └── pipelines
           └── run.py
        ├── requirements.txt
        ├── setup.py
        └── tests
```

<!--TO DO: Add something here about how the variables passed in at the time the project is created are used by Cookiecutter to create the project. Give the cookiecutter.json file?-->

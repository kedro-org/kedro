# Create a Kedro starter

Kedro starters are used to create projects that contain code to run as-is, or to adapt and extend. A good example is the Iris dataset example of basic Kedro project layout, configuration and initialisation code. A team may find it useful to build Kedro starters to create reusable projects that bootstrap a common base and can be extended.

A Kedro starter is a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template that contains the boilerplate code for a Kedro project.

## How to create a Kedro starter

To create a Kedro starter, you need a base project to convert to a `cookiecutter` template, which forms the boilerplate for all projects that use the Kedro starter.

Install `cookiecutter` as follows:

```bash
pip install cookiecutter
```

You then need to decide which are:

* the common, boilerplate parts of the project
* the configurable elements, which need to be replaced by `cookiecutter` strings

## Configuration variables

By default, when you create a new project using a Kedro starter, `kedro new` launches in interactive mode. The user is then prompted for the variables that have been set in `prompts.yml`.

The most basic and empty starter triggered by `kedro new` is set up with the following variable:

* `project_name` - A human readable name for the new project

Kedro will then automatically generate the following two variables from the entered `project_name`:

* `repo_name` - A name for the directory that holds the project repository
* `python_package` - A Python package name for the project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))

See the configuration for this basic configuration in [the default starter setup](https://github.com/kedro-org/kedro/blob/main/kedro/templates/project/prompts.yml).

As the creator of the Kedro starter you can customise the prompts triggered by `kedro new` by adding your own prompts in `prompts.yml`. This is an example of a custom prompt:

```yaml
custom_prompt:
    title: "Prompt title"
    text: |
      Prompt description that explains to the user what
      information they should provide.
```

At the very least, the prompt `title` must be defined for the prompt to be valid. After Kedro gets the user's input for each prompt, we pass the value to [`cookiecutter`](https://cookiecutter.readthedocs.io/en/1.7.2/), so every key in your `prompts.yml` must have a corresponding key in [`cookiecutter.json`](https://cookiecutter.readthedocs.io/en/1.7.2/tutorial1.html#cookiecutter-json).

If the input to the prompts needs to be **validated**, for example to make sure it only has alphanumeric characters, you can add regex validation rules via the `regex_validator` key. For more complex validation, have a look at [cookiecutter pre/post-generate hooks](https://cookiecutter.readthedocs.io/en/1.7.2/advanced/hooks.html#using-pre-post-generate-hooks-0-7-0).

If you want `cookiecutter` to provide sensible **defaults** in case a user doesn't provide any input, you can add those to `cookiecutter.json`. See [the default starter `cookiecutter.json`](https://github.com/kedro-org/kedro/blob/main/kedro/templates/project/cookiecutter.json) as example.

### Example Kedro starter

To review an example Kedro starter, clone [`pandas-iris`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris) from Github.

When you create an Iris dataset example project by calling `kedro new`, you supply configuration variables as the documentation in [Create a new project](../get_started/new_project.md) describes. When you go through the interactive flow you must supply the `project_name` variable, which is then used to generate the `repo_name` and `python_package` variables. If you use a configuration file, you must supply all three variables in the file. You can see how these variables are used by inspecting the template:

**project_name**

The human-readable `project_name` variable is used in the [README.md](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/README.md) for the new project.

**repo_name**

The project structure contains a folder labelled [`{{ cookiecutter.repo_name }}`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/%7B%7B%20cookiecutter.repo_name%20%7D%7D), which forms the top-level folder to contain the Iris dataset example when it is created. The folder storing the example project is represented by `cookiecutter.repo_name`, which is a customisable variable, as you would expect.

**python_package**

Within the parent folder, inside the `src` subfolder, is another configurable variable [{{ cookiecutter.python_package }}](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D) which contains the source code for the example pipelines. The variable is also used within [`__main__.py`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/__main__.py).

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
       ├── __init.py__
       ├── pipelines
       ├── pipeline_registry.py
       ├── __main__.py
       └── settings.py
    ├── requirements.txt
    ├── setup.py
    └── tests
```

```{note}
You can [add an alias by creating a plugin using `kedro.starters` entry point](./plugins.md#extend-starter-aliases), which will allows you to do `kedro new --starter=your_starters` and shows up on shows up on `kedro starter list`.
```

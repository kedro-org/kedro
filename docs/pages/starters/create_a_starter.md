# Create a Kedro starter

Kedro starters are a useful way to create a new project that contains code to run as-is, or to adapt and extend.

A team may find it useful to build Kedro starters to create reusable projects that bootstrap a common base and can be extended.

Please note that users are expected to have [`Git`](https://git-scm.com/) installed for the `kedro new` flow, which is used in this section.

## Install the `cookiecutter` package
A Kedro starter is a [Cookiecutter](https://cookiecutter.readthedocs.io/) template that contains the boilerplate code for a Kedro project. First install `cookiecutter` as follows:

```bash
pip install cookiecutter
```

To create a Kedro starter, you need a base project to convert to a template, which forms the boilerplate for all projects that use it. You then need to decide which are:

* the common, boilerplate parts of the project
* the configurable elements, which need to be replaced by `cookiecutter` strings

## Custom project creation variables

When you create a new project using a Kedro starter, `kedro new` prompts you for a project name. This variable (`project_name`) is set in the [default starter setup](https://github.com/kedro-org/kedro/blob/main/kedro/templates/project/prompts.yml) in`prompts.yml`.

Kedro automatically generates the following two variables from the entered `project_name`:

* `repo_name` - A name for the directory that holds the project repository
* `python_package` - A Python package name for the project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))

As a starter creator, you can customise the prompts triggered by `kedro new` by adding your own prompts into the `prompts.yml` file in the root of your template. This is an example of a custom prompt:

```yaml
custom_prompt:
    title: "Prompt title"
    text: |
      Prompt description that explains to the user what
      information they should provide.
```

At the very least, the prompt `title` must be defined for the prompt to be valid. After Kedro receives the user's input for each prompt, it passes the value to Cookiecutter, so every key in `prompts.yml` must have a corresponding key in [`cookiecutter.json`](https://cookiecutter.readthedocs.io/en/stable/tutorials/tutorial1.html#cookiecutter-json).

If the input to the prompts needs to be validated, for example to make sure it only has alphanumeric characters, you can add regex validation rules via the `regex_validator` key. Consider using [cookiecutter pre/post-generate hooks](https://cookiecutter.readthedocs.io/en/stable/advanced/hooks.html) for more complex validation.

If you want `cookiecutter` to provide sensible default values, in case a user doesn't provide any input, you can add those to `cookiecutter.json`. See [the default starter `cookiecutter.json`](https://github.com/kedro-org/kedro/blob/main/kedro/templates/project/cookiecutter.json) as example.

## Example Kedro starter

To review an example Kedro starter, check out the [`spaceflights-pandas` starter on GitHub](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas).

When a new `spaceflights-pandas` project is created with `kedro new --starter=spaceflights-pandas`, the user is asked to enter a `project_name` variable, which is then used to generate the `repo_name` and `python_package` variables by default.

If you use a configuration file, you must supply all three variables in the file. You can see how these variables are used by [inspecting the template](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D):

### `project_name`

The human-readable `project_name` variable is used in the [README.md](https://github.com/kedro-org/kedro-starters/blob/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/README.md) for the new project.

### `repo_name`

The top-level folder labelled [`{{ cookiecutter.repo_name }}`](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D), which forms the top-level folder to contain the starter project when it is created.

### `python_package`

Within the parent folder, inside the `src` subfolder, is another configurable variable [{{ cookiecutter.python_package }}](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D) which contains the source code for the example pipelines. The variable is also used within [`__main__.py`](https://github.com/kedro-org/kedro-starters/blob/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/__main__.py).

Here is the layout of the project as a Cookiecutter template:

```
{{ cookiecutter.repo_name }}     # Parent directory of the template
├── conf                         # Project configuration files
├── data                         # Local project data (not committed to version control)
├── docs                         # Project documentation
├── notebooks                    # Project related Jupyter notebooks (can be used for experimental code before moving the code to src)
├── pyproject.toml               #
├── README.md                    # Project README
├── requirements.txt
└── src                          # Project source code
    └── {{ cookiecutter.python_package }}
       ├── __init.py__
       ├── pipelines
       ├── pipeline_registry.py
       ├── __main__.py
       └── settings.py
└── tests
```


## Extend starter aliases

You can add an alias by creating a plugin using `kedro.starters` entry point which enables you to call `kedro new --starter=your_starters`. That is, it can be used directly through the `starter` argument in `kedro new` rather than needing to explicitly provide the `template` and `directory` arguments.

A custom starter alias behaves in the same way as an official Kedro starter alias and is also picked up by the command `kedro starter list`.

You need to extend the starters by providing a list of `KedroStarterSpec`, in this example it is defined in a file called `plugin.py`.

Example for a non-git repository starter:

```python
# plugin.py
starters = [
    KedroStarterSpec(
        alias="test_plugin_starter",
        template_path="your_local_directory/starter_folder",
    )
]
```

Example for a git repository starter:

```python
# plugin.py
starters = [
    KedroStarterSpec(
        alias="test_plugin_starter",
        template_path="https://github.com/kedro-org/kedro-starters/",
        directory="spaceflights-pandas",
    )
]
```

The `directory` argument is optional and should be used when you have multiple templates in one repository as for the [official kedro-starters](https://github.com/kedro-org/kedro-starters). If you only have one template, your top-level directory will be treated as the template.

In your `pyproject.toml`, you need to register the specifications to `kedro.starters`:

```toml
[project.entry-points."kedro.starters"]
starter = "plugin:starters"
```

After that you can use this starter with `kedro new --starter=test_plugin_starter`.

```{note}
If your starter is stored on a git repository, Kedro defaults to use a tag or branch labelled with your version of Kedro, e.g. `0.18.12`. This means that you can host different versions of your starter template on the same repository, and the correct one will be used automatically. If you prefer not to follow this structure, you should override it with the `checkout` flag, e.g. `kedro new --starter=test_plugin_starter --checkout=main`.
```

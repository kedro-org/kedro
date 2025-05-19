# Customise a new project
As you saw from the [First steps](./new_project.md) section, once you have [set up Kedro](../getting-started/install.md), you can create a new project with `kedro new` and customise the code added to that project for its tooling and example code requirements.

The pages in this section describe in detail the various options available.

## Tools to customise a new Kedro project
- [Tools and example code options](./new_project_tools.md)
## Kedro starters
- [Starters](./starters.md)


**Use `kedro new` to create a basic project** <br />
In the simplest instance, you can create a project using `kedro new` and select from a range of [tools and example code options](./new_project_tools.md) to extend the basic project.

**Use `kedro new` with `--config`** <br />
Similarly, you can use `kedro new` but additionally pass in a configuration file, for example:

```bash
kedro new --config=config.yml
```

The file enables you to customise details such as the project folder name and package name.

The configuration file must contain:

- `output_dir`: The path in which to create the project directory, which can be set to `~` for the home directory or `.` for the current working directory.
- `project_name`
- `repo_name`
- `python_package`

Additionally, the configuration file may contain:

- `tools`: The tools to customise your project setup with. Select from comma-separated values `lint, test, log, docs, data, pyspark, viz` or `all/none`. Omitting this from your configuration file will result in the default selection of `none`.
- `example_pipeline`: Indicate `yes` or `no` to select whether you would like your project to be populated with example code. Omitting this from your configuration file will result in the default selection of `no`.

The `output_dir` can be specified as `~` for the home directory or `.` for the current working directory. Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: My First Kedro Project
repo_name: testing-kedro
python_package: test_kedro
```

> **Note**
> When the `--config` flag is used together with `--name`, `--tools`, or `--example`, the values provided directly on the CLI will overwrite those specified in the configuration file.


**Use `kedro new` with a `--starter`** <br />
You can create a new Kedro project with a [starter](./starters.md) that adds code for a common project use case.

> **Important**
> You cannot combine the use of a Kedro starter with the tools and example code options listed above.

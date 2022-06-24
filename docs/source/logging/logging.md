# Logging

Kedro uses [Python's `logging` library](https://docs.python.org/3/library/logging.html). Configuration is provided as a dictionary according to the [Python logging configuration schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema) in two places:
1. [Default configuration built into the Kedro framework](https://github.com/kedro-org/kedro/blob/main/kedro/framework/project/logging.yml). This cannot be altered.
2. Your project-side logging configuration. Every project generated using Kedro's CLI `kedro new` command includes a file `conf/base/logging.yml`. You can alter this configuration and provide different configurations for different run environment according to the [standard Kedro mechanism for handling configuration](../kedro_project_setup/configuration.md).

```{note}
Providing project-side logging configuration is entirely optional. You can delete the `conf/base/logging.yml` file and Kedro will run using the framework's built in configuration.
```

Framework-side and project-side logging configuration are loaded through subsequent calls to [`logging.config.dictConfig`](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig). This means that, when it is provided, the project-side logging configuration typically _fully overwrites_ the framework-side logging configuration. [Incremental configuration](https://docs.python.org/3/library/logging.config.html#incremental-configuration) is also possible if the `incremental` key is explicitly set to `True` in your project-side logging configuration.

## Default framework-side logging configuration

Kedro's [default logging configuration](https://github.com/kedro-org/kedro/blob/main/kedro/framework/project/config/default_logging.yml) defines a handler called `rich` that uses the [Rich logging handler](https://rich.readthedocs.io/en/stable/logging.html) to format messages. We also use the [Rich traceback handler](https://rich.readthedocs.io/en/stable/traceback.html) to render exceptions.

By default, Python only shows logging messages at level `WARNING` and above. Kedro's logging configuration specifies that `INFO` level messages from Kedro should also be emitted. This makes it easier to track the progress of your pipeline when you perform a `kedro run`.

## Project-side logging configuration

In addition to the `rich` handler defined in Kedro's framework, the [project-side `conf/base/logging.yml`](https://github.com/kedro-org/kedro/blob/main/kedro/templates/project/%7B%7B%20cookiecutter.repo_name%20%7D%7D/conf/base/logging.yml) defines three further logging handlers:
* `console`: show logs on standard output (typically your terminal screen) without any rich formatting
* `info_file_handler`: write logs of level `INFO` and above to `logs/info.log`
* `error_file_handler`: write logs of level `ERROR` and above to `logs/error.log`

The logging handlers that are actually used by default are `rich`, `info_file_handler` and `error_file_handler`.

The project-side logging configuration also ensures that [logs emitted from your project's logger](#perform-logging-in-your-project) should be shown if they are `INFO` level or above (as opposed to the Python default of `WARNING`).

We now give some common examples of how you might like to change your project's logging configuration.

### Disable file-based logging

You might sometimes need to disable file-based logging, e.g. if you are running Kedro on a read-only file system such as [Databricks Repos](https://docs.databricks.com/repos/index.html). The simplest way to do this is to delete your `conf/base/logging.yml` file. The `logs` directory can then also be safely removed. With no project-side logging configuration specified, Kedro uses the default framework-side logging configuration, which does not include any file-based handlers.

Alternatively, if you would like to keep other configuration in `conf/base/logging.yml` and just disable file-based logging, then you can remove the file-based handlers from the `root` logger as follows:
```diff
 root:
-  handlers: [console, info_file_handler, error_file_handler]
+  handlers: [console]
```

### Use plain console logging

To use plain rather than rich logging, swap the `rich` handler for the `console` one as follows:

```diff
 root:
-  handlers: [rich, info_file_handler, error_file_handler]
+  handlers: [console, info_file_handler, error_file_handler]
```

### Rich logging in a dumb terminal

Rich [detects whether your terminal is capable](https://rich.readthedocs.io/en/stable/console.html#terminal-detection) of displaying richly formatted messages. If your terminal is "dumb" then formatting is automatically stripped out so that the logs are just plain text. This is likely to happen if you perform `kedro run` on CI (e.g. GitHub Actions or CircleCI).

If you find that the default wrapping of the log messages is too narrow but do not wish to switch to using the `console` logger on CI then the simplest way to control the log message wrapping is through altering the `COLUMNS` and `LINES` environment variables. For example:

```bash
export COLUMNS=120 LINES=25
```

```{note}
You must provide a value for both `COLUMNS` and `LINES` even if you only wish to change the width of the log message. Rich's default values for these variables are `COLUMNS=80` and `LINE=25`.
```

### Rich logging in Jupyter

Rich also formats the logs in JupyterLab and Jupyter Notebook. The size of the output console does not adapt to your window but can be controlled through the `JUPYTER_COLUMNS` and `JUPYTER_LINES` environment variables. The default values (115 and 100 respectively) should be suitable for most users, but if you require a different output console size then you should alter the values of `JUPYTER_COLUMNS` and `JUPYTER_LINES`.

## Perform logging in your project

To perform logging in your own code (e.g. in a node), you are advised to do as follows:

```python
import logging

log = logging.getLogger(__name__)
log.warning("Issue warning")
log.info("Send information")
```

```{note}
The name of a logger corresponds to a key in the `loggers`  section in `logging.yml` (e.g. `kedro`). See [Python's logging documentation](https://docs.python.org/3/library/logging.html#logger-objects) for more information.
```

You can take advantage of rich's [console markup](https://rich.readthedocs.io/en/stable/markup.html) when enabled in your logging calls:
```python
log.error("[bold red blink]Important error message![/]", extra={"markup": True})
```

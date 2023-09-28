# Logging


Kedro uses [Python's `logging` library](https://docs.python.org/3/library/logging.html). Configuration is provided as a dictionary according to the [Python logging configuration schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema) in Kedro's default logging configuration, as described below.

By default, Python only shows logging messages at level `WARNING` and above. Kedro's logging configuration specifies that `INFO` level messages from Kedro should also be emitted. This makes it easier to track the progress of your pipeline when you perform a `kedro run`.

# Default logging configuration
Kedro's [default logging configuration](https://github.com/kedro-org/kedro/blob/main/kedro/framework/project/default_logging.yml) defines a handler called `rich` that uses the [Rich logging handler](https://rich.readthedocs.io) to format messages. We also use the Rich traceback handler to render exceptions.

## How to perform logging in your Kedro project
To add logging to your own code (e.g. in a node):

```python
import logging

logger = logging.getLogger(__name__)
logger.warning("Issue warning")
logger.info("Send information")
logger.debug("Useful information for debugging")
```

You can use Rich's [console markup](https://rich.readthedocs.io/en/stable/markup.html) in your logging calls:

```python
log.error("[bold red blink]Important error message![/]", extra={"markup": True})
```

## How to customise Kedro logging

To customise logging in your Kedro project, you need to specify the path to a project-specific logging configuration file. Change the environment variable `KEDRO_LOGGING_CONFIG` to override the default logging configuration. Point the variable instead to your project-specific configuration, which we recommend you store inside the project's`conf` folder, and name `logging.yml`.

For example, you can set `KEDRO_LOGGING_CONFIG` by typing the following into your terminal:

```bash
export KEDRO_LOGGING_CONFIG=<project_root>/conf/logging.yml
```

After setting the environment variable, any subsequent Kedro commands use the logging configuration file at the specified path.

```{note}
If the `KEDRO_LOGGING_CONFIG` environment variable is not set, Kedro will use the [default logging configuration](https://github.com/kedro-org/kedro/blob/main/kedro/framework/project/default_logging.yml).
```

### How to show DEBUG level messages
To see `DEBUG` level messages, change the level of logging in your project-specific logging configuration file (`logging.yml`). We provide a `logging.yml` template:

<details>
<summary><b>Click to expand the <code>logging.yml</code> template</b></summary>
<code>

```yaml
version: 1

disable_existing_loggers: False

formatters:
  simple:
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: simple
    stream: ext://sys.stdout

  info_file_handler:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: simple
    filename: info.log
    maxBytes: 10485760 # 10MB
    backupCount: 20
    encoding: utf8
    delay: True

  rich:
    class: kedro.logging.RichHandler
    rich_tracebacks: True
    # Advance options for customisation.
    # See https://docs.kedro.org/en/stable/logging/logging.html#project-side-logging-configuration
    # tracebacks_show_locals: False

loggers:
  kedro:
    level: INFO

  your_python_package:
    level: INFO

root:
  handlers: [rich]
```
</code>
</details>

You need to change the line:
```diff
loggers:
  kedro:
    level: INFO

  your_python_package:
-   level: INFO
+   level: DEBUG
```

```{note}
The name of a logger corresponds to a key in the `loggers` section of the logging configuration file (e.g. `kedro`). See [Python's logging documentation](https://docs.python.org/3/library/logging.html#logger-objects) for more information.
```

By changing the level value to `DEBUG` for the desired logger (e.g. `<your_python_package>`), you will start seeing `DEBUG` level messages in the log output.

## Advanced logging

In addition to the `rich` handler defined in Kedro's framework, we provide two additional handlers in the template.

* `console`: show logs on standard output (typically your terminal screen) without any rich formatting
* `info_file_handler`: write logs of level `INFO` and above to `info.log`

The following section illustrates some common examples of how to change your project's logging configuration.

## How to customise the `rich` handler

Kedro's `kedro.logging.RichHandler` is a subclass of [`rich.logging.RichHandler`](https://rich.readthedocs.io/en/stable/reference/logging.html#rich.logging.RichHandler) and supports the same set of arguments. By default, `rich_tracebacks` is set to `True` to use `rich` to render exceptions. However, you can disable it by setting `rich_tracebacks: False`.

```{note}
If you want to disable `rich`'s tracebacks, you must set `KEDRO_LOGGING_CONFIG` to point to your local config i.e. `conf/logging.yml`.
```

When `rich_tracebacks` is set to `True`, the configuration is propagated to [`rich.traceback.install`](https://rich.readthedocs.io/en/stable/reference/traceback.html#rich.traceback.install). If an argument is compatible with `rich.traceback.install`, it will be passed to the traceback's settings.

For instance, you can enable the display of local variables inside `logging.yml` to aid with debugging.

```diff
  rich:
    class: kedro.logging.RichHandler
    rich_tracebacks: True
+   tracebacks_show_locals: True
```

A comprehensive list of available options can be found in the [RichHandler documentation](https://rich.readthedocs.io/en/stable/reference/logging.html#rich.logging.RichHandler).

## How to enable file-based logging

File-based logging in Python projects aids troubleshooting and debugging. It offers better visibility into application's behaviour and it's easy to search. However, it does not work well with read-only systems such as [Databricks Repos](https://docs.databricks.com/repos/index.html).

To enable file-based logging,  add `info_file_handler` in your `root` logger as follows in your `conf/logging.yml` as follows:

```diff
 root:
-  handlers: [rich]
+  handlers: [rich, info_file_handler]
```

By default it only tracks `INFO` level messages, but it can be configured to capture any level of logs.

## How to use plain console logging

To use plain rather than rich logging, swap the `rich` handler for the `console` one as follows:

```diff
 root:
-  handlers: [rich]
+  handlers: [console]
```

## How to enable rich logging in a dumb terminal

Rich [detects whether your terminal is capable](https://rich.readthedocs.io/en/stable/console.html#terminal-detection) of displaying richly formatted messages. If your terminal is "dumb" then formatting is automatically stripped out so that the logs are just plain text. This is likely to happen if you perform `kedro run` on CI (e.g. GitHub Actions or CircleCI).

If you find that the default wrapping of the log messages is too narrow but do not wish to switch to using the `console` logger on CI then the simplest way to control the log message wrapping is through altering the `COLUMNS` and `LINES` environment variables. For example:

```bash
export COLUMNS=120 LINES=25
```

```{note}
You must provide a value for both `COLUMNS` and `LINES` even if you only wish to change the width of the log message. Rich's default values for these variables are `COLUMNS=80` and `LINE=25`.
```

## How to enable rich logging in Jupyter

Rich also formats the logs in JupyterLab and Jupyter Notebook. The size of the output console does not adapt to your window but can be controlled through the `JUPYTER_COLUMNS` and `JUPYTER_LINES` environment variables. The default values (115 and 100 respectively) should be suitable for most users, but if you require a different output console size then you should alter the values of `JUPYTER_COLUMNS` and `JUPYTER_LINES`.

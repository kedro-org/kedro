# Logging

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

Kedro uses, and facilitates the use of Python’s `logging` library, by providing a default logging configuration. This can be found in `conf/base/logging.yml` in every project generated using Kedro’s CLI `kedro new` command.

## Configure logging

You can configure the logging by simply instantiating `ProjectContext` class at the entry point of your application (e.g., `src/<package_name>/run.py`). Logging can be easily customised by overriding `_setup_logging()` in `ProjectContext` class as follow:

```python
class ProjectContext(KedroContext):

    # ...

    def _setup_logging(self) -> None:
        # Custom logging configuration here
        pass
```

The configuration should comply with the guidelines from the `logging` library. Find more about it [here](https://docs.python.org/3/library/logging.html).

## Use logging

After configuring the logging using the example above, `kedro` will start emitting the logs automatically. To log your own code, you are advised to do the following:

```python
import logging
log = logging.getLogger(__name__)
log.warning("Issue warning")
log.info("Send information")
```

## Logging for `anyconfig`

By default, [anyconfig](https://github.com/ssato/python-anyconfig) library that is used by `kedro` to read configuration files emits a log message with `INFO` level on every read. To reduce the amount of logs being sent for CLI calls, default project logging configuration in `conf/base/logging.yml` sets the level for `anyconfig` logger to `WARNING`.

If you would like `INFO` level messages to propagate, you can update `anyconfig` logger level in `conf/base/logging.yml` as follows:

```yaml
loggers:
    anyconfig:
        level: INFO  # change
        handlers: [console, info_file_handler, error_file_handler]
        propagate: no
```

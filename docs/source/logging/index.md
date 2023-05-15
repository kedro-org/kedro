# Logging


Kedro uses [Python's `logging` library](https://docs.python.org/3/library/logging.html). Configuration is provided as a dictionary according to the [Python logging configuration schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema) in two places:
1. [Default configuration built into the Kedro framework](https://github.com/kedro-org/kedro/blob/main/kedro/framework/project/default_logging.yml). This cannot be altered.
2. Your project-side logging configuration. Every project generated using Kedro's CLI `kedro new` command includes a file `conf/base/logging.yml`. You can alter this configuration and provide different configurations for different run environment according to the [standard Kedro mechanism for handling configuration](../configuration/configuration_basics.md).

```{note}
Providing project-side logging configuration is entirely optional. You can delete the `conf/base/logging.yml` file and Kedro will run using the framework's built in configuration.
```

Framework-side and project-side logging configuration are loaded through subsequent calls to [`logging.config.dictConfig`](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig). This means that, when it is provided, the project-side logging configuration typically _fully overwrites_ the framework-side logging configuration. [Incremental configuration](https://docs.python.org/3/library/logging.config.html#incremental-configuration) is also possible if the `incremental` key is explicitly set to `True` in your project-side logging configuration.


```{toctree}
:hidden:

logging
```

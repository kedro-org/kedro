# Logging

> *Note:* This documentation is based on `Kedro 0.14.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

Kedro uses, and facilitates the use of Python’s `logging` library, by providing a default logging configuration. This can be found in `conf/base/logging.yml` in every project generated using Kedro’s CLI `kedro new` command.

## Configure logging

You can configure the logging by simply adding the following lines at the entry point of your application (e.g., `src/<package_name>/run.py`):

```python
from logging.config import dictConfig
from kedro.config import ConfigLoader

conf_paths = ['conf/base', 'conf/local']
conf_loader = ConfigLoader(conf_paths)
conf_logging = conf_loader.get('logging*', 'logging*/**')
dictConfig(conf_logging)
```

The configuration should comply with the guidelines from the `logging` library. Find more about it [here](https://docs.python.org/3/library/logging.html).

## Use logging

After configuring the logging using the example above, `kedro` will start emitting the logs automatically. To log your own code, you are advised to do the following:

```python
import logging
log = logging.getLogger(__name__)
log.warning('Issue warning')
log.info('Send information')
```

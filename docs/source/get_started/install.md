# Install Kedro

To install Kedro from the Python Package Index (PyPI), simply run:

```bash
pip install kedro
```

```{note}
It is also possible to install Kedro using `conda install -c conda-forge kedro` but we recommend you use `pip` at this point to eliminate any potential dependency issues:
```

Both `pip` and `conda` install the core Kedro module, which includes the CLI tool, project template, pipeline abstraction, framework, and support for configuration.

## Verify a successful installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number: for example,

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [frequently asked questions](../faq/faq.md), check out the [searchable archive from our retired Discord server](https://linen-discord.kedro.org) or post a new query on the [Slack organisation](https://slack.kedro.org/).

## Install a development version

To try out a development version of Kedro direct from the [Kedro Github repository](https://github.com/kedro-org/kedro), follow [these steps](../faq/faq.md#how-can-i-use-a-development-version-of-kedro).

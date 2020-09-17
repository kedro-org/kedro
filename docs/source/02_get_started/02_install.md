# Install Kedro

To install Kedro from the Python Package Index (PyPI) simply run:

```bash
pip install kedro
```

It is also possible to install Kedro using `conda`:

```bash
conda install -c conda-forge kedro
```

Both approaches install the core Kedro module, which includes the CLI tool, project template, pipeline abstraction, framework, and support for configuration.

## Verify a successful installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [frequently asked questions](../12_faq/01_faq.md) or Kedro community support on [Stack Overflow](https://stackoverflow.com/questions/tagged/kedro).

## Install a development version

You can try out a development version of Kedro direct from the [Kedro Github repository](https://github.com/quantumblacklabs/kedro) by following [these steps](../12_faq/01_faq.md#how-can-i-use-a-development-version-of-kedro).

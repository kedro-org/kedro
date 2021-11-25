# Install Kedro

To install Kedro from the Python Package Index (PyPI) simply run:

```bash
pip install kedro
```

```eval_rst
.. note::  It is also possible to install Kedro using ``conda``, as follows, but we recommend using ``pip`` at this point to eliminate any potential dependency issues, as follows:
```

```bash
conda install -c conda-forge kedro
```

Both `pip` and `conda` install the core Kedro module, which includes the CLI tool, project template, pipeline abstraction, framework, and support for configuration.

## Verify a successful installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [frequently asked questions](../faq/faq.md), check out [GitHub Discussions](https://github.com/quantumblacklabs/kedro/discussions) or talk to the community on the [Discord Server](https://discord.gg/akJDeVaxnB).

## Install a development version

You can try out a development version of Kedro direct from the [Kedro Github repository](https://github.com/quantumblacklabs/kedro) by following [these steps](../faq/faq.md#how-can-i-use-a-development-version-of-kedro).

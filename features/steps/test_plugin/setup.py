from setuptools import find_packages, setup

setup(
    name="test_plugin",
    version="0.1",
    description="Dummy plugin with hook implementations",
    packages=find_packages(),
    entry_points={"kedro.hooks": ["test_plugin = plugin:hooks"]},
)

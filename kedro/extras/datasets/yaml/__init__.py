"""``AbstractDataSet`` implementation to load/save data from/to a YAML file."""

__all__ = ["YAMLDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .yaml_dataset import YAMLDataSet

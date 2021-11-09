"""Provides I/O for TensorFlow Models."""

__all__ = ["TensorFlowModelDataset"]

from contextlib import suppress

with suppress(ImportError):
    from .tensorflow_model_dataset import TensorFlowModelDataset

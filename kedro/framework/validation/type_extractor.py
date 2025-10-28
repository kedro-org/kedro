"""Type extractor for extracting type hints from various sources."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, get_type_hints

from .exceptions import ValidationError

if TYPE_CHECKING:
    from .source_filters import SourceFilter


class TypeExtractor:
    """Extracts type requirements from various sources like pipeline nodes."""

    def __init__(self, source_filter: SourceFilter):
        """Initialize the type extractor.

        Args:
            source_filters: List of source filters to use for extraction.
        """
        self.logger = logging.getLogger(__name__)
        self.source_filter = source_filter

    def extract_types_from_pipelines(self) -> dict[str, type]:
        """Extract all type requirements from available pipelines using configured source filters.

        Returns:
            Dictionary mapping source keys to their expected types
        """
        try:
            from kedro.framework.project import pipelines
        except ImportError:
            self.logger.warning(
                "Could not import pipelines from kedro.framework.project"
            )
            return {}
        except Exception as exc:
            self.logger.warning(f"Error importing pipelines: {exc}")
            return {}

        all_type_requirements = {}
        pipeline_dict = dict(pipelines)

        for pipeline_name, pipeline in pipeline_dict.items():
            # Skip __default__ pipeline to avoid duplicate processing
            if pipeline_name == "__default__":
                continue

            pipeline_type_requirements = self._extract_types_from_pipeline(pipeline)
            all_type_requirements.update(pipeline_type_requirements)

        self.logger.debug(
            f"Found {len(all_type_requirements)} type requirements across all pipelines"
        )
        return all_type_requirements

    def _extract_types_from_pipeline(self, pipeline) -> dict[str, type]:
        """Extract type requirements from a single pipeline.

        Args:
            pipeline: Pipeline object to analyze

        Returns:
            Dictionary mapping source keys to their expected types
        """
        type_requirements = {}

        for node in getattr(pipeline, "nodes", []):
            node_type_requirements = self.extract_types_from_node(node)
            type_requirements.update(node_type_requirements)

        return type_requirements

    def extract_types_from_node(self, node) -> dict[str, type]:
        """Extract typed requirements from a single node using configured source filters.

        Args:
            node: Node object to analyze

        Returns:
            Dictionary mapping source keys to their expected types
        """
        func = getattr(node, "func", None)
        if func is None:
            return {}

        try:
            sig = inspect.signature(func)
            type_hints = get_type_hints(func, include_extras=False)
        except Exception as exc:
            self.logger.warning(
                f"Could not extract type hints from function {func.__name__}: {exc}"
            )
            return {}

        # Map dataset names to argument names
        dataset_to_arg = self._build_dataset_to_arg_mapping(node, sig)

        # Extract requirements using configured source filters
        all_requirements = {}

        for ds_name, arg_name in dataset_to_arg.items():
            expected_type = type_hints.get(arg_name)
            if not expected_type:
                continue

            if self.source_filter.should_process(ds_name):
                source_key = self.source_filter.extract_key(ds_name)
                all_requirements[source_key] = expected_type
                log_message = self.source_filter.get_log_message(
                    source_key, expected_type.__name__
                )
                self.logger.debug(log_message)

        return all_requirements

    def _build_dataset_to_arg_mapping(self, node, signature) -> dict[str, str]:
        """Build mapping from dataset names to argument names.

        Args:
            node: Node object
            signature: Function signature

        Returns:
            Dictionary mapping dataset names to argument names
        """
        dataset_to_arg = {}
        node_inputs = getattr(node, "inputs", None)

        if isinstance(node_inputs, dict):
            dataset_to_arg.update(node_inputs)
        elif isinstance(node_inputs, list) or isinstance(node_inputs, tuple):
            sig_param_names = list(signature.parameters.keys())
            for idx, ds in enumerate(node_inputs):
                if idx < len(sig_param_names):
                    dataset_to_arg[ds] = sig_param_names[idx]

        return dataset_to_arg

    def resolve_nested_path(self, data: dict, path: str) -> Any:
        """Handle nested paths like 'database.host'.

        Args:
            data: Data dictionary
            path: Dot-separated path

        Returns:
            Value at the specified path or None if not found
        """
        if "." not in path:
            return data.get(path)

        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def set_nested_value(self, data: dict, path: str, value: Any) -> None:
        """Set nested value supporting dot notation.

        Args:
            data: Data dictionary to modify
            path: Dot-separated path
            value: Value to set
        """
        if "." not in path:
            data[path] = value
            return

        keys = path.split(".")
        current = data

        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                # Can't set nested value if intermediate value is not a dict
                raise ValidationError(
                    f"Cannot set nested value '{path}': intermediate key '{key}' is not a dictionary"
                )
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

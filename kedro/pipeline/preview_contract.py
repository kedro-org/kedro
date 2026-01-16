from __future__ import annotations

import json
from abc import ABC
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import (
    Any,
    Literal,
    TypeAlias,
    Union,
)

# JSON-safe type system
JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = Union[JSONScalar, "JSONObject", "JSONArray"]
JSONObject: TypeAlias = dict[str, JSONValue]
JSONArray: TypeAlias = list[JSONValue]
Meta: TypeAlias = dict[str, JSONValue]


def assert_json_value(data: Any, path: str = "$") -> None:
    """
    Raise TypeError if data is not JSON-serializable.

    Uses json.dumps() to validate serializability while checking dict keys are strings.
    """
    # Check dict keys are strings (json.dumps allows non-string keys in some cases)
    if isinstance(data, dict):
        for key in data.keys():
            if not isinstance(key, str):
                raise TypeError(
                    f"{path}: object keys must be str, got {type(key).__name__}"
                )

    # Let json.dumps validate everything else
    try:
        json.dumps(data)
    except (TypeError, ValueError) as e:
        raise TypeError(
            f"{path}: value is not JSON-serializable, got {type(data).__name__}"
        ) from e


@dataclass(frozen=True)
class BasePreview(ABC):
    """Base class for all preview types with shared functionality."""

    meta: Meta | None = field(default=None, kw_only=True)

    def to_dict(self) -> JSONObject:
        """Convert preview to JSON-serializable dict."""
        if not is_dataclass(self) or isinstance(self, type):
            raise TypeError(f"Not JSON-serializable: {type(self).__name__}")

        # Validate meta only when serializing
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

        return asdict(self)


def _validate_type(value: Any, expected_type: type, field_name: str) -> None:
    """Validate that value is an instance of expected_type."""
    if not isinstance(value, expected_type):
        raise TypeError(
            f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}"
        )


def _validate_non_empty_str(value: Any, field_name: str) -> None:
    """Validate that value is a non-empty string."""
    if not isinstance(value, str) or not value:
        raise TypeError(f"{field_name} must be a non-empty str")


def _validate_table_rows(rows: list[dict[str, JSONValue]], field_name: str) -> None:
    """Validate that table rows are properly formatted."""
    for i, row in enumerate(rows):
        _validate_type(row, dict, f"{field_name}[{i}]")
        if not all(isinstance(k, str) for k in row.keys()):
            raise TypeError(f"{field_name}[{i}] keys must be str")
        assert_json_value(row, path=f"$.content[{i}]")


@dataclass(frozen=True)
class TextPreview(BasePreview):
    content: str
    kind: Literal["text"] = field(default="text", init=False)

    def __post_init__(self) -> None:
        _validate_type(self.content, str, "TextPreview.content")


@dataclass(frozen=True)
class MermaidPreview(BasePreview):
    content: str
    kind: Literal["mermaid"] = field(default="mermaid", init=False)

    def __post_init__(self) -> None:
        _validate_type(self.content, str, "MermaidPreview.content")


@dataclass(frozen=True)
class JsonPreview(BasePreview):
    content: JSONValue
    kind: Literal["json"] = field(default="json", init=False)

    def __post_init__(self) -> None:
        assert_json_value(self.content, "$.content")


@dataclass(frozen=True)
class TablePreview(BasePreview):
    content: list[dict[str, JSONValue]]
    kind: Literal["table"] = field(default="table", init=False)

    def __post_init__(self) -> None:
        _validate_type(self.content, list, "TablePreview.content")
        _validate_table_rows(self.content, "TablePreview.content")


@dataclass(frozen=True)
class PlotlyPreview(BasePreview):
    content: JSONObject
    kind: Literal["plotly"] = field(default="plotly", init=False)

    def __post_init__(self) -> None:
        _validate_type(self.content, dict, "PlotlyPreview.content")
        assert_json_value(self.content, "$.content")


@dataclass(frozen=True)
class ImagePreview(BasePreview):
    content: str  # URL or data URI (e.g., "data:image/png;base64,...")
    kind: Literal["image"] = field(default="image", init=False)

    def __post_init__(self) -> None:
        _validate_type(self.content, str, "ImagePreview.content")


@dataclass(frozen=True)
class CustomPreview(BasePreview):
    renderer_key: str
    content: JSONObject
    kind: Literal["custom"] = field(default="custom", init=False)

    def __post_init__(self) -> None:
        _validate_non_empty_str(self.renderer_key, "CustomPreview.renderer_key")
        _validate_type(self.content, dict, "CustomPreview.content")
        assert_json_value(self.content, "$.content")


PreviewPayload: TypeAlias = (
    TextPreview
    | MermaidPreview
    | JsonPreview
    | TablePreview
    | PlotlyPreview
    | ImagePreview
    | CustomPreview
)

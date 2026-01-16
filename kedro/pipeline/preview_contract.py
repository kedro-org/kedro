from __future__ import annotations

import json
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


def _validate_meta(meta: Meta | None) -> None:
    """Validate that meta is JSON-serializable if provided."""
    if meta is not None:
        assert_json_value(meta, "$.meta")


@dataclass(frozen=True)
class TextPreview:
    content: str
    meta: Meta | None = None
    kind: Literal["text"] = field(default="text", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("TextPreview.content must be str")
        _validate_meta(self.meta)

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class MermaidPreview:
    content: str
    meta: Meta | None = None
    kind: Literal["mermaid"] = field(default="mermaid", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("MermaidPreview.content must be str")
        _validate_meta(self.meta)

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class JsonPreview:
    content: JSONValue
    meta: Meta | None = None
    kind: Literal["json"] = field(default="json", init=False)

    def __post_init__(self) -> None:
        assert_json_value(self.content, "$.content")
        _validate_meta(self.meta)

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class TablePreview:
    content: list[dict[str, JSONValue]]
    meta: Meta | None = None
    kind: Literal["table"] = field(default="table", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.content, list):
            raise TypeError("TablePreview.content must be a list")
        for i, row in enumerate(self.content):
            if not isinstance(row, dict):
                raise TypeError(f"TablePreview.content[{i}] must be a dict")
            if not all(isinstance(k, str) for k in row.keys()):
                raise TypeError(f"TablePreview.content[{i}] keys must be str")
            assert_json_value(row, path=f"$.content[{i}]")
        _validate_meta(self.meta)

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class PlotlyPreview:
    content: JSONObject
    meta: Meta | None = None
    kind: Literal["plotly"] = field(default="plotly", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.content, dict):
            raise TypeError("PlotlyPreview.content must be a dict (JSON object)")
        assert_json_value(self.content, "$.content")
        _validate_meta(self.meta)

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class ImagePreview:
    content: str  # URL or data URI (e.g., "data:image/png;base64,...")
    meta: Meta | None = None
    kind: Literal["image"] = field(default="image", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("ImagePreview.content must be str")
        _validate_meta(self.meta)

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class CustomPreview:
    renderer_key: str
    content: JSONObject
    meta: Meta | None = None
    kind: Literal["custom"] = field(default="custom", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.renderer_key, str) or not self.renderer_key:
            raise TypeError("CustomPreview.renderer_key must be a non-empty str")
        if not isinstance(self.content, dict):
            raise TypeError("CustomPreview.content must be dict (JSON object)")
        assert_json_value(self.content, "$.content")
        _validate_meta(self.meta)

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


PreviewPayload: TypeAlias = (
    TextPreview
    | MermaidPreview
    | JsonPreview
    | TablePreview
    | PlotlyPreview
    | ImagePreview
    | CustomPreview
)


# JSON serialization helpers
def _dataclass_to_json_dict(payload: Any) -> JSONObject:
    """Convert payload to a pure-JSON dict via asdict."""
    if not is_dataclass(payload) or isinstance(payload, type):
        raise TypeError(f"Not JSON-serializable: {type(payload).__name__}")

    return asdict(payload)

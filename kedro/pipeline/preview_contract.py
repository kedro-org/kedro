from __future__ import annotations

import base64
import re
from dataclasses import asdict, dataclass, is_dataclass
from typing import (
    Any,
    Literal,
    TypeAlias,
    Union,
    cast,
)

# JSON-safe type system
JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = Union[JSONScalar, "JSONObject", "JSONArray"]
JSONObject: TypeAlias = dict[str, JSONValue]
JSONArray: TypeAlias = list[JSONValue]
Meta: TypeAlias = dict[str, JSONValue]


def _is_json_scalar(data: Any) -> bool:
    return data is None or isinstance(data, str | bool | int | float)


def assert_json_value(data: Any, path: str = "$") -> None:
    """
    Raise TypeError if data is not JSON-serializable according to JSONValue.

    """
    if _is_json_scalar(data):
        return

    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"{path}: object keys must be str, got {type(key).__name__}"
                )
            assert_json_value(value, f"{path}.{key}")
        return

    if isinstance(data, list | tuple):
        for key, value in enumerate(data):
            assert_json_value(value, f"{path}[{key}]")
        return

    raise TypeError(
        f"{path}: value is not JSON-serializable, got {type(data).__name__}"
    )


# Table Payloads
@dataclass(frozen=True)
class ColumnDef:
    key: str
    label: str | None = None
    type: Literal["string", "number", "boolean", "date", "json"] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key:
            raise TypeError("ColumnDef.key must be a non-empty str")


@dataclass(frozen=True)
class TableContent:
    """
    Strict table contract:
      - rows: list[dict[str, JSONValue]] (JSON-safe cell values)
      - optional columns: defines order, labels, formatting, etc.
    """

    rows: list[dict[str, JSONValue]]
    columns: list[ColumnDef] | None = None
    row_id_key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.rows, list):
            raise TypeError("TableContent.rows must be a list")

        for i, row in enumerate(self.rows):
            if not isinstance(row, dict):
                raise TypeError(f"TableContent.rows[{i}] must be dict[str, JSONValue]")
            if not all(isinstance(k, str) for k in row.keys()):
                raise TypeError(f"TableContent.rows[{i}] keys must be str")
            assert_json_value(row, path=f"$.content.rows[{i}]")

        if self.columns is not None:
            if not isinstance(self.columns, list):
                raise TypeError("TableContent.columns must be list[ColumnDef] or None")
            keys = [col.key for col in self.columns]
            if len(set(keys)) != len(keys):
                raise TypeError("TableContent.columns contains duplicate keys")

        if self.row_id_key is not None and not isinstance(self.row_id_key, str):
            raise TypeError("TableContent.row_id_key must be str or None")


# Image Payloads
@dataclass(frozen=True)
class ImageUrl:
    source: Literal["url"]
    url: str

    def __post_init__(self) -> None:
        if not isinstance(self.url, str) or not self.url:
            raise TypeError("ImageUrl.url must be a non-empty str")


@dataclass(frozen=True)
class ImageBase64:
    source: Literal["base64"]
    data: str  # base64 only, no "data:image/png;base64," prefix
    mime: str  # "image/png", "image/jpeg", ...

    def __post_init__(self) -> None:
        if not isinstance(self.mime, str) or not re.match(
            r"^image\/[a-zA-Z0-9.+-]+$", self.mime
        ):
            raise TypeError(f"Invalid image mime: {self.mime!r}")

        if not isinstance(self.data, str) or not self.data:
            raise TypeError("ImageBase64.data must be a non-empty base64 string")

        try:
            base64.b64decode(self.data, validate=True)
        except Exception as e:
            raise TypeError("ImageBase64.data is not valid base64") from e


ImageContent: TypeAlias = ImageUrl | ImageBase64


@dataclass(frozen=True)
class TextPreview:
    kind: Literal["text"]
    content: str
    meta: Meta | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("TextPreview.content must be str")
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class MermaidPreview:
    kind: Literal["mermaid"]
    content: str
    meta: Meta | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("MermaidPreview.content must be str")
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class JsonPreview:
    kind: Literal["json"]
    content: JSONValue
    meta: Meta | None = None

    def __post_init__(self) -> None:
        assert_json_value(self.content, "$.content")
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class TablePreview:
    kind: Literal["table"]
    content: TableContent
    meta: Meta | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, TableContent):
            raise TypeError("TablePreview.content must be TableContent")
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class PlotlyPreview:
    kind: Literal["plotly"]
    # Plotly figure is JSON object; keep it JSON-safe
    content: JSONObject
    meta: Meta | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, dict):
            raise TypeError("PlotlyPreview.content must be a dict (JSON object)")
        assert_json_value(self.content, "$.content")
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class ImagePreview:
    kind: Literal["image"]
    content: ImageContent
    meta: Meta | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, ImageUrl | ImageBase64):
            raise TypeError("ImagePreview.content must be ImageUrl or ImageBase64")
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

    def to_dict(self) -> JSONObject:
        return _dataclass_to_json_dict(self)


@dataclass(frozen=True)
class CustomPreview:
    kind: Literal["custom"]
    renderer_key: str
    content: JSONObject
    meta: Meta | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.renderer_key, str) or not self.renderer_key:
            raise TypeError("CustomPreview.renderer_key must be a non-empty str")
        if not isinstance(self.content, dict):
            raise TypeError("CustomPreview.content must be dict (JSON object)")
        assert_json_value(self.content, "$.content")
        if self.meta is not None:
            assert_json_value(self.meta, "$.meta")

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
    """
    Convert payload to a pure-JSON dict:
      - dataclasses -> dict
      - tuples -> lists
      - ensures final output is JSONValue
    """

    def convert(data: Any) -> JSONValue:
        if _is_json_scalar(data):
            return cast(JSONValue, data)

        if isinstance(data, dict):
            out: dict[str, JSONValue] = {}
            for key, value in data.items():
                if not isinstance(key, str):
                    # keys must be str
                    raise TypeError(
                        f"Non-str key encountered during serialization: {key!r}"
                    )
                out[key] = convert(value)
            return out

        if isinstance(data, list | tuple):
            return [convert(value) for value in data]

        if is_dataclass(data) and not isinstance(data, type):
            return convert(asdict(data))

        raise TypeError(f"Not JSON-serializable: {type(data).__name__}")

    serializable_payload = convert(payload)

    if not isinstance(serializable_payload, dict):
        raise TypeError(
            "PreviewPayload serialization must produce a JSON object at top-level"
        )

    assert_json_value(serializable_payload, "$")

    return serializable_payload

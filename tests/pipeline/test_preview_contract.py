"""Tests for preview_contract module."""

import pytest

from kedro.pipeline.preview_contract import (
    CustomPreview,
    ImagePreview,
    JsonPreview,
    MermaidPreview,
    PlotlyPreview,
    TablePreview,
    TextPreview,
    assert_json_value,
)


class TestAssertJsonValue:
    """Tests for assert_json_value validation function."""

    def test_valid_scalar_values(self):
        """Test that scalar values are accepted."""
        assert_json_value(None)
        assert_json_value("string")
        assert_json_value(123)
        assert_json_value(45.67)
        assert_json_value(True)
        assert_json_value(False)

    def test_valid_dict(self):
        """Test that valid dicts are accepted."""
        assert_json_value({"key": "value", "num": 123, "bool": True})

    def test_valid_list(self):
        """Test that valid lists are accepted."""
        assert_json_value([1, 2, "three", None, True])

    def test_valid_nested_structure(self):
        """Test that nested structures are accepted."""
        assert_json_value(
            {
                "data": [1, 2, 3],
                "nested": {"key": "value"},
                "mixed": [{"a": 1}, {"b": 2}],
            }
        )

    def test_invalid_dict_with_non_string_key(self):
        """Test that dicts with non-string keys are rejected."""
        with pytest.raises(TypeError, match="object keys must be str, got int"):
            assert_json_value({1: "value"})

    def test_invalid_non_json_serializable(self):
        """Test that non-JSON-serializable types are rejected."""
        with pytest.raises(
            TypeError, match="value is not JSON-serializable, got object"
        ):
            assert_json_value(object())

    def test_invalid_nested_non_json_serializable(self):
        """Test that nested non-JSON-serializable values are rejected."""
        with pytest.raises(TypeError, match=r"\$: value is not JSON-serializable"):
            assert_json_value({"data": object()})

    def test_invalid_in_list(self):
        """Test that non-JSON-serializable values in lists are rejected."""
        with pytest.raises(TypeError, match=r"\$: value is not JSON-serializable"):
            assert_json_value([1, object(), 3])


class TestTextPreview:
    """Tests for TextPreview dataclass."""

    def test_valid_text_preview(self):
        """Test creating valid TextPreview."""
        preview = TextPreview(content="Hello world")
        assert preview.kind == "text"
        assert preview.content == "Hello world"
        assert preview.meta is None

    def test_text_preview_with_meta(self):
        """Test TextPreview with metadata."""
        preview = TextPreview(content="Hello", meta={"lang": "en"})
        assert preview.meta == {"lang": "en"}

    def test_text_preview_invalid_content(self):
        """Test that non-string content is rejected."""
        with pytest.raises(TypeError, match="TextPreview.content must be str"):
            TextPreview(content=123)

    def test_text_preview_invalid_meta(self):
        """Test that non-JSON-serializable meta is rejected."""
        with pytest.raises(TypeError, match="value is not JSON-serializable"):
            TextPreview(content="test", meta={"obj": object()})

    def test_text_preview_to_dict(self):
        """Test TextPreview serialization."""
        preview = TextPreview(content="Hello", meta={"key": "value"})
        result = preview.to_dict()
        assert result["kind"] == "text"
        assert result["content"] == "Hello"
        assert result["meta"] == {"key": "value"}


class TestMermaidPreview:
    """Tests for MermaidPreview dataclass."""

    def test_valid_mermaid_preview(self):
        """Test creating valid MermaidPreview."""
        preview = MermaidPreview(content="graph LR\n A --> B")
        assert preview.kind == "mermaid"
        assert preview.content == "graph LR\n A --> B"

    def test_mermaid_preview_invalid_content(self):
        """Test that non-string content is rejected."""
        with pytest.raises(TypeError, match="MermaidPreview.content must be str"):
            MermaidPreview(content=["not", "string"])

    def test_mermaid_preview_to_dict(self):
        """Test MermaidPreview serialization."""
        preview = MermaidPreview(content="graph TD\n A")
        result = preview.to_dict()
        assert result["kind"] == "mermaid"
        assert result["content"] == "graph TD\n A"


class TestJsonPreview:
    """Tests for JsonPreview dataclass."""

    def test_valid_json_preview_with_dict(self):
        """Test creating valid JsonPreview with dict."""
        preview = JsonPreview(content={"key": "value"})
        assert preview.kind == "json"
        assert preview.content == {"key": "value"}

    def test_valid_json_preview_with_list(self):
        """Test creating valid JsonPreview with list."""
        preview = JsonPreview(content=[1, 2, 3])
        assert preview.kind == "json"
        assert preview.content == [1, 2, 3]

    def test_json_preview_invalid_content(self):
        """Test that non-JSON-serializable content is rejected."""
        with pytest.raises(TypeError, match="value is not JSON-serializable"):
            JsonPreview(content=object())

    def test_json_preview_to_dict(self):
        """Test JsonPreview serialization."""
        preview = JsonPreview(content={"data": [1, 2, 3]})
        result = preview.to_dict()
        assert result["kind"] == "json"
        assert result["content"] == {"data": [1, 2, 3]}


class TestTablePreview:
    """Tests for TablePreview dataclass."""

    def test_valid_table_preview(self):
        """Test creating valid TablePreview."""
        preview = TablePreview(content=[{"name": "Alice", "age": 30}])
        assert preview.kind == "table"
        assert preview.content == [{"name": "Alice", "age": 30}]

    def test_table_preview_non_list_content(self):
        """Test that non-list content is rejected."""
        with pytest.raises(TypeError, match="TablePreview.content must be list"):
            TablePreview(content="not a list")

    def test_table_preview_non_dict_row(self):
        """Test that non-dict rows are rejected."""
        with pytest.raises(TypeError, match=r"TablePreview.content\[0\] must be dict"):
            TablePreview(content=["not a dict"])

    def test_table_preview_row_with_non_string_key(self):
        """Test that rows with non-string keys are rejected."""
        with pytest.raises(
            TypeError, match=r"TablePreview.content\[0\] keys must be str"
        ):
            TablePreview(content=[{1: "value"}])

    def test_table_preview_non_json_serializable_cell(self):
        """Test that non-JSON-serializable cell values are rejected."""
        with pytest.raises(TypeError, match="value is not JSON-serializable"):
            TablePreview(content=[{"data": object()}])

    def test_table_preview_to_dict(self):
        """Test TablePreview serialization."""
        preview = TablePreview(content=[{"id": 1, "name": "Alice"}])
        result = preview.to_dict()
        assert result["kind"] == "table"
        assert result["content"] == [{"id": 1, "name": "Alice"}]


class TestPlotlyPreview:
    """Tests for PlotlyPreview dataclass."""

    def test_valid_plotly_preview(self):
        """Test creating valid PlotlyPreview."""
        preview = PlotlyPreview(content={"data": [], "layout": {}})
        assert preview.kind == "plotly"
        assert preview.content == {"data": [], "layout": {}}

    def test_plotly_preview_invalid_content_type(self):
        """Test that non-dict content is rejected."""
        with pytest.raises(TypeError, match="PlotlyPreview.content must be dict"):
            PlotlyPreview(content="not a dict")

    def test_plotly_preview_invalid_content_value(self):
        """Test that non-JSON-serializable content is rejected."""
        with pytest.raises(TypeError, match="value is not JSON-serializable"):
            PlotlyPreview(content={"obj": object()})

    def test_plotly_preview_to_dict(self):
        """Test PlotlyPreview serialization."""
        preview = PlotlyPreview(content={"data": [1, 2]})
        result = preview.to_dict()
        assert result["kind"] == "plotly"
        assert result["content"]["data"] == [1, 2]


class TestImagePreview:
    """Tests for ImagePreview dataclass."""

    def test_valid_image_preview_with_url(self):
        """Test creating valid ImagePreview with URL."""
        preview = ImagePreview(content="https://example.com/img.png")
        assert preview.kind == "image"
        assert preview.content == "https://example.com/img.png"

    def test_valid_image_preview_with_data_uri(self):
        """Test creating valid ImagePreview with data URI."""
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        preview = ImagePreview(content=data_uri)
        assert preview.kind == "image"
        assert preview.content == data_uri

    def test_image_preview_invalid_content(self):
        """Test that non-string content is rejected."""
        with pytest.raises(TypeError, match="ImagePreview.content must be str"):
            ImagePreview(content=123)

    def test_image_preview_to_dict(self):
        """Test ImagePreview serialization."""
        preview = ImagePreview(content="https://example.com/img.png")
        result = preview.to_dict()
        assert result["kind"] == "image"
        assert result["content"] == "https://example.com/img.png"


class TestCustomPreview:
    """Tests for CustomPreview dataclass."""

    def test_valid_custom_preview(self):
        """Test creating valid CustomPreview."""
        preview = CustomPreview(
            renderer_key="my_renderer",
            content={"data": "value"},
        )
        assert preview.kind == "custom"
        assert preview.renderer_key == "my_renderer"
        assert preview.content == {"data": "value"}

    def test_custom_preview_empty_renderer_key(self):
        """Test that empty renderer_key is rejected."""
        with pytest.raises(
            TypeError, match="CustomPreview.renderer_key must be a non-empty str"
        ):
            CustomPreview(renderer_key="", content={})

    def test_custom_preview_non_string_renderer_key(self):
        """Test that non-string renderer_key is rejected."""
        with pytest.raises(
            TypeError, match="CustomPreview.renderer_key must be a non-empty str"
        ):
            CustomPreview(renderer_key=123, content={})

    def test_custom_preview_invalid_content_type(self):
        """Test that non-dict content is rejected."""
        with pytest.raises(TypeError, match="CustomPreview.content must be dict"):
            CustomPreview(renderer_key="key", content="not dict")

    def test_custom_preview_invalid_content_value(self):
        """Test that non-JSON-serializable content is rejected."""
        with pytest.raises(TypeError, match="value is not JSON-serializable"):
            CustomPreview(renderer_key="key", content={"obj": object()})

    def test_custom_preview_to_dict(self):
        """Test CustomPreview serialization."""
        preview = CustomPreview(
            renderer_key="viz",
            content={"type": "chart"},
        )
        result = preview.to_dict()
        assert result["kind"] == "custom"
        assert result["renderer_key"] == "viz"
        assert result["content"]["type"] == "chart"


class TestSerializationEdgeCases:
    """Tests for edge cases in serialization."""

    def test_to_dict_on_preview_instances(self):
        """Test that preview instances can be serialized to dict."""
        preview = TextPreview(content="test", meta={"key": "value"})
        result = preview.to_dict()

        assert result["kind"] == "text"
        assert result["content"] == "test"
        assert result["meta"] == {"key": "value"}

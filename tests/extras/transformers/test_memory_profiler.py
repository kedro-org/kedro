import importlib

import pytest

import kedro.extras.transformers.memory_profiler as tf


class TestMemoryTransformer:
    def test_memory_usage(self, catalog, caplog):
        expected_log = "MiB memory at peak time"
        catalog.add_transformer(tf.ProfileMemoryTransformer())

        catalog.save("test", 42)
        assert "Saving test consumed" in caplog.text
        assert expected_log in caplog.text
        caplog.clear()
        assert catalog.load("test") == 42
        assert "Loading test consumed" in caplog.text
        assert expected_log in caplog.text

    def test_import_error(self, mocker):
        mocker.patch.dict("sys.modules", {"memory_profiler": None})
        pattern = (
            r".*`pip install kedro\[profilers\]` to get the required "
            "memory profiler dependencies"
        )
        with pytest.raises(ImportError, match=pattern):
            importlib.reload(tf)

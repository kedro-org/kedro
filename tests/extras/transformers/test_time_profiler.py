from kedro.extras.transformers import ProfileTimeTransformer


class TestTransformers:
    def test_timing(self, catalog, caplog):
        catalog.add_transformer(ProfileTimeTransformer())

        catalog.save("test", 42)
        assert "Saving test took" in caplog.text
        assert catalog.load("test") == 42
        assert "Loading test took" in caplog.text

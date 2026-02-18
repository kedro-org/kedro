from __future__ import annotations


class TestParameterSourceFilter:
    def test_should_process_params_prefix(self, source_filter):
        assert source_filter.should_process("params:model_options") is True

    def test_should_process_non_params(self, source_filter):
        assert source_filter.should_process("companies") is False

    def test_should_process_non_string(self, source_filter):
        assert source_filter.should_process(123) is False

    def test_extract_key(self, source_filter):
        assert source_filter.extract_key("params:model_options") == "model_options"

    def test_extract_key_nested(self, source_filter):
        assert (
            source_filter.extract_key("params:model_options.test_size")
            == "model_options.test_size"
        )

    def test_get_log_message(self, source_filter):
        msg = source_filter.get_log_message("model_options", "ModelOptions")
        assert "model_options" in msg
        assert "ModelOptions" in msg


class TestDatasetSourceFilter:
    def test_should_process_non_params(self, dataset_filter):
        assert dataset_filter.should_process("companies") is True

    def test_should_process_params_prefix(self, dataset_filter):
        assert dataset_filter.should_process("params:model_options") is False

    def test_should_process_non_string(self, dataset_filter):
        assert dataset_filter.should_process(123) is False

    def test_extract_key(self, dataset_filter):
        assert dataset_filter.extract_key("companies") == "companies"

    def test_get_log_message(self, dataset_filter):
        msg = dataset_filter.get_log_message("companies", "CSVDataset")
        assert "companies" in msg
        assert "CSVDataset" in msg

import pytest

from kedro.naming import slugify_name, uniquify_name


class TestSlugifyName:
    def test_basic(self):
        assert slugify_name("Sales Revenue (Q1)") == "sales_revenue_q1"

    def test_collapses_underscores(self):
        assert slugify_name("a---b___c") == "a_b_c"

    def test_leading_digit(self):
        assert slugify_name("123abc") == "_123abc"

    def test_only_invalid_chars(self):
        assert slugify_name("!!!") == "_"

    def test_strips(self):
        assert slugify_name("  Hello World  ") == "hello_world"

    def test_type_error(self):
        with pytest.raises(TypeError):
            slugify_name(123)  


class TestUniquifyName:
    def test_unique_when_free(self):
        taken = {"x", "y"}
        assert uniquify_name("z", taken) == "z"

    def test_appends_suffix(self):
        taken = {"model_output", "model_output_1"}
        assert uniquify_name("model output", taken) == "model_output_2"

    def test_respects_slugify(self):
        taken = set()
        # base becomes "a_b"
        assert uniquify_name("A B", taken) == "a_b"

    def test_many_collisions(self):
        taken = {f"dataset_{i}" for i in range(1, 6)}
        taken.add("dataset")
        assert uniquify_name("dataset", taken) == "dataset_6"




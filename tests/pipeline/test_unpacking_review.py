from collections import UserDict

import pytest

from kedro.pipeline import node, pipeline


def train(data, a, b):
    return data + a + b


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"namespace": "ns", "inputs": {"data"}}, ["data", "params:ns.options"]),
        ({"parameters": {"options": "alt"}}, ["data", "params:alt"]),
        ({"inputs": {"data": "other"}}, ["other", "params:options"]),
    ],
)
def test_modular_unpacking(kwargs, expected):
    base = pipeline([node(train, ["data", "**params:options"], "out")])
    actual = pipeline(base, **kwargs).nodes[0]
    assert actual.inputs == expected
    assert actual.run({expected[0]: 1, expected[1]: {"a": 2, "b": 3}}) == {
        "out" if "namespace" not in kwargs else "ns.out": 6
    }


def test_all_parameters_not_namespaced():
    base = pipeline([node(lambda **kw: kw, "**parameters", "out")])
    actual = pipeline(base, namespace="ns").nodes[0]
    assert actual._inputs == "**parameters"
    assert actual.run({"parameters": {"a": 1}}) == {"ns.out": {"a": 1}}


@pytest.mark.parametrize(
    "inputs, function",
    [
        ({"data": "d", "a": "**params:p"}, lambda data, a: None),
        (["d", "**"], lambda d, **kw: None),
    ],
)
def test_invalid_unpacking_rejected_at_definition(inputs, function):
    with pytest.raises((ValueError, TypeError)):
        node(function, inputs, "out")


@pytest.mark.parametrize("spec", ["**params:p", ["**params:p"]])
def test_non_mapping_error_identifies_node_and_dataset(spec):
    n = node(lambda **kw: kw, spec, "out", name="training")
    with pytest.raises(TypeError, match="training.*params:p.*mapping"):
        n.run({"params:p": 1})


def test_mapping_subclass_supported():
    assert node(lambda **kw: kw, "**params:p", "out").run(
        {"params:p": UserDict(a=1)}
    ) == {"out": {"a": 1}}


def test_duplicate_unpacked_keys_rejected():
    n = node(lambda **kw: kw, ["**params:x", "**params:y"], "out")
    with pytest.raises(TypeError, match="multiple values.*k"):
        n.run({"params:x": {"k": 1}, "params:y": {"k": 2}})


def test_positional_key_collision_remains_rejected():
    n = node(lambda d, a: (d, a), ["data", "**params:x"], "out")
    with pytest.raises(TypeError, match="multiple values"):
        n.run({"data": 1, "params:x": {"d": 2, "a": 3}})


def test_type_extraction_does_not_consume_unpacking_slot():
    import inspect

    from kedro.validation.type_extractor import TypeExtractor

    def function(data, a, options):
        return data, a, options

    n = node(function, ["data", "**params:p", "params:options"], "out")
    assert TypeExtractor._build_dataset_to_arg_mapping(
        n, inspect.signature(function)
    ) == {"data": "data", "params:options": "a"}


def test_load_node_generated_code_unpacks_dictionaries():
    from kedro.ipython import _load_node

    n = node(train, ["data", "**params:options"], "out", name="training")
    cells = _load_node("training", {"p": pipeline([n])})

    class Catalog:
        def load(self, name):
            return {"data": 1, "params:options": {"a": 2, "b": 3}}[name]

    namespace = {"catalog": Catalog(), "train": train}
    exec(cells[0], namespace)  # noqa: S102 - execute generated debugging code against synthetic inputs
    assert eval(cells[-1], namespace) == 6  # noqa: S307 - generated call uses only synthetic inputs
    assert "**" in cells[-1]


@pytest.mark.parametrize("spec", ["**params:p", ["**params:p"]])
def test_unpacked_non_string_keys_rejected(spec):
    n = node(lambda **kw: kw, spec, "out")
    with pytest.raises(TypeError, match="keywords must be strings"):
        n.run({"params:p": {1: "value"}})


def test_namespace_with_parameter_remap():
    base = pipeline([node(train, ["data", "**params:options"], "out")])
    actual = pipeline(
        base, namespace="ns", inputs={"data"}, parameters={"options": "other"}
    ).nodes[0]
    assert actual._inputs == ["data", "**params:other"]
    assert actual.run({"data": 1, "params:other": {"a": 2, "b": 3}}) == {"ns.out": 6}


def test_unpacking_before_later_positional_input():
    n = node(train, ["**params:options", "data"], "out")
    assert n.run({"data": 1, "params:options": {"a": 2, "b": 3}}) == {"out": 6}


@pytest.mark.parametrize("kind", ["ordinary", "positional_only", "varargs"])
def test_empty_unpacking_without_remaining_named_parameters(kind):
    def ordinary(value):
        return value

    def positional_only(value, /):
        return value

    def varargs(*values):
        return values

    function = {
        "ordinary": ordinary,
        "positional_only": positional_only,
        "varargs": varargs,
    }[kind]
    n = node(function, ["data", "**params:extra"], "out")
    expected = (5,) if kind == "varargs" else 5
    assert n.run({"data": 5, "params:extra": {}}) == {"out": expected}
    with pytest.raises(TypeError):
        n.run({"data": 5, "params:extra": {"unexpected": 7}})


def test_non_identifier_string_keyword_is_supported():
    n = node(lambda **kwargs: kwargs, "**params:extra", "out")
    assert n.run({"params:extra": {"not-valid": 3}}) == {"out": {"not-valid": 3}}

# YAML

``YAMLLocalDataset`` loads and saves data to a local yaml file using ``PyYAML``.
See [PyYAMLDocumentation](https://pyyaml.org/wiki/PyYAMLDocumentation) for details.


#### Example use:

```python
from kedro.contrib.io.yaml_local import YAMLLocalDataSet
my_dict = {
    'a_string': 'Hello, World!',
    'a_list': [1, 2, 3]
}
data_set = YAMLLocalDataSet(filepath="test.yml")
data_set.save(my_dict)
reloaded = data_set.load()
assert my_dict == reloaded
```

#### Example catalog.yml:

```yaml
example_yaml_data:
  type: kedro.contrib.io.yaml_local.YAMLLocalDataSet
  filepath: data/08_reporting/test.yml
```

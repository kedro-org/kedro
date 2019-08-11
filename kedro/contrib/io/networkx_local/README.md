# NetworkX

``NetworkXLocalDataset`` loads and saves graphs to a local json file in node/link format using
``NetworkX``.
See [NetworkX Documentation](https://networkx.github.io/documentation/stable/tutorial.html) for details.


#### Example use:

```python
from kedro.contrib.io.networkx_label import NetworkXLocalDataSet
import networkx
graph = networkx.complete_graph(100)
graph_dataset = NetworkXLocalDataSet(filepath="test.json")
graph_dataset.save(graph)
reloaded = graph_dataset.load()
assert graph == reloaded
```

#### Example catalog.yml:

```yaml
example_graph_data:
  type: kedro.contrib.io.networkx_local.NetworkXLocalDataSet
  filepath: data/08_reporting/test.yml
```

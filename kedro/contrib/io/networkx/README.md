# NetworkX

``NetworkXLocalDataset`` loads and saves graphs to a local JSON file in node/link format using
``NetworkX``.
See [NetworkX Documentation](https://networkx.github.io/documentation/stable/tutorial.html) for details.


#### Example use:

```python
from kedro.contrib.io.networkx import NetworkXLocalDataSet
import networkx as nx
graph = nx.complete_graph(100)
graph_dataset = NetworkXLocalDataSet(filepath="test.json")
graph_dataset.save(graph)
reloaded = graph_dataset.load()
assert nx.is_isomorphic(graph, reloaded)
```

#### Example catalog.yml:

```yaml
example_graph_data:
  type: kedro.contrib.io.networkx.NetworkXLocalDataSet
  filepath: data/02_intermediate/test.json
```

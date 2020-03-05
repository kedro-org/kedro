# GeoJSON

``GeoJSONDataSet`` loads and saves data to a local yaml file using ``geopandas``.
See [geopandas.GeoDataFrame](http://geopandas.org/reference/geopandas.GeoDataFrame.html) for details.

#### Example use:

```python
import geopandas as gpd
from shapely.geometry import Point
from kedro.extras.datasets.geopandas import GeoJSONDataSet

data = gpd.GeoDataFrame(
    {"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]},
    geometry=[Point(1, 1), Point(2, 4)],
)
data_set = GeoJSONDataSet(filepath="test.geojson")
data_set.save(data)
reloaded = data_set.load()
assert data.equals(reloaded)
``

#### Example catalog.yml:

```yaml
example_geojson_data:
  type: geopandas.GeoJSONDataSet
  filepath: data/08_reporting/test.geojson
```

Contributed by (Luis Blanche)[https://github.com/lblanche].

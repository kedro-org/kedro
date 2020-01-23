# GeoJSON

``GeoJSONDataSet`` loads and saves data to a local yaml file using ``geopandas``.
See [geopandas.GeoDataFrame](http://geopandas.org/reference/geopandas.GeoDataFrame.html) for details.


#### Example use:

```python
import geopandas as gpd
from kedro.contrib.io.geojson import GeoJSONDataSet
my_gdf = data = gpd.GeoDataFrame({'col1': [1, 2],
                                  'col2': [4, 5],
                                  'col3': [5, 6]},
                                  geometry=[Point(1,1), Point(2,4)])
data_set = GeoJSONDataSet(filepath="test.geojson")
data_set.save(data)
reloaded = data_set.load()
assert data.equals(reloaded)
```

#### Example catalog.yml:

```yaml
example_geojson_data:
  type: kedro.contrib.io.geojson_local.GeoJSONDataSet
  filepath: data/08_reporting/test.geojson
```

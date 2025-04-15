# How to use Ibis with Kedro for SQL queries

[Ibis](https://ibis-project.org/) is an open-source Python library that provides a high-level, Pythonic interface for SQL queries. It allows users to write SQL queries using Python syntax, which are then translated into actual SQL code for execution on various database backends. Ibis supports multiple database engines including PostgreSQL, MySQL, SQLite, Google BigQuery, and many others.

Integrating Ibis with Kedro enables you to efficiently execute SQL queries as part of your data workflows without needing to resort to hardcoded SQL or less flexible methods. This integration provides several benefits:

- **Centralized SQL Query Management**: Define SQL queries in Python code, allowing for version control within your Kedro project repository
- **Database Engine Flexibility**: Switch between different database backends without changing your query syntax
- **Performance Optimizations**: Push down SQL operations to the database, optimizing performance and reducing data movement

## Prerequisites

You will need the following:

- A working Kedro project in a virtual environment
- Ibis installed in the same virtual environment
- Access to a supported database (PostgreSQL, MySQL, SQLite, etc.)

To set yourself up, install Ibis and the appropriate database connector:

```bash
pip install ibis-framework

# Install the appropriate backend connector
# For PostgreSQL
pip install 'ibis-framework[postgres]'
# For MySQL
pip install 'ibis-framework[mysql]'
# For SQLite
pip install 'ibis-framework[sqlite]'
# For BigQuery
pip install 'ibis-framework[bigquery]'
```

## Setting up Ibis in your Kedro project

### Configure database connection

The first step is to configure your database connection in your Kedro project. We recommend storing your database connection parameters in your configuration files.

Create a file at `conf/base/db.yml` with your database connection parameters:

```yaml
# conf/base/db.yml
database:
  type: postgres  # or mysql, sqlite, bigquery, etc.
  host: localhost
  port: 5432
  database: mydatabase
  username: myuser
  password: ${DB_PASSWORD}  # Use credentials from environment variables
```

### Initialize Ibis connection using a hook

You can initialize your Ibis connection using a Kedro hook to ensure it's available before your pipeline runs. Create a hook in `src/<package_name>/hooks.py`:

```python
from kedro.framework.hooks import hook_impl
import ibis


class IbisHooks:
    @hook_impl
    def after_context_created(self, context) -> None:
        """Initialize an Ibis connection using the config
        defined in project's conf folder.
        """
        # Load the database configuration
        db_config = context.config_loader["database"]
        
        # Store the connection in the context for later use
        if db_config["type"] == "postgres":
            context.ibis_conn = ibis.postgres.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["username"],
                password=db_config["password"]
            )
        elif db_config["type"] == "mysql":
            context.ibis_conn = ibis.mysql.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["username"],
                password=db_config["password"]
            )
        elif db_config["type"] == "sqlite":
            context.ibis_conn = ibis.sqlite.connect(db_config["database"])
        elif db_config["type"] == "bigquery":
            context.ibis_conn = ibis.bigquery.connect(
                project_id=db_config["project_id"],
                dataset_id=db_config["dataset_id"]
            )
        else:
            raise ValueError(f"Unsupported database type: {db_config['type']}")
```

Register your hook in `src/<package_name>/__init__.py`:

```python
from <package_name>.hooks import IbisHooks

hooks = [IbisHooks()]
```

## Creating an Ibis dataset for Kedro's DataCatalog

To integrate Ibis with Kedro's DataCatalog, you can create a custom dataset that handles Ibis tables and query results. Here's an example implementation:

```python
# src/<package_name>/extras/datasets/ibis_dataset.py
from typing import Any, Dict

from kedro.io import AbstractDataSet
import ibis
import pandas as pd


class IbisTableDataSet(AbstractDataSet):
    """``IbisTableDataSet`` loads and saves data from/to a SQL database using Ibis.
    
    This dataset represents an Ibis table in a database.
    """

    def __init__(self, connection, table_name=None, query=None):
        """Initialize the dataset.
        
        Args:
            connection: An Ibis connection object or a callable that returns one
            table_name: Name of the table in the database (if loading an existing table)
            query: An Ibis expression to execute (alternative to table_name)
        """
        self._connection = connection
        self._table_name = table_name
        self._query = query
        
        if not (table_name or query):
            raise ValueError("Either table_name or query must be provided")
        if table_name and query:
            raise ValueError("Only one of table_name or query should be provided")

    def _load(self) -> ibis.expr.types.TableExpr:
        """Load the data."""
        conn = self._connection() if callable(self._connection) else self._connection
        
        if self._table_name:
            return conn.table(self._table_name)
        return self._query

    def _save(self, data: ibis.expr.types.TableExpr) -> None:
        """Save the Ibis expression results to a table."""
        if self._table_name:
            conn = self._connection() if callable(self._connection) else self._connection
            # Execute the expression and save results to the specified table
            data.execute().to_sql(self._table_name, conn.con, if_exists="replace")

    def _describe(self) -> Dict[str, Any]:
        """Return a description of the dataset."""
        return {
            "table_name": self._table_name,
            "has_query": self._query is not None
        }
```

## Configuring the DataCatalog

Now you can configure your DataCatalog to use the Ibis dataset. Add the following to your `conf/base/catalog.yml`:

```yaml
# conf/base/catalog.yml
customers_table:
  type: <package_name>.extras.datasets.ibis_dataset.IbisTableDataSet
  connection: ${ibis_connection}
  table_name: customers

filtered_customers:
  type: <package_name>.extras.datasets.ibis_dataset.IbisTableDataSet
  connection: ${ibis_connection}
  query: ${ibis_query}
```

You'll need to provide the connection and query objects in your `catalog_dict` when creating the `DataCatalog`:

```python
from kedro.framework.context import KedroContext
from kedro.framework.hooks import hook_impl


class ProjectContext(KedroContext):
    @hook_impl
    def register_catalog(self, catalog, credentials, load_versions, save_version, journal):
        # Get the Ibis connection from the context
        ibis_connection = lambda: self.ibis_conn
        
        # Define an example query
        def ibis_query():
            customers = self.ibis_conn.table('customers')
            return customers.filter(customers.age > 30)
        
        # Add these objects to the catalog's dictionary
        catalog.add_feed_dict({
            'ibis_connection': ibis_connection,
            'ibis_query': ibis_query()
        })
        
        return catalog
```

## Using Ibis in Kedro nodes

Now you can use Ibis in your Kedro nodes to perform SQL operations. Here's an example of a node that uses Ibis to transform data:

```python
def filter_customers(customers_table: ibis.expr.types.TableExpr) -> ibis.expr.types.TableExpr:
    """Filter customers by age and calculate average purchase amount."""
    # Filter customers older than 25
    filtered = customers_table.filter(customers_table.age > 25)
    
    # Group by customer_id and calculate average purchase amount
    result = filtered.group_by('customer_id').aggregate(
        avg_purchase=filtered.purchase_amount.mean(),
        total_purchases=filtered.purchase_amount.count()
    )
    
    return result


def join_customer_orders(customers: ibis.expr.types.TableExpr, 
                        orders: ibis.expr.types.TableExpr) -> ibis.expr.types.TableExpr:
    """Join customers with their orders."""
    # Join customers and orders on customer_id
    joined = customers.join(orders, customers.id == orders.customer_id)
    
    # Select relevant columns
    result = joined.select([
        customers.id,
        customers.name,
        orders.order_date,
        orders.amount
    ])
    
    return result
```

Add these nodes to your pipeline:

```python
from kedro.pipeline import Pipeline, node


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=filter_customers,
                inputs="customers_table",
                outputs="filtered_customers",
                name="filter_customers_node",
            ),
            node(
                func=join_customer_orders,
                inputs=["customers_table", "orders_table"],
                outputs="customer_orders",
                name="join_customer_orders_node",
            ),
        ]
    )
```

## Best practices

### Structuring SQL queries in your Kedro project

- **Modularize your queries**: Create reusable Ibis expressions in separate modules
- **Avoid hardcoded SQL**: Use Ibis expressions instead of raw SQL strings
- **Use Kedro parameters**: Parameterize your queries using Kedro's parameter system

### Performance optimization

- **Push operations to the database**: Let Ibis push down operations to the database when possible
- **Use appropriate indexes**: Ensure your database tables have proper indexes for your queries
- **Limit data transfer**: Only select the columns you need to minimize data movement

### Error handling and debugging

- **Log query execution**: Use Kedro's logging system to log query execution
- **Handle database errors**: Implement proper error handling for database connection issues
- **Debug with .compile()**: Use Ibis's `.compile()` method to see the generated SQL

## Example: Complete pipeline with Ibis

Here's a complete example of a Kedro pipeline that uses Ibis for SQL operations:

```python
# src/<package_name>/pipelines/data_processing/nodes.py
import ibis
from ibis import _


def load_customers(conn) -> ibis.expr.types.TableExpr:
    """Load customers table from database."""
    return conn.table('customers')


def load_orders(conn) -> ibis.expr.types.TableExpr:
    """Load orders table from database."""
    return conn.table('orders')


def filter_high_value_customers(customers: ibis.expr.types.TableExpr, 
                               min_value: float) -> ibis.expr.types.TableExpr:
    """Filter customers with high total order value."""
    return customers.filter(customers.lifetime_value > min_value)


def join_with_orders(customers: ibis.expr.types.TableExpr,
                    orders: ibis.expr.types.TableExpr) -> ibis.expr.types.TableExpr:
    """Join customers with their orders."""
    return customers.join(orders, customers.id == orders.customer_id)


def aggregate_order_stats(joined_data: ibis.expr.types.TableExpr) -> ibis.expr.types.TableExpr:
    """Calculate order statistics by customer."""
    return joined_data.group_by(joined_data.customer_id).aggregate(
        total_orders=joined_data.order_id.count(),
        avg_order_value=joined_data.amount.mean(),
        max_order_value=joined_data.amount.max(),
        min_order_value=joined_data.amount.min()
    )


def to_pandas(expr: ibis.expr.types.TableExpr) -> pd.DataFrame:
    """Execute the Ibis expression and return a pandas DataFrame."""
    return expr.execute()


# src/<package_name>/pipelines/data_processing/pipeline.py
from kedro.pipeline import Pipeline, node
from kedro.pipeline.modular_pipeline import pipeline

from .<package_name>.pipelines.data_processing.nodes import (
    load_customers,
    load_orders,
    filter_high_value_customers,
    join_with_orders,
    aggregate_order_stats,
    to_pandas
)


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=load_customers,
                inputs="ibis_connection",
                outputs="customers_table",
                name="load_customers_node",
            ),
            node(
                func=load_orders,
                inputs="ibis_connection",
                outputs="orders_table",
                name="load_orders_node",
            ),
            node(
                func=filter_high_value_customers,
                inputs=["customers_table", "params:min_customer_value"],
                outputs="high_value_customers",
                name="filter_high_value_customers_node",
            ),
            node(
                func=join_with_orders,
                inputs=["high_value_customers", "orders_table"],
                outputs="joined_customer_orders",
                name="join_with_orders_node",
            ),
            node(
                func=aggregate_order_stats,
                inputs="joined_customer_orders",
                outputs="customer_order_stats_ibis",
                name="aggregate_order_stats_node",
            ),
            node(
                func=to_pandas,
                inputs="customer_order_stats_ibis",
                outputs="customer_order_stats_df",
                name="to_pandas_node",
            ),
        ]
    )
```

## Conclusion

Integrating Ibis with Kedro provides a powerful way to work with SQL databases in your data pipelines. By using Ibis, you can write SQL queries in a Pythonic way, making them more maintainable and easier to version control. The integration allows you to leverage the strengths of both tools: Kedro's pipeline management and Ibis's SQL query capabilities.

This approach offers several advantages:

1. **Maintainability**: SQL queries are written in Python, making them easier to maintain and version control
2. **Flexibility**: Switch between different database backends without changing your query syntax
3. **Performance**: Push down operations to the database for optimal performance
4. **Integration**: Seamlessly integrate SQL operations with the rest of your Kedro pipeline

By following the best practices outlined in this guide, you can build efficient, maintainable data pipelines that leverage the power of SQL databases through Ibis and Kedro.
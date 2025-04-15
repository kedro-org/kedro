# Ibis integration

[Ibis](https://ibis-project.org/) is an open-source Python library that provides a high-level, Pythonic interface for SQL queries. It allows users to write SQL queries using Python syntax, which are then translated into actual SQL code for execution on various database backends. Ibis supports multiple database engines including PostgreSQL, MySQL, SQLite, Google BigQuery, DuckDB, and many others.

Integrating Ibis with Kedro enables you to efficiently execute SQL queries as part of your data workflows without needing to resort to hardcoded SQL or less flexible methods. This integration provides several benefits:

- **Centralized SQL Query Management**: Define SQL queries in Python code, allowing for version control within your Kedro project repository
- **Database Engine Flexibility**: Switch between different database backends without changing your query syntax
- **Performance Optimizations**: Push down SQL operations to the database, optimizing performance and reducing data movement

## Prerequisites

You will need the following:

- A working Kedro project in a virtual environment
- Ibis installed in the same virtual environment

To set yourself up, install Ibis and the appropriate database connector. We recommend using DuckDB as it's easy to install and use:

```bash
pip install ibis-framework

# Install DuckDB connector (recommended)
pip install 'ibis-framework[duckdb]'

# Or install other backend connectors if needed
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

The first step is to configure your database connection in your Kedro project. You should store your database connection parameters in your credentials configuration files for better security.

Create or update your file at `conf/local/credentials.yml` with your database connection parameters:

```yaml
# conf/local/credentials.yml
database:
  type: duckdb  # or postgres, mysql, sqlite, bigquery, etc.
  # For DuckDB, you only need to specify the path to the database file
  path: ${BASE_PATH}/data/database.duckdb
  
  # For other databases like PostgreSQL, you would include these parameters:
  # host: localhost
  # port: 5432
  # database: mydatabase
  # username: myuser
  # password: ${DB_PASSWORD}  # Use credentials from environment variables
```

## Using the Ibis TableDataset with Kedro's DataCatalog

Kedro provides a built-in `TableDataset` for Ibis in the `kedro-datasets` package. You can use this dataset to integrate Ibis tables with your Kedro pipelines.

First, install the required package:

```bash
pip install "kedro-datasets[ibis]"
```

Then, configure your DataCatalog to use the Ibis TableDataset. Add the following to your `conf/base/catalog.yml`:

```yaml
# conf/base/catalog.yml
customers_table:
  type: kedro_datasets.ibis.TableDataset
  credentials: database  # References the database config in credentials.yml
  table_name: customers

filtered_customers:
  type: kedro_datasets.ibis.TableDataset
  credentials: database
  table_name: customers
  query: SELECT * FROM customers WHERE age > 30

# Example of using Ibis expressions in catalog
high_value_customers:
  type: kedro_datasets.ibis.TableDataset
  credentials: database
  table_name: customers
  # Using Ibis expression for filtering
  ibis_expr: |
    def query(table):
        return table.filter(table.lifetime_value > 1000)

customer_orders:
  type: kedro_datasets.ibis.TableDataset
  credentials: database
  table_name: orders
  # Using Ibis expression for joining and aggregation
  ibis_expr: |
    def query(table):
        customers = context.catalog.load('customers_table')
        return table.join(
            customers,
            table.customer_id == customers.id
        ).group_by(table.customer_id).aggregate(
            total_orders=table.order_id.count(),
            avg_amount=table.amount.mean()
        )
```



## Creating a database connection from credentials

To use Ibis in your Kedro nodes, you'll need to create a database connection object from your credentials. You can do this by adding a custom dataset to your catalog that creates and provides an Ibis connection:

```yaml
# conf/base/catalog.yml
database_connection:
  type: kedro_datasets.ibis.IbisConnectionDataset
  credentials: database  # References the database config in credentials.yml
```

This will create an Ibis connection object that can be used in your nodes to interact with the database.

## Using Ibis in Kedro nodes

Now you can use Ibis in your Kedro nodes to perform SQL operations. Here's an example of a node that uses Ibis to transform data:

```python
def filter_customers(customers_table: ibis.expr.types.TableExpr) -> ibis.expr.types.TableExpr:
    """Filter customers by age and calculate average purchase amount."""
    # Filter customers older than 25
    filtered = customers_table.filter(customers_table.age > 25)
    
    # Group by customer_id and calculate average purchase amount
    result = filtered.group_by("customer_id").aggregate(
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

## Example: Complete pipeline with Ibis and DuckDB

Here's a complete example of a Kedro pipeline that uses Ibis with DuckDB for SQL operations:

```python
# src/<package_name>/pipelines/data_processing/nodes.py
import ibis
from ibis import _
import pandas as pd


def create_sample_data(conn) -> None:
    """Create sample tables in DuckDB for demonstration."""
    # Create customers table
    customers_df = pd.DataFrame({
        'id': range(1, 11),
        'name': [f'Customer {i}' for i in range(1, 11)],
        'age': [25, 40, 35, 28, 52, 19, 31, 45, 33, 60],
        'lifetime_value': [100.0, 2500.0, 550.0, 1200.0, 3000.0, 50.0, 750.0, 1800.0, 400.0, 5000.0]
    })
    
    # Create orders table
    orders_df = pd.DataFrame({
        'order_id': range(1, 21),
        'customer_id': [1, 2, 2, 3, 4, 5, 5, 5, 6, 7, 7, 8, 8, 8, 9, 9, 10, 10, 10, 10],
        'order_date': pd.date_range('2023-01-01', periods=20),
        'amount': [50.0, 100.0, 200.0, 150.0, 300.0, 500.0, 400.0, 600.0, 50.0, 75.0, 
                  80.0, 200.0, 300.0, 150.0, 100.0, 200.0, 1000.0, 1500.0, 800.0, 1200.0]
    })
    
    # Create tables in DuckDB
    conn.create_table('customers', customers_df)
    conn.create_table('orders', orders_df)


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
    create_sample_data,
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
                func=create_sample_data,
                inputs="database_connection",  # Connection object created from database credentials
                outputs=None,
                name="create_sample_data_node",
            ),
            node(
                func=load_customers,
                inputs="database_connection",  # Connection object created from database credentials
                outputs="customers_table",
                name="load_customers_node",
            ),
            node(
                func=load_orders,
                inputs="database_connection",  # Connection object created from database credentials
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
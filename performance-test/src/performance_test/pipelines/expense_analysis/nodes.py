from time import sleep

import pyspark.sql.functions as F
from pyspark.sql.window import Window


def analyze_expenses_per_party(congress_expenses, parameters):
    """Calculate total expense per party."""
    sleep( parameters["dataset_load_delay"])
    sleep(parameters["file_save_delay"])

    return congress_expenses.groupBy("sgpartido").agg(
        F.sum("vlrliquido").alias("total_expense")
    ).orderBy(F.desc("total_expense"))

def find_largest_expense_source(congress_expenses, parameters):
    """Find the largest source of expense."""
    sleep( parameters["dataset_load_delay"])
    sleep(parameters["file_save_delay"])

    return congress_expenses.groupBy("txtdescricao").agg(
        F.sum("vlrliquido").alias("total_expense")
    ).orderBy(F.desc("total_expense")).limit(1)

def find_top_spender_per_party(congress_expenses, parameters):
    """Find the top-spending congressman for each party."""
    sleep( parameters["dataset_load_delay"])
    sleep(parameters["file_save_delay"])

    return congress_expenses.groupBy("sgpartido", "txnomeparlamentar").agg(
        F.sum("vlrliquido").alias("total_spent")
    ).withColumn(
        "rank", F.row_number().over(Window.partitionBy("sgpartido").orderBy(F.desc("total_spent")))
    ).filter(F.col("rank") == 1).drop("rank")

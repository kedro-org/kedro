import os
from time import sleep

import pyspark.sql.functions as F
from pyspark.sql.window import Window

DATASET_LOAD_DELAY = int(os.getenv("DATASET_LOAD_DELAY", 0))
FILE_SAVE_DELAY = int(os.getenv("FILE_SAVE_DELAY", 0))

def analyze_expenses_per_party(congress_expenses):
    """Calculate total expense per party."""
    sleep(DATASET_LOAD_DELAY)
    sleep(FILE_SAVE_DELAY)
    return congress_expenses.groupBy("sgpartido").agg(
        F.sum("vlrliquido").alias("total_expense")
    ).orderBy(F.desc("total_expense"))

def find_largest_expense_source(congress_expenses):
    """Find the largest source of expense."""
    sleep(DATASET_LOAD_DELAY)
    sleep(FILE_SAVE_DELAY)
    return congress_expenses.groupBy("txtdescricao").agg(
        F.sum("vlrliquido").alias("total_expense")
    ).orderBy(F.desc("total_expense")).limit(1)

def find_top_spender_per_party(congress_expenses):
    """Find the top-spending congressman for each party."""
    sleep(DATASET_LOAD_DELAY)
    sleep(FILE_SAVE_DELAY)
    return congress_expenses.groupBy("sgpartido", "txnomeparlamentar").agg(
        F.sum("vlrliquido").alias("total_spent")
    ).withColumn(
        "rank", F.row_number().over(Window.partitionBy("sgpartido").orderBy(F.desc("total_spent")))
    ).filter(F.col("rank") == 1).drop("rank")

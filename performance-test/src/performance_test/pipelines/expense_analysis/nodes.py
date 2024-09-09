import pyspark.sql.functions as F


def analyze_expenses(congress_expenses):
    expenses_per_party = congress_expenses.groupBy("sgpartido").agg(
        F.sum("vlrliquido").alias("total_expense")
    ).orderBy(F.desc("total_expense"))

    largest_expense_source = congress_expenses.groupBy("txtdescricao").agg(
        F.sum("vlrliquido").alias("total_expense")
    ).orderBy(F.desc("total_expense")).limit(1)

    return expenses_per_party, largest_expense_source

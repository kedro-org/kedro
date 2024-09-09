"""
This is a boilerplate pipeline 'expense_analysis'
generated using Kedro 0.19.8
"""

from kedro.pipeline import Pipeline, node

from .nodes import analyze_expenses


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=analyze_expenses,
                inputs="congress_expenses",
                outputs=["expenses_per_party", "largest_expense_source"],
                name="analyze_expenses_node",
            )
        ]
    )

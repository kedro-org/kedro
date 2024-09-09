"""
This is a boilerplate pipeline 'expense_analysis'
generated using Kedro 0.19.8
"""

from kedro.pipeline import Pipeline, node

from .nodes import (
    analyze_expenses_per_party,
    find_largest_expense_source,
    find_top_spender_per_party,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=analyze_expenses_per_party,
                inputs="congress_expenses",
                outputs="expenses_per_party",
                name="analyze_expenses_per_party_node",
            ),
            node(
                func=find_largest_expense_source,
                inputs="congress_expenses",
                outputs="largest_expense_source",
                name="find_largest_expense_source_node",
            ),
            node(
                func=find_top_spender_per_party,
                inputs="congress_expenses",
                outputs="top_spender_per_party",
                name="find_top_spender_per_party_node",
            ),
        ]
    )

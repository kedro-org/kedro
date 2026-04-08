"""Missing value reporter utility for Kedro pipelines."""

import logging
from typing import Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)            #Flagged column will be noted in the text file starting with __name__


def generate_missing_value_report(
    df: pd.DataFrame,                           #Takes table of data as input
    threshold: float = 20.0                     #Set the threshold value that is 20% so if the column is more than 20% emoty flag it
) -> Dict[str, Any]:                            #Return a dictionary like a structured report
    """Generate a missing value report for a pandas DataFrame.

    Scans each column in the DataFrame and reports the null count,
    null percentage, and data type. Columns exceeding the threshold
    percentage are flagged for attention.

    Args:
        df: The input pandas DataFrame to analyse.
        threshold: Percentage of missing values above which a column
            is flagged. Defaults to 20.0.

    Returns:
        A dictionary containing:
            - total_rows: total number of rows in the DataFrame
            - columns: per-column stats (null_count, null_pct, dtype)
            - flagged_columns: list of columns exceeding the threshold

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, 3]})
        >>> report = generate_missing_value_report(df, threshold=50.0)
        >>> report["flagged_columns"]
        ['b']
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to missing value reporter.")     #Return a log stating total rows as 0,columns empty and flagged columns as empty with the warning if the table is completely empty
        return {
            "total_rows": 0,
            "columns": {},
            "flagged_columns": []
        }

    total_rows = len(df)                        #Count how many rows the table has
    column_stats: Dict[str, Any] = {}           #Create an empty container  to store each columns report    
    flagged_columns = []                        #Create an empty list to store bad columns

    for col in df.columns:
        null_count = int(df[col].isnull().sum())            #Count how many blank columns are in this column
        null_pct = round((null_count / total_rows) * 100, 2)    #Convert into percentage
        dtype = str(df[col].dtype)                          #stores the type of data in the column

        column_stats[col] = {           #Storing the null counts and the data types in columns
            "null_count": null_count,
            "null_pct": null_pct,
            "dtype": dtype,
        }

        if null_pct > threshold:                    #If the null count is greater than threshold then flag it 
            flagged_columns.append(col)
            logger.warning(
                "Column '%s' has %.2f%% missing values "
                "(threshold: %.2f%%).", col, null_pct, threshold
            )

    report: Dict[str, Any] = {                  #Generating the report to show how many columns are flagged
        "total_rows": total_rows,
        "columns": column_stats,
        "flagged_columns": flagged_columns,
    }

    logger.info(
        "Missing value report generated. %d/%d columns flagged.",
        len(flagged_columns),
        len(df.columns)
    )

    return report
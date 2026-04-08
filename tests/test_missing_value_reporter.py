"""Unit tests for the missing value reporter utility."""

import pandas as pd
import pytest
from kedro.missing_value_reporter import generate_missing_value_report


class TestMissingValueReporter:
    def test_no_missing_values(self):                               #Test 1 -  clean data nothing missing
        df = pd.DataFrame({
            "Name": ["Alice", "Bob", "Carol"],
            "Age": [25, 30, 35],
            "Salary": [50000, 60000, 70000]
        })
        report = generate_missing_value_report(df, threshold=20.0)          #Report generated

        assert report["total_rows"] == 3                #Checks if total rows are three then passes true else false
        assert report["flagged_columns"] == []          #no columns flagged all clean
        for col in ["Name", "Age", "Salary"]:
            assert report["columns"][col]["null_count"] == 0        #No missing values
            assert report["columns"][col]["null_pct"] == 0.0        #0.0 percent missing values

    def test_partial_missing_values(self):                          #Test 2 -  Few missing values   
        df = pd.DataFrame({
            "Name": ["Alice", None, "Carol", None],
            "Age": [25, 30, 35, 40],
        })
        report = generate_missing_value_report(df, threshold=40.0)      #threshold as 40 so flag and report the columns that are more than 40% empty
         #Check the results
        assert report["total_rows"] == 4                               
        assert report["columns"]["Name"]["null_count"] == 2
        assert report["columns"]["Name"]["null_pct"] == 50.0
        assert report["columns"]["Age"]["null_count"] == 0

    def test_all_missing_values(self):                                  #An entire column is completely empty
        df = pd.DataFrame({                                             #Create a table where score column is all blank 
            "Name": ["Alice", "Bob", "Carol"],                          
            "Score": [None, None, None]
        })
        report = generate_missing_value_report(df, threshold=20.0)        #Geneate the report

        assert report["columns"]["Score"]["null_count"] == 3              #Check the score has 3 missing values
        assert report["columns"]["Score"]["null_pct"] == 100.0            #Check the score is 100% missing
        assert "Score" in report["flagged_columns"]                       #Score appears in the flagged list

    def test_threshold_flagging(self):                                    #Check when one column is empty and one is fine
        df = pd.DataFrame({
            "A": [1, None, None, None, None],  # 80% missing
            "B": [1, 2, 3, 4, 5],              # 0% missing
        })
        report = generate_missing_value_report(df, threshold=20.0)

        assert "A" in report["flagged_columns"]
        assert "B" not in report["flagged_columns"]

    def test_empty_dataframe(self):                                           #Test the complete empty table with no rows and no columns
        df = pd.DataFrame()
        report = generate_missing_value_report(df, threshold=20.0)

        assert report["total_rows"] == 0
        assert report["columns"] == {}
        assert report["flagged_columns"] == []

    def test_report_structure(self):                                            #Test the report if it has all the required keys
        df = pd.DataFrame({
            "X": [1, 2, None],
            "Y": [None, 2, 3]
        })
        report = generate_missing_value_report(df, threshold=20.0)

        assert "total_rows" in report
        assert "columns" in report
        assert "flagged_columns" in report
        for col in ["X", "Y"]:
            assert "null_count" in report["columns"][col]
            assert "null_pct" in report["columns"][col]
            assert "dtype" in report["columns"][col]
"""
Regional Inventory Data Analysis
================================

A self-contained Pandas script that walks through five core tasks:
    1. Data Construction   - build inventory_df with missing values (np.nan)
    2. Data Exploration    - .info() and .dtypes
    3. Statistical Analysis- median of Unit_Cost, total Stock_Qty via .sum()
    4. Data Subsetting     - rows where Stock_Qty > 50
    5. Data Manipulation   - Inventory_Value column + .fillna(0)
"""

import numpy as np
import pandas as pd


def build_inventory() -> pd.DataFrame:
    """Task 1: Data Construction.

    Create a DataFrame with the required columns, intentionally seeding
    some cells with np.nan to exercise the missing-value handling later.
    """
    data = {
        "ProductID": [101, 102, 103, 104, 105, 106, 107, 108],
        "Department": [
            "Electronics",
            "Grocery",
            "Apparel",
            "Electronics",
            np.nan,          # missing department
            "Grocery",
            "Apparel",
            "Home",
        ],
        "Unit_Cost": [250.0, 15.5, np.nan, 99.9, 12.0, np.nan, 45.0, 8.75],
        "Stock_Qty": [30, np.nan, 120, 45, 200, 60, np.nan, 75],
    }
    return pd.DataFrame(data)


def explore(df: pd.DataFrame) -> None:
    """Task 2: Data Exploration via .info() and .dtypes."""
    print("=" * 60)
    print("TASK 2: DATA EXPLORATION")
    print("=" * 60)

    print("\n--- DataFrame.info() ---")
    df.info()

    print("\n--- Column data types (.dtypes) ---")
    print(df.dtypes)


def analyze(df: pd.DataFrame) -> None:
    """Task 3: Statistical Analysis."""
    print("\n" + "=" * 60)
    print("TASK 3: STATISTICAL ANALYSIS")
    print("=" * 60)

    # .median() skips NaN by default
    median_cost = df["Unit_Cost"].median()
    # .sum() skips NaN by default
    total_stock = df["Stock_Qty"].sum()

    print(f"\nMedian of Unit_Cost : {median_cost}")
    print(f"Total items in stock (sum of Stock_Qty): {total_stock}")


def subset(df: pd.DataFrame) -> pd.DataFrame:
    """Task 4: Data Subsetting - rows where Stock_Qty > 50."""
    print("\n" + "=" * 60)
    print("TASK 4: DATA SUBSETTING (Stock_Qty > 50)")
    print("=" * 60)

    # NaN comparisons evaluate to False, so those rows are excluded.
    high_stock = df[df["Stock_Qty"] > 50]
    print(f"\nRows with Stock_Qty > 50 ({len(high_stock)} found):")
    print(high_stock)
    return high_stock


def manipulate(df: pd.DataFrame) -> pd.DataFrame:
    """Task 5: Data Manipulation.

    Add Inventory_Value (Unit_Cost * Stock_Qty) and replace remaining
    missing values with 0 via .fillna(0).
    """
    print("\n" + "=" * 60)
    print("TASK 5: DATA MANIPULATION")
    print("=" * 60)

    df = df.copy()
    df["Inventory_Value"] = df["Unit_Cost"] * df["Stock_Qty"]

    # Fill every remaining NaN across numeric columns with 0.
    df_filled = df.fillna(0)

    print("\nDataFrame with Inventory_Value and NaNs filled with 0:")
    print(df_filled)
    return df_filled


def main() -> None:
    # Wider display so nothing gets truncated in the console.
    pd.set_option("display.width", 120)
    pd.set_option("display.max_columns", None)

    # Task 1
    inventory_df = build_inventory()
    print("=" * 60)
    print("TASK 1: DATA CONSTRUCTION")
    print("=" * 60)
    print("\nOriginal inventory_df (with np.nan values):")
    print(inventory_df)

    # Tasks 2-5
    explore(inventory_df)
    analyze(inventory_df)
    subset(inventory_df)
    manipulate(inventory_df)


if __name__ == "__main__":
    main()

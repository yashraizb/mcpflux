"""Tests for DataContext-based multi-sheet / multi-file pipeline."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from spreadsheet_mcp_agent.loaders import (
    CsvLoaderStrategy,
    DataContext,
    ExcelLoaderStrategy,
    FileLoaderContext,
)
from spreadsheet_mcp_agent.schema_extractor import extract_schema
from spreadsheet_mcp_agent.sql_executor import execute_sql, validate_sql


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_csv(tmp_path: Path, name: str, data: dict) -> Path:
    """Write a CSV file and return its path."""
    p = tmp_path / name
    pd.DataFrame(data).to_csv(p, index=False)
    return p


def _make_excel(tmp_path: Path, name: str, sheets: dict[str, dict]) -> Path:
    """Write an Excel file with one or more sheets and return its path."""
    p = tmp_path / name
    with pd.ExcelWriter(p, engine="openpyxl") as writer:
        for sheet_name, data in sheets.items():
            pd.DataFrame(data).to_excel(writer, sheet_name=sheet_name, index=False)
    return p


# ---------------------------------------------------------------------------
# CsvLoaderStrategy
# ---------------------------------------------------------------------------

class TestCsvLoaderStrategy:
    def test_returns_data_context_keyed_by_stem(self, tmp_path):
        p = _make_csv(tmp_path, "sales.csv", {"a": [1, 2], "b": [3, 4]})
        ctx = CsvLoaderStrategy().load(str(p))
        assert isinstance(ctx, dict)
        assert list(ctx.keys()) == ["sales"]
        assert list(ctx["sales"].columns) == ["a", "b"]
        assert len(ctx["sales"]) == 2

    def test_can_handle_csv(self):
        s = CsvLoaderStrategy()
        assert s.can_handle(".csv")
        assert not s.can_handle(".xlsx")


# ---------------------------------------------------------------------------
# ExcelLoaderStrategy
# ---------------------------------------------------------------------------

class TestExcelLoaderStrategy:
    def test_single_sheet_uses_stem_as_key(self, tmp_path):
        p = _make_excel(tmp_path, "report.xlsx", {"Sheet1": {"x": [10, 20]}})
        ctx = ExcelLoaderStrategy().load(str(p))
        assert list(ctx.keys()) == ["report"]
        assert list(ctx["report"].columns) == ["x"]

    def test_multi_sheet_uses_stem_double_underscore_sheet_name(self, tmp_path):
        p = _make_excel(
            tmp_path,
            "workbook.xlsx",
            {"Sales": {"amount": [100]}, "Returns": {"amount": [5]}},
        )
        ctx = ExcelLoaderStrategy().load(str(p))
        assert set(ctx.keys()) == {"workbook__Sales", "workbook__Returns"}
        assert ctx["workbook__Sales"]["amount"].iloc[0] == 100
        assert ctx["workbook__Returns"]["amount"].iloc[0] == 5

    def test_can_handle_xlsx_and_xls(self):
        s = ExcelLoaderStrategy()
        assert s.can_handle(".xlsx")
        assert s.can_handle(".xls")
        assert not s.can_handle(".csv")


# ---------------------------------------------------------------------------
# FileLoaderContext
# ---------------------------------------------------------------------------

class TestFileLoaderContext:
    def test_load_single_csv(self, tmp_path):
        p = _make_csv(tmp_path, "employees.csv", {"name": ["Alice"], "age": [30]})
        ctx = FileLoaderContext().load(str(p))
        assert "employees" in ctx
        assert ctx["employees"]["name"].iloc[0] == "Alice"

    def test_load_single_excel(self, tmp_path):
        p = _make_excel(tmp_path, "data.xlsx", {"Info": {"val": [99]}})
        ctx = FileLoaderContext().load(str(p))
        assert "data" in ctx

    def test_load_comma_separated_files_merges_contexts(self, tmp_path):
        p1 = _make_csv(tmp_path, "orders.csv", {"id": [1, 2], "total": [50, 80]})
        p2 = _make_csv(tmp_path, "customers.csv", {"id": [1, 2], "name": ["Alice", "Bob"]})
        ctx = FileLoaderContext().load(f"{p1},{p2}")
        assert "orders" in ctx
        assert "customers" in ctx
        assert len(ctx) == 2

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            FileLoaderContext().load(str(tmp_path / "missing.csv"))

    def test_unsupported_format_raises(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported file format"):
            FileLoaderContext().load(str(p))


# ---------------------------------------------------------------------------
# extract_schema
# ---------------------------------------------------------------------------

class TestExtractSchema:
    def test_single_table_schema_contains_table_name(self):
        ctx: DataContext = {"sales": pd.DataFrame({"revenue": [100, 200]})}
        schema = extract_schema(ctx)
        assert "Table: sales" in schema
        assert "revenue" in schema

    def test_multi_table_schema_contains_all_table_names(self):
        ctx: DataContext = {
            "orders": pd.DataFrame({"id": [1], "amount": [50]}),
            "customers": pd.DataFrame({"id": [1], "name": ["Alice"]}),
        }
        schema = extract_schema(ctx)
        assert "Table: orders" in schema
        assert "Table: customers" in schema
        assert "---" in schema  # separator between tables

    def test_schema_includes_row_count(self):
        ctx: DataContext = {"t": pd.DataFrame({"v": range(7)})}
        schema = extract_schema(ctx)
        assert "Row count: 7" in schema


# ---------------------------------------------------------------------------
# execute_sql
# ---------------------------------------------------------------------------

class TestExecuteSql:
    def test_single_table_query(self):
        ctx: DataContext = {"products": pd.DataFrame({"name": ["A", "B"], "price": [10, 20]})}
        result = execute_sql(ctx, "SELECT * FROM products WHERE price > 15")
        assert len(result) == 1
        assert result["name"].iloc[0] == "B"

    def test_cross_table_join(self):
        ctx: DataContext = {
            "orders": pd.DataFrame({"order_id": [1, 2], "customer_id": [10, 20], "amount": [100, 200]}),
            "customers": pd.DataFrame({"customer_id": [10, 20], "name": ["Alice", "Bob"]}),
        }
        result = execute_sql(
            ctx,
            "SELECT c.name, o.amount FROM orders o JOIN customers c ON o.customer_id = c.customer_id",
        )
        assert len(result) == 2
        names = set(result["name"].tolist())
        assert names == {"Alice", "Bob"}

    def test_aggregate_query(self):
        ctx: DataContext = {"sales": pd.DataFrame({"region": ["A", "A", "B"], "revenue": [10, 20, 30]})}
        result = execute_sql(ctx, "SELECT region, SUM(revenue) AS total FROM sales GROUP BY region ORDER BY region")
        assert len(result) == 2
        assert result.loc[result["region"] == "A", "total"].iloc[0] == 30

    def test_invalid_sql_raises(self):
        ctx: DataContext = {"t": pd.DataFrame({"v": [1]})}
        with pytest.raises(Exception, match="SQL execution failed"):
            execute_sql(ctx, "NOT VALID SQL !!!!")


# ---------------------------------------------------------------------------
# validate_sql
# ---------------------------------------------------------------------------

class TestValidateSql:
    def test_valid_sql_returns_true(self):
        ctx: DataContext = {"t": pd.DataFrame({"v": [1, 2, 3]})}
        assert validate_sql(ctx, "SELECT * FROM t") is True

    def test_invalid_sql_raises(self):
        ctx: DataContext = {"t": pd.DataFrame({"v": [1]})}
        with pytest.raises(Exception):
            validate_sql(ctx, "SELECT * FROM nonexistent_table_xyz")


# ---------------------------------------------------------------------------
# Multi-sheet Excel end-to-end
# ---------------------------------------------------------------------------

class TestMultiSheetExcelEndToEnd:
    def test_multi_sheet_join_query(self, tmp_path):
        p = _make_excel(
            tmp_path,
            "store.xlsx",
            {
                "Products": {"id": [1, 2, 3], "name": ["Widget", "Gadget", "Doohickey"], "price": [10, 25, 5]},
                "Orders": {"product_id": [1, 1, 2], "qty": [2, 1, 3]},
            },
        )
        ctx = FileLoaderContext().load(str(p))
        assert "store__Products" in ctx
        assert "store__Orders" in ctx

        result = execute_sql(
            ctx,
            "SELECT p.name, SUM(o.qty) AS total_qty "
            "FROM store__Orders o JOIN store__Products p ON o.product_id = p.id "
            "GROUP BY p.name ORDER BY p.name",
        )
        assert len(result) == 2
        row = result.loc[result["name"] == "Widget"]
        assert row["total_qty"].iloc[0] == 3

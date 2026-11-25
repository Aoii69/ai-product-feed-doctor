"""Read, validate, and export a product feed without changing its values."""
import csv
from collections import Counter
from decimal import Decimal
from io import StringIO
import re

import pandas as pd

REQUIRED_COLUMNS = ("sku", "name", "price", "stock")
MISSING_EXTRA_VALUE = "Missing value"
ISSUE_TYPES = ("Missing SKU", "Duplicate SKU", "Missing product name", "Invalid price", "Invalid stock quantity", MISSING_EXTRA_VALUE)
PRICE = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")
STOCK = re.compile(r"[+]?[0-9]+")


def read_feed(data: bytes) -> pd.DataFrame:
    """Read UTF-8 CSV fields as text, preserving leading zeros and blanks."""
    reader = csv.reader(StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
    headers = next(reader, [])
    if not headers or any(not name.strip() for name in headers):
        raise ValueError("The CSV must have a header with a name for every column.")
    if len(set(headers)) != len(headers):
        raise ValueError("CSV column names must be unique.")
    missing = [name for name in REQUIRED_COLUMNS if name not in headers]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}.")

    records = []
    for row_number, record in enumerate(reader, start=2):
        if len(record) != len(headers):
            raise ValueError(f"CSV row {row_number} must have {len(headers)} fields.")
        records.append(record)
    return pd.DataFrame(records, columns=headers, dtype=str)


def validate_feed(feed: pd.DataFrame, required_extra_columns: list[str] | None = None) -> pd.DataFrame:
    """Return issues in CSV row order. By default, require every extra column."""
    sku_counts = Counter(value.strip() for value in feed["sku"] if value.strip())
    issues = []
    extra_columns = [
        column for column in feed.columns
        if column not in REQUIRED_COLUMNS
        and (required_extra_columns is None or column in required_extra_columns)
    ]
    fields = feed.loc[:, [*REQUIRED_COLUMNS, *extra_columns]]
    for row, values in enumerate(fields.itertuples(index=False, name=None), start=2):
        sku, name, price, stock = (value.strip() for value in values[:4])
        if not sku:
            issues.append((row, "sku", "Missing SKU", "Enter the SKU from your product records."))
        elif sku_counts[sku] > 1:
            issues.append((row, "sku", "Duplicate SKU", f"SKU {sku!r} appears on {sku_counts[sku]} rows. Verify each product's SKU."))
        if not name:
            issues.append((row, "name", "Missing product name", "Enter the product name from your catalog."))
        if not PRICE.fullmatch(price) or Decimal(price) <= 0:
            issues.append((row, "price", "Invalid price", "Enter a number greater than zero with a decimal point if needed, such as 19.95."))
        if not STOCK.fullmatch(stock):
            issues.append((row, "stock", "Invalid stock quantity", "Enter a whole number of zero or more. Check your inventory records."))
        for column, value in zip(extra_columns, values[4:]):
            if not value.strip():
                issues.append((row, column, MISSING_EXTRA_VALUE, f"Enter the verified value for {column!r} from your product records."))
    return pd.DataFrame(issues, columns=["CSV row", "Column", "Issue", "Explanation"])


def export_feed(feed: pd.DataFrame) -> bytes:
    """Export the reviewed values and original columns as UTF-8 CSV."""
    return feed.to_csv(index=False, lineterminator="\r\n").encode("utf-8-sig")

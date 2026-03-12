"""Generate example datasets for testing."""

import pandas as pd
from pathlib import Path


def create_sales_data() -> None:
    """Create a sample sales dataset."""
    data = {
        "product": [
            "Widget A",
            "Widget B",
            "Widget A",
            "Widget C",
            "Widget B",
            "Widget A",
            "Widget C",
            "Widget B",
            "Widget A",
            "Widget D",
        ],
        "country": [
            "USA",
            "USA",
            "UK",
            "Canada",
            "UK",
            "Canada",
            "USA",
            "Germany",
            "France",
            "USA",
        ],
        "revenue": [5000, 3000, 4000, 2000, 3500, 4500, 6000, 2500, 3200, 5500],
        "units_sold": [50, 30, 40, 20, 35, 45, 60, 25, 32, 55],
        "date": [
            "2024-01-01",
            "2024-01-01",
            "2024-01-02",
            "2024-01-02",
            "2024-01-03",
            "2024-01-03",
            "2024-01-04",
            "2024-01-04",
            "2024-01-05",
            "2024-01-05",
        ],
    }

    df = pd.DataFrame(data)
    output_file = Path(__file__).parent / "sales_data.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Created sample data: {output_file}")


def create_customer_data() -> None:
    """Create a sample customer dataset."""
    data = {
        "customer_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "customer_name": [
            "Acme Corp",
            "TechStart Inc",
            "Global Solutions",
            "DataFlow Ltd",
            "CloudBase Co",
            "AI Systems",
            "Digital Pro",
            "Tech Hub",
            "Smart Solutions",
            "Future Tech",
        ],
        "country": [
            "USA",
            "UK",
            "Canada",
            "USA",
            "Germany",
            "France",
            "USA",
            "UK",
            "Canada",
            "USA",
        ],
        "revenue": [25000, 18000, 15000, 12000, 10000, 9000, 8500, 7500, 6000, 5500],
        "orders": [50, 35, 28, 24, 20, 18, 17, 15, 12, 11],
    }

    df = pd.DataFrame(data)
    output_file = Path(__file__).parent / "customer_data.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Created sample data: {output_file}")


if __name__ == "__main__":
    print("Generating example datasets...\n")
    create_sales_data()
    create_customer_data()
    print("\nExample datasets created successfully!")
    print("You can now test the MCP server with these files.")

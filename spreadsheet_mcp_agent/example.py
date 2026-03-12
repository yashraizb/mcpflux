"""Example usage of the spreadsheet MCP agent."""

import os
import pandas as pd
from pathlib import Path

# Create sample data if it doesn't exist
def create_sample_csv() -> str:
    """Create a sample CSV file for testing.

    Returns:
        Path to the created CSV file.
    """
    data = {
        "product": [
            "Widget A",
            "Widget B",
            "Widget A",
            "Widget C",
            "Widget B",
            "Widget A",
        ],
        "country": ["USA", "USA", "UK", "Canada", "UK", "Canada"],
        "revenue": [5000, 3000, 4000, 2000, 3500, 4500],
        "date": [
            "2024-01-01",
            "2024-01-01",
            "2024-01-02",
            "2024-01-02",
            "2024-01-03",
            "2024-01-03",
        ],
    }

    df = pd.DataFrame(data)
    csv_path = "sample_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"Created sample CSV: {csv_path}")
    return csv_path


def main() -> None:
    """Run example queries."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Create sample data
    csv_path = create_sample_csv()

    # Import and use the server
    from spreadsheet_mcp_agent import query_spreadsheet
    import json

    # Example queries
    example_queries = [
        "Which country has the highest revenue?",
        "Total sales per product",
        "Top 3 products by revenue",
    ]

    print("\nRunning example queries:\n")

    for question in example_queries:
        print(f"Question: {question}")
        result = query_spreadsheet(csv_path, question)
        result_dict = json.loads(result)

        if result_dict.get("success"):
            print(f"SQL: {result_dict['generated_sql']}")
            print(f"Results: {json.dumps(result_dict['result_preview'], indent=2)}")
        else:
            print(f"Error: {result_dict.get('error')}")

        print()


if __name__ == "__main__":
    main()

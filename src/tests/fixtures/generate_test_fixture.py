# Generate test fixture Excel file
import pandas as pd
from pathlib import Path

# Create sample data
data = {
    "Provider Name": ["Phoenix Health Center", "Tempe Medical Group", "Scottsdale Clinic"],
    "Provider Address": ["100 N Central Ave", "200 E University Dr", "300 N Scottsdale Rd"],
    "Provider City": ["Phoenix", "Tempe", "Scottsdale"],
    "Provider State": ["AZ", "AZ", "AZ"],
    "Provider Zip": ["85004", "85281", "85251"],
    "License Number": ["AZ-001", "AZ-002", "AZ-003"],
    "License Type": ["Hospital", "Clinic", "Clinic"],
    "License Date": ["2023-01-15", "2023-03-20", "2023-06-10"],
    "Capacity": [250, 50, 75],
}

# Create Excel file
fixture_path = Path(__file__).parent / "sample_adhs_2025-05.xlsx"
df = pd.DataFrame(data)
with pd.ExcelWriter(fixture_path, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Providers", index=False)

print(f"Created test fixture: {fixture_path}")
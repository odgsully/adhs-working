"""
Demo script showing BatchData pipeline capabilities
"""

import os
import sys
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def demo_transformation():
    """Demonstrate eCorp to BatchData transformation."""
    print("🔄 eCorp to BatchData Transformation Demo")
    print("-" * 50)
    
    from src.transform import transform_ecorp_to_batchdata
    
    # Load sample eCorp data
    ecorp_df = pd.read_excel("../M.YY_Ecorp_Complete.xlsx").head(2)
    print(f"📊 Loaded {len(ecorp_df)} eCorp records")
    
    print("\n📋 Sample eCorp Record:")
    sample = ecorp_df.iloc[0]
    for col in ['ECORP_NAME_S', 'ECORP_ENTITY_ID_S', 'Title1', 'Name1', 'Address1']:
        print(f"  {col}: {sample.get(col, 'N/A')}")
    
    # Transform
    batchdata_df = transform_ecorp_to_batchdata(ecorp_df)
    print(f"\n✨ Transformed to {len(batchdata_df)} BatchData records")
    
    print("\n📋 Sample BatchData Records:")
    for i, (_, row) in enumerate(batchdata_df.head(3).iterrows()):
        print(f"  Record {i+1}:")
        print(f"    ID: {row['BD_RECORD_ID']}")
        print(f"    Entity: {row['BD_ENTITY_NAME']}")
        print(f"    Name: {row['BD_TARGET_FIRST_NAME']} {row['BD_TARGET_LAST_NAME']}")
        print(f"    Role: {row['BD_TITLE_ROLE']}")
        print(f"    Location: {row['BD_CITY']}, {row['BD_STATE']}")
    
    return batchdata_df


def demo_data_quality():
    """Show data quality and normalization features."""
    print("\n🧹 Data Quality & Normalization Demo")
    print("-" * 50)
    
    from src.normalize import split_full_name, normalize_state, normalize_phone_e164
    
    # Name splitting demo
    test_names = ["John Doe Jr.", "Mary Jane Smith", "Bob", "Alice Van Der Berg III"]
    print("👤 Name Splitting:")
    for name in test_names:
        first, last = split_full_name(name)
        print(f"  '{name}' → First: '{first}', Last: '{last}'")
    
    # State normalization demo
    test_states = ["Arizona", "AZ", "CALIFORNIA", "NY"]
    print("\n🗺️  State Normalization:")
    for state in test_states:
        normalized = normalize_state(state)
        print(f"  '{state}' → '{normalized}'")
    
    # Phone normalization demo
    test_phones = ["(480) 555-1234", "602.555.5678", "1-520-555-9999", "invalid"]
    print("\n📞 Phone Normalization (E.164):")
    for phone in test_phones:
        normalized = normalize_phone_e164(phone)
        result = normalized if normalized else "❌ Invalid"
        print(f"  '{phone}' → '{result}'")


def demo_cost_estimation():
    """Demonstrate cost estimation."""
    print("\n💰 Cost Estimation Demo")  
    print("-" * 50)
    
    from src.batchdata import BatchDataClient
    
    # Mock client for demo
    client = BatchDataClient({'BD_SKIPTRACE_KEY': 'demo'})
    
    # Different scenarios
    scenarios = [
        {"name": "Small Test (10 records)", "records": 10, "config": {"workflow.enable_phone_verification": True}},
        {"name": "Medium Batch (100 records)", "records": 100, "config": {"workflow.enable_phone_verification": True, "workflow.enable_phone_dnc": True}},
        {"name": "Large Batch (1000 records)", "records": 1000, "config": {"workflow.enable_phone_verification": True, "workflow.enable_phone_dnc": True, "workflow.enable_phone_tcpa": True}}
    ]
    
    for scenario in scenarios:
        costs = client.estimate_cost(scenario["records"], scenario["config"])
        print(f"\n📊 {scenario['name']}:")
        print(f"  Skip-trace: ${costs['skip_trace']:.2f}")
        if "phone_verification" in costs:
            print(f"  Phone verification: ${costs['phone_verification']:.2f}")
        if "phone_dnc" in costs:
            print(f"  DNC checking: ${costs['phone_dnc']:.2f}")
        if "phone_tcpa" in costs:
            print(f"  TCPA checking: ${costs['phone_tcpa']:.2f}")
        print(f"  💵 Total: ${costs['total']:.2f}")


def demo_configuration():
    """Show configuration options."""
    print("\n⚙️  Configuration Demo")
    print("-" * 50)
    
    from src.io import load_workbook_sheets, load_config_dict
    
    # Load config from template
    sheets = load_workbook_sheets("../batchdata_local_pack/template_batchdata_upload.xlsx")
    config = load_config_dict(sheets['CONFIG'])
    
    print("📋 Available Configuration Options:")
    for key, value in config.items():
        if key.startswith('workflow.'):
            print(f"  🔧 {key}: {value}")
    
    print(f"\n⚡ Batch Settings:")
    for key, value in config.items():
        if key.startswith('batch.'):
            print(f"  📦 {key}: {value}")


def main():
    """Run the full demo."""
    print("🚀 BatchData Pipeline Demo")
    print("=" * 50)
    print("This demo shows the key features of the BatchData pipeline")
    print("without making actual API calls.\n")
    
    # Run demos
    try:
        batchdata_df = demo_transformation()
        demo_data_quality()
        demo_cost_estimation() 
        demo_configuration()
        
        print("\n🎯 Next Steps:")
        print("1. Configure your API keys in .env")
        print("2. Run: python -m src.run --input batchdata_local_input.xlsx --dry-run")
        print("3. For production: python -m src.run --input your_input.xlsx")
        
        print("\n📁 Generated Files:")
        print("- batchdata_local_input.xlsx (test input)")
        print("- results/ directory (output location)")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")


if __name__ == "__main__":
    main()
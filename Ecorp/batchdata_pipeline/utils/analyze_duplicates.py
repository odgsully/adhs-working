"""
Analyze the potential duplicates in BatchData records more carefully
"""

import os
import sys
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_duplicates():
    """Analyze duplicate patterns in the BatchData records."""
    print("🔍 Analyzing Duplicate Patterns")
    print("-" * 50)
    
    # Load the data
    csv_file = 'results/filtered_input_20250818_132817_20250818_132817.csv'
    df = pd.read_csv(csv_file)
    
    print(f"Total records: {len(df)}")
    
    # Check duplicates by different field combinations
    duplicate_analyses = [
        ('name_only', ['target_first_name', 'target_last_name']),
        ('name_address', ['target_first_name', 'target_last_name', 'address_line1']),
        ('name_entity', ['target_first_name', 'target_last_name', 'source_entity_name']),
        ('full_comparison', ['target_first_name', 'target_last_name', 'owner_name_full', 'address_line1', 'city', 'state', 'zip', 'source_entity_name', 'title_role'])
    ]
    
    for analysis_name, fields in duplicate_analyses:
        print(f"\n📊 {analysis_name.replace('_', ' ').title()} Analysis:")
        
        # Create comparison key with null handling
        df_temp = df.copy()
        for field in fields:
            if field in df_temp.columns:
                df_temp[field] = df_temp[field].fillna('').astype(str).str.strip().str.upper()
        
        # Group by comparison fields
        if all(field in df_temp.columns for field in fields):
            grouped = df_temp.groupby(fields).size()
            duplicates = grouped[grouped > 1]
            
            print(f"   Duplicate groups: {len(duplicates)}")
            print(f"   Total duplicate records: {duplicates.sum() - len(duplicates)}")
            
            if len(duplicates) > 0:
                print("   Top duplicate groups:")
                for i, (group_key, count) in enumerate(duplicates.head(5).items()):
                    if isinstance(group_key, tuple):
                        key_str = ' | '.join(str(k)[:30] for k in group_key)
                    else:
                        key_str = str(group_key)[:50]
                    print(f"     {key_str}: {count} records")
    
    # Show specific examples of potential duplicates
    print(f"\n🔍 Detailed Duplicate Analysis:")
    
    # Find records with same name but different record_ids
    name_groups = df.groupby(['target_first_name', 'target_last_name'])
    
    for (first, last), group in name_groups:
        if len(group) > 1 and first and last and str(first) != 'nan' and str(last) != 'nan':
            print(f"\n👤 {first} {last} ({len(group)} records):")
            for _, record in group.iterrows():
                entity = record['source_entity_name'][:30] if record['source_entity_name'] else 'N/A'
                address = record['address_line1'][:30] if record['address_line1'] else 'N/A'
                print(f"   {record['record_id']}: {entity} | {address}")
            
            # Check if these would be considered duplicates
            if len(group) > 1:
                # Test our deduplication logic
                from src.transform import deduplicate_batchdata_records
                test_group = group.copy()
                deduplicated = deduplicate_batchdata_records(test_group)
                reduction = len(test_group) - len(deduplicated)
                if reduction > 0:
                    print(f"   ✅ Would remove {reduction} duplicates")
                else:
                    print(f"   ❌ No duplicates detected by algorithm")
            
            if len(name_groups) > 5:  # Limit output
                break


def main():
    """Run duplicate analysis."""
    print("🕵️ BatchData Duplicate Analysis")
    print("=" * 50)
    
    try:
        analyze_duplicates()
    except Exception as e:
        print(f"❌ Analysis failed: {e}")


if __name__ == "__main__":
    main()
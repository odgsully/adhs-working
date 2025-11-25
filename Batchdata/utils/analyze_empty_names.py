"""
Analyze records with empty individual names to assess API processing value
"""

import pandas as pd

def analyze_empty_name_records():
    """Analyze records with no individual names."""
    
    df = pd.read_csv('results/filtered_input_20250818_135812_dedupe_families_20250818_135812.csv')
    
    print('🔍 Analyzing Records with No Individual Names')
    print('=' * 60)
    
    # Check for records with empty individual names
    empty_name_records = df[(df['BD_TARGET_FIRST_NAME'].isna() | (df['BD_TARGET_FIRST_NAME'] == '')) &
                           (df['BD_TARGET_LAST_NAME'].isna() | (df['BD_TARGET_LAST_NAME'] == ''))]

    print(f'Records with empty first AND last names: {len(empty_name_records)}')
    print()

    for i, (idx, row) in enumerate(empty_name_records.iterrows(), 1):
        entity = str(row['BD_ENTITY_NAME'])[:50]
        owner = str(row['BD_OWNER_NAME_FULL'])[:40]
        role = str(row['BD_TITLE_ROLE'])
        address = str(row['BD_ADDRESS'])[:30]
        
        print(f'{i}. Row {idx+1}: Entity: {entity}')
        print(f'   Owner: {owner} | Role: {role}')
        print(f'   Address: {address}')
        
        # Assess API value
        has_useful_owner = owner != 'nan' and len(owner) > 5 and ('LLC' in owner.upper() or 'CORP' in owner.upper())
        has_address = address != 'nan' and len(address) > 10
        
        if has_useful_owner and has_address:
            api_value = 'MEDIUM - Entity with address'
        elif has_address:
            api_value = 'LOW - Address only'  
        else:
            api_value = 'NONE - No useful data'
            
        print(f'   API Value: {api_value}')
        print()
    
    print('💡 API Processing Analysis:')
    print('For BatchData skip-trace APIs, records typically need:')
    print('1. Person name (first + last) + address = HIGH value')
    print('2. Entity name + address = MEDIUM value (some APIs support)')
    print('3. Address only = LOW value (property-based lookup)')
    print('4. Neither = NO value (cannot process)')
    
    useful_count = len(empty_name_records[empty_name_records['BD_ADDRESS'].notna() &
                                         (empty_name_records['BD_ADDRESS'] != '')])

    print(f'\nOf {len(empty_name_records)} entity-only records, {useful_count} have addresses')
    print(f'Potential savings by filtering these: ${len(empty_name_records) * 0.07:.2f}')

    # Show what these records actually are
    print('\n📋 What these records represent:')
    for role in empty_name_records['BD_TITLE_ROLE'].value_counts().head(5).items():
        print(f'  {role[0]}: {role[1]} records')
    
    return empty_name_records

if __name__ == "__main__":
    analyze_empty_name_records()
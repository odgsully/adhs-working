import pandas as pd

# Load the 10.24 Analysis file
df = pd.read_excel('Analysis/10.24 Analysis.xlsx', sheet_name='Analysis')

print('=== CHECKING ALL FIXES ===')
print()

# 1. Check LEAD_TYPE has no blanks
blanks = df[df['LEAD_TYPE'].isna() | (df['LEAD_TYPE'] == '')].shape[0]
total = len(df)
print(f'1. LEAD_TYPE blanks: {blanks}/{total}')

# Check specific mapping
existing_both = df[df['THIS_MONTH_STATUS'] == 'EXISTING PROVIDER TYPE, EXISTING ADDRESS']
if not existing_both.empty:
    lead_types = existing_both['LEAD_TYPE'].value_counts()
    print(f'   EXISTING PROVIDER TYPE, EXISTING ADDRESS maps to: {lead_types.to_dict()}')

# 2. Check CAPACITY formatting
print()
non_empty_cap = df[df['CAPACITY'] != '']
sample_values = non_empty_cap['CAPACITY'].head(20).tolist()
print(f'2. CAPACITY sample values: {sample_values[:10]}')

# Check for decimals
has_decimal = non_empty_cap[non_empty_cap['CAPACITY'].astype(str).str.contains('\.', na=False)]
print(f'   Values with decimals: {has_decimal.shape[0]}')

# 3. Check PROVIDER_TYPES_GAINED
print()
non_empty_gained = df[df['PROVIDER_TYPES_GAINED'] != '']
print(f'3. PROVIDER_TYPES_GAINED populated: {non_empty_gained.shape[0]} records')
if not non_empty_gained.empty:
    samples = non_empty_gained[['PROVIDER', 'PROVIDER_TYPES_GAINED']].head(3)
    for _, row in samples.iterrows():
        print(f'   {row["PROVIDER"]}: {row["PROVIDER_TYPES_GAINED"]}')

# 4. Check PROVIDER_TYPES_LOST
print()
non_empty_lost = df[df['PROVIDER_TYPES_LOST'] != '']
print(f'4. PROVIDER_TYPES_LOST populated: {non_empty_lost.shape[0]} records')
if not non_empty_lost.empty:
    samples = non_empty_lost[['PROVIDER', 'PROVIDER_TYPES_LOST']].head(3)
    for _, row in samples.iterrows():
        print(f'   {row["PROVIDER"]}: {row["PROVIDER_TYPES_LOST"]}')

# 5. Check column names
print()
columns_with_spaces = [col for col in df.columns if ' ' in col]
if columns_with_spaces:
    print(f'5. ❌ Columns with spaces found: {columns_with_spaces[:3]}')
else:
    print(f'5. ✅ All column names use underscores')

# 6. Check SUMMARY columns
print()
summary_col = '10.24_SUMMARY'
if summary_col in df.columns:
    non_empty_summary = df[df[summary_col] != '']
    print(f'6. {summary_col} populated: {non_empty_summary.shape[0]} records')
    if not non_empty_summary.empty:
        sample = non_empty_summary[['PROVIDER_GROUP,_ADDRESS_COUNT', 'PROVIDER_GROUP_(DBA_CONCAT)', summary_col]].head(2)
        for _, row in sample.iterrows():
            print(f'   N={row["PROVIDER_GROUP,_ADDRESS_COUNT"]}, M={row["PROVIDER_GROUP_(DBA_CONCAT)"][:30]}...')
            print(f'   SUMMARY={row[summary_col][:60]}...')
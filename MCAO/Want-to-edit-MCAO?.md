# Want to Edit MCAO Column Structure?

## ⚠️ CRITICAL WARNING: Don't Move Existing Columns!

The MCAO column structure is **position-dependent**. Moving columns will break downstream processing, specifically:

- **Ecorp Pipeline** expects:
  - Column A (position 0): FULL_ADDRESS
  - Column B (position 1): COUNTY
  - Column E (position 4): Owner_Ownership

Moving any of these columns will cause the Ecorp Upload generation to pull incorrect data and fail.

## ✅ Adding New MCAO Headers is Supported

You CAN safely add new columns from the MCAO API. The system handles additional columns well when added correctly.

### Requirements for Adding New Columns

1. **Verify API Support**: Ensure the MCAO API actually returns the fields you want to add
2. **Append Only**: New columns must be added AFTER the existing 106 columns (starting at column DC/position 106)
3. **Update Three Files**:
   - `src/adhs_etl/mcao_field_mapping.py` - Add to MCAO_MAX_HEADERS list
   - `src/adhs_etl/mcao_client.py` - Add mapping logic in map_to_max_headers()
   - `MCAO/MAX_HEADERS.xlsx` - Update reference documentation

### Template Prompt for Claude Code

Use this exact prompt template to successfully add new MCAO columns:

```
I need to add new MCAO API fields to the pipeline. Please add the following columns AFTER the existing 106 columns (starting at position 106/column DC):

New columns to add:
- [ColumnName1]: Maps from API field [api.field.path1]
- [ColumnName2]: Maps from API field [api.field.path2]
- [ColumnName3]: Maps from API field [api.field.path3]

Requirements:
1. Add these column names to the END of MCAO_MAX_HEADERS list in src/adhs_etl/mcao_field_mapping.py
2. Update the assertion to check for the new total (currently 106 +number of new columns)
3. In src/adhs_etl/mcao_client.py, add mapping logic in the map_to_max_headers() function to map the API response fields to these new columns
4. Ensure all new mappings handle None/missing values by converting to empty strings
5. Verify the column order is preserved and no existing columns are moved
6. Update MCAO/MAX_HEADERS.xlsx documentation to reflect the new columns
7. Test that the Ecorp pipeline still works correctly (it uses columns A, B, and E by position)
8. Update all hardcoded "84" references in:
   - scripts/test_mcao_integration.py (lines 30, 41, 54)
   - scripts/test_mcao_mapping.py (lines 54-55)
   - scripts/process_months_local.py (line 225)
   - PIPELINE_FLOW.md and README.md documentation
9. Run pytest scripts/test_mcao_*.py to verify all tests pass

Example API response structure for reference:
[Paste a sample API response showing where these fields come from]

Please implement these changes while ensuring no existing functionality breaks.
```

### Example Implementation Pattern

When adding a new field, the code should follow this pattern:

```python
# In mcao_field_mapping.py - Add to end of list
MCAO_MAX_HEADERS = [
    # ... existing 106 columns ...
    'Valuations_0_AssessmentRatioPercentage',    # Column DB (position 105)
    'YourNewField1',                             # Column DC (position 106)
    'YourNewField2',                             # Column DD (position 107)
]

# In mcao_client.py - Add mapping logic
def map_to_max_headers(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing mappings ...

    # New field mappings
    if 'parcel' in api_data and api_data['parcel']:
        parcel = api_data['parcel']
        mapped['YourNewField1'] = str(parcel.get('SomeApiField', ''))
        mapped['YourNewField2'] = str(parcel.get('AnotherApiField', ''))

    return mapped
```

### Downstream Impact Checklist

Before deploying changes, verify:
- [ ] Total column count matches new expected value (106 +additions)
- [ ] Ecorp Upload still generates correctly with 4 columns
- [ ] MCAO_Complete files generate with all columns in order
- [ ] No existing scripts using positional indexing are affected
- [ ] Column names don't conflict with existing names
- [ ] All new columns handle null/missing values gracefully
- [ ] **Update all hardcoded "84" references** in test files and comments
- [ ] **Test script assertions** pass (multiple scripts assert exactly 106 columns)
- [ ] **Console output messages** updated (process_months_local.py mentions "84 fields")
- [ ] **Column count validation** in ecorp.py still works (checks for minimum 5 columns)

### Files Requiring Updates for Column Additions

When adding new columns, these files contain hardcoded references to "84" that must be updated:

1. **Core Files** (MUST update):
   - `src/adhs_etl/mcao_field_mapping.py` - Line 146: assertion for exactly 106 columns (already updated)
   - `scripts/test_mcao_integration.py` - Lines 30, 41, 54: assertions for 84 columns
   - `scripts/test_mcao_mapping.py` - Lines 54-55: references to "out of 84"

2. **Display Messages** (should update for accuracy):
   - `scripts/process_months_local.py` - Line 225: mentions "enriched with 84 fields"

3. **Documentation** (update for completeness):
   - `PIPELINE_FLOW.md` - References to 84 property fields
   - `README.md` - Mentions "84 fields from Maricopa County Assessor"

### Common Pitfalls to Avoid

1. **Don't rename existing columns** - This breaks field references throughout the pipeline
2. **Don't insert columns in the middle** - Always append to the end
3. **Don't assume API fields exist** - Always use `.get()` with defaults
4. **Don't forget the assertion update** - The column count check will fail if not updated
5. **Don't skip testing Ecorp** - It's the most fragile part due to positional dependencies
6. **Don't forget test file updates** - Multiple test scripts have hardcoded assertions for 84 columns

### Getting API Field Names

To find available API fields:
1. Check `MCAO/API_Responses/` for sample JSON responses
2. Review `MCAO/mcao-api-ref/mcao-api-reference.md` for field documentation
3. Run a test API call and save the response to see actual field structure

### Performance Considerations

Adding new columns has these impacts:

1. **File Size**: Each new column increases Excel file size (approximately 10-50KB per column per 1000 rows)
2. **Memory Usage**: Pandas DataFrames use more memory with additional columns
3. **Processing Time**: Minimal impact unless new columns require additional API calls
4. **Excel Limits**: Excel supports up to 16,384 columns (XFD), so adding a few won't hit limits
5. **Network Transfer**: Larger files take longer to upload/download if using cloud storage

### Support

If the pipeline breaks after adding columns:
1. Check that existing columns A, B, and E haven't moved
2. Verify the MCAO_MAX_HEADERS list has exactly the expected number of columns
3. Ensure all new mappings handle None values
4. Review Ecorp/Upload generation for correct column extraction
5. Run the test suite: `pytest scripts/test_mcao_*.py`
6. Verify Ecorp still extracts from correct positions (columns 0, 1, 4)
# BatchData BD_ Prefix Migration Summary

## Overview
Date: November 20, 2025
Version: 2.0

All BatchData columns have been standardized to use the `BD_` prefix for clear namespace separation and to prevent naming conflicts with other pipeline stages.

## Column Naming Changes

### Core Input/Output Columns (16 columns)
| Old Name | New Name | Status |
|----------|----------|--------|
| `record_id` | `BD_RECORD_ID` | Active |
| `source_type` | `BD_SOURCE_TYPE` | Active |
| `source_entity_name` | `BD_ENTITY_NAME` | Active |
| `source_entity_id` | `BD_SOURCE_ENTITY_ID` | Active |
| `title_role` | `BD_TITLE_ROLE` | Active |
| `target_first_name` | `BD_TARGET_FIRST_NAME` | **REMOVED (Nov 2025)** |
| `target_last_name` | `BD_TARGET_LAST_NAME` | **REMOVED (Nov 2025)** |
| `owner_name_full` | `BD_OWNER_NAME_FULL` | **REMOVED (Nov 2025)** |
| `address_line1` | `BD_ADDRESS` | Active |
| `address_line2` | `BD_ADDRESS_2` | **REMOVED (Nov 2025)** |
| `city` | `BD_CITY` | Active |
| `state` | `BD_STATE` | Active |
| `zip` | `BD_ZIP` | Active |
| `county` | `BD_COUNTY` | Active |
| `apn` | `BD_APN` | Active |
| `mailing_line1` | `BD_MAILING_LINE1` | Active |
| `mailing_city` | `BD_MAILING_CITY` | Active |
| `mailing_state` | `BD_MAILING_STATE` | Active |
| `mailing_zip` | `BD_MAILING_ZIP` | Active |
| `notes` | `BD_NOTES` | Active |

**Note**: 4 columns removed in November 2025. API uses address-only for skip-trace lookups.

### Enrichment Columns
| Old Pattern | New Pattern |
|-------------|-------------|
| `phone_1` to `phone_10` | `BD_PHONE_1` to `BD_PHONE_10` |
| `phone_N_type` | `BD_PHONE_N_TYPE` |
| `phone_N_carrier` | `BD_PHONE_N_CARRIER` |
| `phone_N_dnc` | `BD_PHONE_N_DNC` |
| `phone_N_tcpa` | `BD_PHONE_N_TCPA` |
| `phone_N_confidence` | `BD_PHONE_N_CONFIDENCE` |
| `email_1` to `email_10` | `BD_EMAIL_1` to `BD_EMAIL_10` |
| `email_N_tested` | `BD_EMAIL_N_TESTED` |

### API Status Columns
| Old Name | New Name |
|----------|----------|
| `api_status` | `BD_API_STATUS` |
| `api_response_time` | `BD_API_RESPONSE_TIME` |
| `persons_found` | `BD_PERSONS_FOUND` |
| `phones_found` | `BD_PHONES_FOUND` |
| `emails_found` | `BD_EMAILS_FOUND` |
| `pipeline_version` | `BD_PIPELINE_VERSION` |
| `pipeline_timestamp` | `BD_PIPELINE_TIMESTAMP` |
| `stages_applied` | `BD_STAGES_APPLIED` |

## Files Updated

### Core Code Files
- ✅ `Batchdata/src/transform.py` - All column creation and references updated
- ✅ `Batchdata/src/batchdata_sync.py` - API request/response mapping updated
- ✅ `Batchdata/src/io.py` - Output field references updated
- ✅ `Batchdata/src/run.py` - Merge operations updated
- ✅ `Batchdata/src/normalize.py` - Default parameter updated

### Documentation Files
- ✅ `Batchdata/README.md` - Added column naming convention section
- ✅ `Batchdata/PIPELINE_INTEGRATION_GUIDE.md` - Updated input/output specifications

### Files Removed
- ❌ `Batchdata/template_config.xlsx` - No longer needed (CONFIG from .env)
- ❌ `Batchdata/tests/batchdata_local_input.xlsx` - Consolidated to Batchdata_Template.xlsx

## Template Consolidation

### Previous Structure (Complex)
- Multiple template files with different purposes
- CONFIG sheet in Excel files
- BLACKLIST_NAMES sheet in Excel files
- Unclear which template to use

### New Structure (Simplified)
- Single template: `Batchdata_Template.xlsx`
- CONFIG from environment variables
- Blacklist from dynamic code logic
- Clear BD_ prefix on all columns

## Benefits of BD_ Prefix

1. **Namespace Separation**: Clear distinction from other pipeline stages (MCAO, Ecorp, etc.)
2. **Data Lineage**: Easy to track which data came from BatchData enrichment
3. **Conflict Prevention**: No column name collisions with other data sources
4. **Consistency**: All BatchData fields follow same naming pattern
5. **Documentation**: Self-documenting column names

## Migration Notes

### For Existing Files
Files created before this migration will still have old column names. The pipeline is NOT backward compatible - all new processing must use BD_ prefixed columns.

### For New Development
All new code must use BD_ prefixed column names. The transform functions in `transform.py` automatically create the correct column names.

### Testing
Test files need to be updated to use BD_ prefixed columns. Any test that creates mock DataFrames must use the new column naming convention.

## Version History
- **1.0**: Original implementation with non-prefixed columns
- **2.0**: BD_ prefix migration (November 20, 2025)

## Contact
For questions about this migration, refer to the main project documentation or the BatchData README.md file.
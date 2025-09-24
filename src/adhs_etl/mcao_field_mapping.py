"""
MCAO Field Mapping Configuration
=================================

Defines the column structure and order for MCAO_Complete output files
based on MAX_HEADERS.xlsx specification.
"""

# Column order and names from MAX_HEADERS.xlsx
# These are the exact 84 columns in order (A through CG)
MCAO_MAX_HEADERS = [
    # Columns A-C (from MCAO_Upload)
    'FULL_ADDRESS',  # Column A
    'COUNTY',        # Column B
    'APN',           # Column C

    # Columns D-N (Owner Information)
    'Owner_OwnerID',                   # Column D
    'Owner_Ownership',                  # Column E
    'Owner_OwnerName',                  # Column F
    'Owner_FullMailingAddress',         # Column G
    'Owner_MailingAddress_Street',      # Column H
    'Owner_MailingAddress_City',        # Column I
    'Owner_MailingAddress_State',       # Column J
    'Owner_MailingAddress_Zip',         # Column K
    'Owner_DeedDate',                   # Column L
    'Owner_SalePrice',                  # Column M
    'Owner_Mailing_CareOf',             # Column N

    # Columns O-Y (Property Information)
    'PropertyID',                       # Column O
    'PropertyType',                     # Column P
    'LotSize',                          # Column Q
    'IsResidential',                    # Column R
    'YearBuilt',                        # Column S
    'TaxDistrict',                      # Column T
    'SubdivisionName',                  # Column U
    'LegalDescription',                 # Column V
    'Zoning',                           # Column W
    'LandUse',                          # Column X
    'EffectiveDate',                    # Column Y

    # Columns Z-AI (Residential Property Data)
    'ResidentialPropertyData_LivableSpace',               # Column Z
    'ResidentialPropertyData_NumberOfGarages',            # Column AA
    'ResidentialPropertyData_OriginalConstructionYear',   # Column AB
    'ResidentialPropertyData_Detached_Livable_sqft',     # Column AC
    'ResidentialPropertyData_Bedrooms',                   # Column AD
    'ResidentialPropertyData_Bathrooms',                  # Column AE
    'ResidentialPropertyData_Pools',                      # Column AF
    'ResidentialPropertyData_AirConditioning',           # Column AG
    'ResidentialPropertyData_HeatingType',               # Column AH
    'ResidentialPropertyData_WaterHeater',               # Column AI

    # Columns AJ-AO (Commercial Property Data)
    'CommercialPropertyData_GrossSquareFeet',    # Column AJ
    'CommercialPropertyData_NetLeasableArea',    # Column AK
    'CommercialPropertyData_NumberOfUnits',      # Column AL
    'CommercialPropertyData_NumberOfStories',    # Column AM
    'CommercialPropertyData_ParkingSpaces',      # Column AN
    'CommercialPropertyData_ConstructionType',   # Column AO

    # Columns AP-AZ (Valuations - Year 0 and Year 1)
    'Valuations_0_LegalClassification',          # Column AP
    'Valuations_0_TaxYear',                      # Column AQ
    'Valuations_0_FullCashValue',                # Column AR
    'Valuations_0_AssessedValue',                # Column AS
    'Valuations_0_LimitedPropertyValue',         # Column AT
    'Valuations_0_Land_FullCashValue',           # Column AU
    'Valuations_0_Improvements_FullCashValue',   # Column AV
    'Valuations_1_LegalClassification',          # Column AW
    'Valuations_1_TaxYear',                      # Column AX
    'Valuations_1_FullCashValue',                # Column AY
    'Valuations_1_AssessedValue',                # Column AZ

    # Column BA (Valuation continued)
    'Valuations_1_LimitedPropertyValue',         # Column BA

    # Columns BB-BH (Sales History)
    'Sales_0_SaleDate',                          # Column BB
    'Sales_0_SalePrice',                         # Column BC
    'Sales_0_SaleType',                          # Column BD
    'Sales_0_Grantor',                           # Column BE
    'Sales_0_Grantee',                           # Column BF
    'Sales_1_SaleDate',                          # Column BG
    'Sales_1_SalePrice',                         # Column BH
    'Sales_1_SaleType',                          # Column BI

    # Columns BJ-BO (GIS Data)
    'GIS_Latitude',                              # Column BJ
    'GIS_Longitude',                             # Column BK
    'GIS_MapNumber',                             # Column BL
    'GIS_Township',                              # Column BM
    'GIS_Range',                                 # Column BN
    'GIS_Section',                               # Column BO

    # Columns BP-CE (Additional Data)
    'CensusBlock',                               # Column BP
    'SchoolDistrict',                            # Column BQ
    'FireDistrict',                              # Column BR
    'AssessmentRatio',                           # Column BS
    'ExemptionCode',                             # Column BT
    'ExemptionValue',                            # Column BU
    'SpecialAssessments',                        # Column BV
    'TotalTaxes',                                # Column BW
    'DelinquentTaxes',                          # Column BX
    'PropertyClass',                             # Column BY
    'UseCode',                                   # Column BZ

    # Columns CA-CC (Permits)
    'Permits_0_PermitDate',                      # Column CA
    'Permits_0_PermitType',                      # Column CB
    'Permits_0_PermitValue',                     # Column CC

    # Columns CD-CF (Improvements)
    'Improvements_Pool',                         # Column CD
    'Improvements_Tennis',                       # Column CE
    'Improvements_Other'                         # Column CF
]

# Verify we have exactly 84 columns
assert len(MCAO_MAX_HEADERS) == 84, f"Expected 84 columns, got {len(MCAO_MAX_HEADERS)}"

# Create a set for quick lookup of valid column names
MCAO_VALID_COLUMNS = set(MCAO_MAX_HEADERS)

def get_empty_mcao_record():
    """
    Get an empty MCAO record with all fields initialized to empty strings.

    Returns:
        Dictionary with all MCAO_MAX_HEADERS keys set to empty strings
    """
    return {col: '' for col in MCAO_MAX_HEADERS}

def validate_mcao_record(record: dict) -> dict:
    """
    Validate and clean an MCAO record to ensure it has all required columns.

    Args:
        record: Dictionary with MCAO data

    Returns:
        Cleaned record with all required columns
    """
    # Start with empty template
    clean_record = get_empty_mcao_record()

    # Fill in values from input record
    for col in MCAO_MAX_HEADERS:
        if col in record and record[col] is not None:
            # Convert to string and handle various null representations
            val = str(record[col])
            if val.upper() in ['NONE', 'NULL', 'NA', 'N/A']:
                clean_record[col] = ''
            else:
                clean_record[col] = val
        else:
            clean_record[col] = ''

    return clean_record
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
    'Improvements_Other',                        # Column CF

    # Columns CG-DB (New fields - 22 additional columns added from MAX_HEADERS.xlsx)
    'IsRental',                                              # Column CG (position 84)
    'LocalJusidiction',                                      # Column CH (position 85) - Note: typo preserved to match Excel header
    'MCR',                                                   # Column CI (position 86)
    'MapIDs_Book/Map Maps_0_UpdateDate',                    # Column CJ (position 87)
    'MapIDs_Book/Map Maps_0_Url',                           # Column CK (position 88)
    'MapIDs_Book/Map Maps_1_UpdateDate',                    # Column CL (position 89)
    'MapIDs_Book/Map Maps_1_Url',                           # Column CM (position 90)
    'MapIDs_Book/Map Maps_2_UpdateDate',                    # Column CN (position 91)
    'MapIDs_Book/Map Maps_2_Url',                           # Column CO (position 92)
    'NumberOfParcelsInMCR',                                  # Column CP (position 93)
    'NumberOfParcelsInSTR',                                  # Column CQ (position 94)
    'NumberOfParcelsInSubdivision',                          # Column CR (position 95)
    'Owner_DeedType',                                        # Column CS (position 96)
    'Owner_SaleDate',                                        # Column CT (position 97)
    'PEPropUseDesc',                                         # Column CU (position 98)
    'PropertyAddress',                                       # Column CV (position 99)
    'PropertyDescription',                                   # Column CW (position 100)
    'ResidentialPropertyData_ConstructionYear',              # Column CX (position 101)
    'ResidentialPropertyData_ExteriorWalls',                 # Column CY (position 102)
    'ResidentialPropertyData_ImprovementQualityGrade',       # Column CZ (position 103)
    'Valuations_0_AssessedLPV',                             # Column DA (position 104)
    'Valuations_0_AssessmentRatioPercentage'                # Column DB (position 105)
]

# Verify we have exactly 106 columns (84 original + 22 new)
assert len(MCAO_MAX_HEADERS) == 106, f"Expected 106 columns, got {len(MCAO_MAX_HEADERS)}"

# Verify critical columns haven't moved (for Ecorp pipeline safety)
assert MCAO_MAX_HEADERS[0] == 'FULL_ADDRESS', "Column A must be FULL_ADDRESS"
assert MCAO_MAX_HEADERS[1] == 'COUNTY', "Column B must be COUNTY"
assert MCAO_MAX_HEADERS[4] == 'Owner_Ownership', "Column E must be Owner_Ownership"

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
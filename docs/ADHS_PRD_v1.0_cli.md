
1. Project overview and Goal ' Have a simple clean functioning database with
exceptional mapping & attention to detail. I have a monthly recurring number of
datasets to download. The goal is to have a singular script that gives
Reformatting capabilities and Analysis with perfect data execution. References a
local folder called 'Raw New Month', located:
/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/Cursor MY MAP/Raw
New Month. These separate excel files are a straight raw download from Arizona
Department of Health Services where it lists active licenses each month. There
is a lot of value to be able to see who is no longer licensed as it could be a
Lead opportunity for an owner looking to sell the location. Besides
documentation output files, this is a large part of the ultimate goal to
populate the 'M.YY Analysis.xlsx' output file with perfect accuracy.

2. Tech Stack ' Local folders listed in the Folder Structure. Using MS Excel 365
for all workbooks. Maricopa County Assessors Office API key:
cc6f7947-2054-479b-ae49-f3fa1c57f3d8
3. Folder Structure 'Inputs described in (i.), Outputs described in (ii.,iii.,iv.)
   - There is a non-linear asynchronous nature to what is considered a 'New Month'
& the input folder of 'Raw New Month' is really just a folder (References a
local folder called 'Raw New Month', located:
/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/Cursor MY MAP/Raw
New Month.) to reference which month we're running results for. Because there is
10 months of data as of June 2025 when we are making this tool, there might be
cases where we're running an older months (takes the form of it's own folder) to create alignment on the data with
the Goal to get to the codebase working & it truly becomes 'New Month'. There should be functionality to run multiple months in RAW NEW MONTH, grouping standalone .xlsx file as one and folders within the directory (if any), as other months. Referencing the subfolder name will indicate which month that is. With the Raw New Month naming designation OK for the grouping of the 12 or so standalone files.

   - 'M.YY Reformat.xlsx'; a singular file combing the many Raw separate excel
file's records that formats the data into only following field headers, getting
assistance from similar field mapping as 'track_files_ii.py'.


```tsv
A1 'MONTH'; Records should all be in Number format.
B1 'YEAR'; Records should all be in Number format.
C1 'PROVIDER TYPE'; Raw name of every of the 12 excel Raw files (i.e.
```
ADULT_BEHAVIORAL_HEALTH_THERAPEUTIC_HOME, ASSISTED_LIVING_CENTER,
ASSISTED_LIVING_HOME, BEHAVIORAL_HEALTH_INPATIENT,
BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY, CC_CENTERS, CC_GROUP_HOMES,
DEVELOPMENTALLY_DISABLED_GROUP_HOME, HOSPITAL_REPORT, NURSING_HOME,
NURSING_SUPPORTED_GROUP_HOMES, OUTPATIENT_HEALTH_TREATMENT_CENTER_REPORT

'PROVIDER'; Reference Field mapping in 'track_files_ii.py'.
'ADDRESS'; Reference Field mapping in 'track_files_ii.py'.
'CITY'; Reference Field mappi1ng in 'track_files_ii.py'.
'ZIP'; Reference Field mapping in 'track_files_ii.py'.
'CAPACITY'; Reference Field mapping in 'track_files_ii.py'.
'LONGITUDE'; Reference Field mapping in 'track_files_ii.py'.
'LATITUDE'; Reference Field mapping in 'track_files_ii.py'.
'PROVIDER GROUP INDEX #';
All records should pass through an upper-case command. The output location of
this is __________. Additional logic like IF 20 consecutive characters 1:1
match, THEN group together.

The field mapping from Raw to Reformat can use the 'track_files_ii.py' in this
project directory as a field mapping reference. Ignore the outputs of said
file.as a template. Know that there should also be logic to check for new field
names and give a follow up response prior to running the script all the way
through until confirmation of New field mapping.

   - 'Reformat All to Date M.YY'; this simply takes the newly reformatted excel
file and adds it to the prev. month Reformat All to Date M.YY'. There should be
some logic in here to if ran a second time where the month/year conflict with
existing records in previous month, it replaces with only one version, that
being This New Month (no duplicates). The output location is the same as 'M.YY
Reformat.xlsx'

   - The 'M.YY Analysis.xlsx' is the final output excel. This is the most
sophisticated logic, most number of workbooks and fields so we'll break this up
to properly focus on each. The fields of 'v100Track_this_shit.xlsx' is the basis
for the below Analysis file.

a. Sheet #1 Summary: All relevant counts are just for the New Month. Column A
has the metrics and column B has what the count is for each metric - This needs to be referenced when populating Counts in B. For Seller Leads count all that are designated Seller Leads or Seller/Survey Lead. For
Survey Leads count all Survey Lead and Seller/Survey Lead. The following should be used to give context for what exactly the count values should reference for Column B- also be sure to reference Column A.

B2 i.e. Count of all ADDRESS
B3 i.e. Count of all PROVIDER
B4 i.e. highest PROVIDER GROUP INDEX #
B5 i.e. Count of all Blank records
B6 i.e. count of 'Y' records
B8 - B14 i.e. Based off of the PROVIDER's record for PROVIDER TYPE & ADDRESS details in Column A
B16 i.e. ‘Seller Lead’, or ‘Seller/Survey Lead’
B17 i.e. ‘Survey Lead’, or ‘Seller/Survey Lead’
B19 - B31 i.e. Total records for Month (all PROVIDER TYPE's) for corresponding PROVIDER TYPE detailed in column A


b. Sheet #2 BlanksCount: Fill in this simple table for all twelve PROVIDER TYPE
fields (starting in A2).

```tsv
      B1 'MONTH'; From Reformat
C1 'YEAR'; From Reformat
D1 'PROVIDER'; From Reformat
E1 'ADDRESS'; From Reformat
F1 'CITY'; From Reformat
G1 'ZIP'; From Reformat
H1 'CAPACITY'; From Reformat
I1 'LONGITUDE'; From Reformat
J1 'LATITUDE'; From Reformat
K1 'PROVIDER GROUP INDEX #'; From Reformat
```

c. Sheet #3 Analysis This should reference previous analysis or any All to Date
.xlsx to always include all of the current, previous and otherwise licensees and
providers, and MATCH them to the corresponding record to give summary and
analysis on each, here are those fields in more detail:

```tsv
A1 'SOLO PROVIDER TYPE PROVIDER [Y, #]'; If a single record and no other match
```
for an alternative PROVIDER TYPE for a records PROVIDER and ADDRESS fields, then
this field is marked 'Y' aka Yes. If there is a match in PROVIDER and ADDRESS
fields, this should be marked '#' where # is equal to the Count of all PROVIDER
TYPE's that matched 1:1 with PROVIDER and ADDRESS.


```tsv
B1 'PROVIDER TYPE'; Always individual record of that records PROVIDER.
C1 'PROVIDER'; Leading data point is the Name of Provider. Direct from Reformat
```
field mapping. Number of records should be consistent.
```tsv
D1 'ADDRESS'; Also a leading data point with PROVIDER. From Reformat field mapping.
E1 'CITY'; From Reformat field mapping.
F1 'ZIP'; From Reformat
G1 'CAPACITY'; From Reformat field mapping.
H1 'LONGITUDE'; From Reformat field mapping.
I1 'LATITUDE'; From Reformat field mapping.
J1 'PROVIDER GROUP INDEX #'; This is assigning a number to each PROVIDER GROUP
```
to be shared by each PROVIDER within the PROVIDER GROUP. From Reformat field
mapping.

```tsv
K1 'PROVIDER GROUP (DBA Concat)'; is essentially a concatenate of each
```
'PROVIDER'; name within 85%+ confidence of each other. Followed by parenthesis
of that record's ADDRESS. This cells contents of multiple PROVIDER's comprising
this GROUP to be separated by comma following each closed ADDRESS parenthesis.
Example:
For Ready for Life LLC, the 'PROVIDER GROUP (DBA Concat)' would be 'Ready for
Life II (ADDRESS), Ready for Life III (ADDRESS)'
Vice versa for Ready for Life II, the 'PROVIDER GROUP (DBA Concat)' would be
'Ready for Life LLC (ADDRESS), Ready for Life III (ADDRESS)'
		If none within group, return should be: 'n/a'

```tsv
L1 'PROVIDER GROUP, ADDRESS Count'; Count of all ADDRESS within the PROVIDER GROUP
M1 'This month Status'; is one of the following summary texts:
```
      'New PROVIDER TYPE, New ADDRESS'
      'New PROVIDER TYPE, Existing ADDRESS'
			'Existing PROVIDER TYPE, New ADDRESS'
			'Existing PROVIDER TYPE, Existing ADDRESS'
			'Lost PROVIDER TYPE, Existing ADDRESS'
			'Lost PROVIDER TYPE, Lost ADDRESS (0 remain)'
			'Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)'

```tsv
      N1 'Lead Type' is simply a match of Status result to the below.
```
      'New PROVIDER TYPE, New ADDRESS' = 'Survey Lead',
      'New PROVIDER TYPE, Existing ADDRESS' = 'Survey Lead',
      'Existing PROVIDER TYPE, New ADDRESS' = 'Survey Lead',
'Existing PROVIDER TYPE, Existing ADDRESS' = 'Survey Lead',
'Lost PROVIDER TYPE, Existing ADDRESS' = 'Seller/Survey Lead',
      'Lost PROVIDER TYPE, Lost ADDRESS (0 remain)' = 'Seller Lead',
      'Lost PROVIDER TYPE, Lost ADDRESS (1+ remain)' = 'Seller Lead'
```tsv
O1  '9.24 count' to AD1 '12.25 count'; is a Count of number of ADDRESS for the
```
corresponding PROVIDER record. For the New Month, it should only update that
column. If a month never processed, leave blank i.e. ' '. If a same month
processed a second time, overwrite that month alone.



```tsv
      AE1 '10.24 to prev' to AS1 '12.25 to prev'; Results are either
```
'Decreased', 'Increased' or 'No movement' for the count comparing the subject
month to the previous in O1 to AD1. For example in any given record, if O2 =
'1', P2 = '0', Q2 = '0', R2 = '2' then in AE2 it would show 'Decreased'. AF2 'No
movement'. AG2 'Increased'.


```tsv
AT1 '9.24 summary' to BI1 '12.25 summary' is simply a concatenate of the
```
following fields separated by ', '. Fields in order: L, K, J.

BJ1 is Month
BK1 is Year
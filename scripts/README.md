# ADHS ETL Batch Processing Script

## Quick Start Guide

This script automates processing multiple months of ADHS data. Perfect for junior developers! 🚀

### What This Script Does

1. **Scans** your `ALL-MONTHS/` folder for available month data
2. **Shows you a menu** to pick start and end months
3. **Processes each month** in chronological order automatically
4. **Generates all output files** (Reformat, All-to-Date, Analysis) for each month
5. **Cleans up** temporary files between runs

### How to Use

1. **Open Terminal** and navigate to your project directory:
   ```bash
   cd "/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/Cursor MY MAP"
   ```

2. **Run the script**:
   ```bash
   poetry run python scripts/batch_process_months.py
   ```

3. **Follow the prompts**:
   - View available months
   - Select start month (e.g., September 2024)
   - Select end month (e.g., July 2025)
   - Choose dry-run mode (recommended first time)
   - Confirm and let it run!

### Example Run

```
====================================
ADHS ETL Batch Processing Script
====================================

📋 Step 1: Checking prerequisites
✅ Poetry is available
✅ Created Raw-New-Month directory

📋 Step 2: Scanning for available months
✅ Found 11 available months

📅 Available Months:
----------------------------------------
 1.   9.24 - September 2024 (Raw 9.24)
 2.  10.24 - October 2024 (Raw 10.24)
 3.  11.24 - November 2024 (Raw 11.24)
 4.  12.24 - December 2024 (Raw 12.24)
 5.   1.25 - January 2025 (Raw 1.25)
 6.   2.25 - February 2025 (Raw 2.25)
 7.   3.25 - March 2025 (Raw 3.25)
 8.   4.25 - April 2025 (Raw 4.25)
 9.   5.25 - May 2025 (Raw 5.25)
10.   6.25 - June 2025 (Raw 6.25)
11.   7.25 - July 2025 (Raw 7.25)

📋 Step 3: Selecting month range

Select START month (1-11): 1
Select END month (1-11): 11

📋 Selected months to process:
  • 9.24 (Raw 9.24)
  • 10.24 (Raw 10.24)
  • ... (all months)
  • 7.25 (Raw 7.25)

Run in dry-run mode? (y/N): y

🚀 Ready to process 11 months
Continue? (y/N): y
```

### For Your 11-Month Scenario

For your specific case with 11 months of data:

1. **First Run** (Recommended):
   - Select months 1-11 (September 2024 to July 2025)
   - Choose **dry-run mode** to test without creating files
   - This lets you see what would happen

2. **Second Run** (Actual Processing):
   - Select months 1-11 again
   - Choose **normal mode** (not dry-run)
   - Let it process all 11 months

### What You'll Get

After processing all 11 months:

**Reformat folder:** 11 files
- `9.24_Reformat_{timestamp}.xlsx` through `7.25_Reformat_{timestamp}.xlsx`

**All-to-Date folder:** 11 files
- `7.25_Reformat_All_to_Date_{timestamp}.xlsx` (final file contains all 11 months)

**Analysis folder:** 11 files
- `9.24_Analysis_{timestamp}.xlsx` through `7.25_Analysis_{timestamp}.xlsx`
- Each shows lost licenses and seller leads for that month

### Tips for Success

✅ **Do**: Run in dry-run mode first to test
✅ **Do**: Process months in chronological order (script does this automatically)
✅ **Do**: Let the script run without interruption
✅ **Do**: Check output files after completion

❌ **Don't**: Manually copy files to Raw-New-Month while script is running
❌ **Don't**: Skip months - each month needs the previous month's data
❌ **Don't**: Run multiple instances of the script at once

### If Something Goes Wrong

- **Press Ctrl+C** to stop the script safely
- **Check the error messages** - they're color-coded and helpful
- **Run individual months** if needed:
  ```bash
  # Copy files manually
  cp ALL-MONTHS/Raw\ 1.25/*.xlsx Raw-New-Month/
  
  # Run single month
  poetry run adhs-etl run --month 1.25 --raw-dir ./Raw-New-Month
  
  # Clean up
  rm Raw-New-Month/*.xlsx
  ```

### Need Help?

- Type `q` or `quit` at any prompt to exit
- The script shows colored output:
  - 🟢 Green = Success
  - 🔴 Red = Error
  - 🟡 Yellow = Warning
  - 🔵 Blue = Information

Happy analyzing! 📊
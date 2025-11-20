#!/usr/bin/env python3
"""
Statutory Agent Analysis Script
================================

Analyzes Ecorp Complete files to identify professional service companies
vs. individual statutory agents for blacklist creation.

Usage:
    python scripts/analyze_statutory_agents.py
"""

import pandas as pd
from collections import Counter
from pathlib import Path
import re


def is_professional_service(name: str) -> bool:
    """
    Identify if a statutory agent name represents a professional service company.

    Professional service indicators:
    - Contains "SERVICE", "AGENT", "REGISTERED"
    - Contains "CORPORATION SERVICE", "CT CORPORATION"
    - Contains "INCORP", "INC.", "LLC" in agent name
    - Contains "COMPANY", "ASSOCIATES"
    """
    if not name or pd.isna(name):
        return False

    name_upper = str(name).upper()

    # Professional service keywords
    service_keywords = [
        'CORPORATION SERVICE',
        'CT CORPORATION',
        'REGISTERED AGENT',
        'AGENT SOLUTIONS',
        'INCORPORATING SERVICES',
        'INCORP SERVICES',
        'STATUTORY AGENT',
        'CORPORATE AGENT',
        'RESIDENT AGENT',
        'AGENT, INC',
        'AGENT LLC',
        'AGENTS LLC',
        'BUSINESS FILINGS',
        'LEGALZOOM',
        'NORTHWEST REGISTERED',
        'WOLTERS KLUWER',
        'COGENCY GLOBAL',
        'CSC',  # Corporation Service Company abbreviation
        'PARACORP',
        'SWYFT FILINGS',
        'INCFILE',
        'BIZFILINGS'
    ]

    for keyword in service_keywords:
        if keyword in name_upper:
            return True

    # Pattern: ends with "SERVICES", "SERVICE COMPANY", etc.
    if re.search(r'\b(SERVICES?|SOLUTIONS)\s*(COMPANY|INC\.?|LLC)?\s*$', name_upper):
        return True

    # Pattern: "XYZ AGENT" or "AGENT XYZ"
    if re.search(r'\bAGENT\b', name_upper) and not re.search(r'\b(REAL ESTATE|INSURANCE|INSURANCE AGENT)\b', name_upper):
        return True

    return False


def is_individual_name(name: str) -> bool:
    """
    Identify if a name appears to be an individual person.

    Individual indicators:
    - 2-4 words
    - No business entity keywords
    - Proper name pattern (Title case or ALL CAPS)
    """
    if not name or pd.isna(name):
        return False

    name_str = str(name).strip()
    words = name_str.split()

    # Individuals typically have 2-4 words
    if len(words) < 2 or len(words) > 4:
        return False

    # Check for business keywords
    business_keywords = [
        'LLC', 'INC', 'CORP', 'COMPANY', 'CO.', 'PARTNERSHIP',
        'SERVICES', 'SERVICE', 'ASSOCIATES', 'TRUST',
        'FOUNDATION', 'GROUP', 'ENTERPRISES', 'HOLDINGS',
        'INVESTMENTS', 'PROPERTIES', 'REALTY', 'AGENT',
        'REGISTERED', 'STATUTORY', 'CORPORATE'
    ]

    name_upper = name_str.upper()
    for keyword in business_keywords:
        if keyword in name_upper:
            return False

    return True


def analyze_files(file_paths):
    """Analyze Ecorp Complete files for statutory agent patterns."""

    all_agents = []

    for file_path in file_paths:
        print(f"\n{'='*80}")
        print(f"Reading: {file_path.name}")
        print(f"{'='*80}")

        try:
            df = pd.read_excel(file_path)
            print(f"Total records: {len(df):,}")

            # Look for StatutoryAgent1_Name column
            stat_col = None
            for col in df.columns:
                if 'StatutoryAgent1_Name' in str(col):
                    stat_col = col
                    break

            # If not found by name, try column Q (index 16)
            if stat_col is None and len(df.columns) > 16:
                stat_col = df.columns[16]
                print(f"Using column index 16: {stat_col}")

            if stat_col is None:
                print("ERROR: Cannot find StatutoryAgent1_Name column")
                continue

            # Get non-null agents
            agents = df[stat_col].dropna()
            print(f"Non-null statutory agents: {len(agents):,}")

            all_agents.extend(agents.tolist())

        except Exception as e:
            print(f"ERROR reading file: {e}")
            continue

    if not all_agents:
        print("\nERROR: No agent data found!")
        return

    print(f"\n{'='*80}")
    print(f"COMBINED ANALYSIS")
    print(f"{'='*80}")
    print(f"Total agents across all files: {len(all_agents):,}")
    print(f"Unique agents: {len(set(all_agents)):,}")

    # Count occurrences
    agent_counts = Counter(all_agents)

    # Classify agents
    professional_services = {}
    individuals = {}
    unknown = {}

    for name, count in agent_counts.items():
        if is_professional_service(name):
            professional_services[name] = count
        elif is_individual_name(name):
            individuals[name] = count
        else:
            unknown[name] = count

    # Print results
    print(f"\n{'='*80}")
    print(f"TOP 50 MOST COMMON STATUTORY AGENTS (ALL)")
    print(f"{'='*80}")
    print(f"{'Rank':<5} {'Count':<8} {'Type':<15} {'Name':<60}")
    print(f"{'-'*5} {'-'*8} {'-'*15} {'-'*60}")

    for i, (name, count) in enumerate(agent_counts.most_common(50), 1):
        if is_professional_service(name):
            agent_type = "PROFESSIONAL"
        elif is_individual_name(name):
            agent_type = "INDIVIDUAL"
        else:
            agent_type = "UNKNOWN"

        # Truncate long names for display
        display_name = str(name)[:60]
        print(f"{i:<5} {count:<8,} {agent_type:<15} {display_name:<60}")

    # Print professional services
    print(f"\n{'='*80}")
    print(f"PROFESSIONAL SERVICE COMPANIES ({len(professional_services)} unique)")
    print(f"{'='*80}")
    print(f"Total occurrences: {sum(professional_services.values()):,}")
    print(f"\n{'Count':<8} {'Name'}")
    print(f"{'-'*8} {'-'*70}")

    for name, count in sorted(professional_services.items(), key=lambda x: x[1], reverse=True):
        print(f"{count:<8,} {name}")

    # Print top individuals
    print(f"\n{'='*80}")
    print(f"TOP 20 INDIVIDUAL STATUTORY AGENTS")
    print(f"{'='*80}")
    print(f"{'Count':<8} {'Name'}")
    print(f"{'-'*8} {'-'*60}")

    for name, count in sorted(individuals.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"{count:<8,} {name}")

    # Create blacklist file
    blacklist_path = Path("Ecorp") / "statutory_agent_blacklist.txt"
    print(f"\n{'='*80}")
    print(f"Creating blacklist file: {blacklist_path}")
    print(f"{'='*80}")

    with open(blacklist_path, 'w') as f:
        f.write("# Statutory Agent Professional Service Blacklist\n")
        f.write(f"# Generated from Ecorp Complete file analysis\n")
        f.write(f"# Total professional services: {len(professional_services)}\n")
        f.write(f"# Total occurrences: {sum(professional_services.values()):,}\n")
        f.write("#\n")
        f.write("# These are registered agent/statutory agent service companies\n")
        f.write("# that should be filtered out when looking for actual owner contacts.\n")
        f.write("#\n")
        f.write("# Format: One name per line (exact match, case-insensitive)\n")
        f.write("#\n\n")

        for name in sorted(professional_services.keys()):
            f.write(f"{name}\n")

    print(f"✅ Blacklist created with {len(professional_services)} entries")

    # Create whitelist examples
    whitelist_path = Path("Ecorp") / "statutory_agent_whitelist_examples.txt"
    print(f"Creating whitelist examples: {whitelist_path}")

    with open(whitelist_path, 'w') as f:
        f.write("# Statutory Agent Individual Examples (Whitelist)\n")
        f.write(f"# These are examples of individual statutory agents that should be kept\n")
        f.write(f"# Total individuals: {len(individuals)}\n")
        f.write("#\n\n")

        for name, count in sorted(individuals.items(), key=lambda x: x[1], reverse=True)[:50]:
            f.write(f"{name} ({count} occurrences)\n")

    print(f"✅ Whitelist examples created with top 50 individuals")

    # Print unknown patterns for review
    if unknown:
        print(f"\n{'='*80}")
        print(f"UNKNOWN CLASSIFICATION (Review These)")
        print(f"{'='*80}")
        print(f"Total: {len(unknown)} unique names")
        print(f"\n{'Count':<8} {'Name'}")
        print(f"{'-'*8} {'-'*60}")

        for name, count in sorted(unknown.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"{count:<8,} {name}")

    # Print patterns
    print(f"\n{'='*80}")
    print(f"BLACKLIST PATTERNS FOR FILTERING")
    print(f"{'='*80}")
    print("""
Keywords that indicate professional services:
- "CORPORATION SERVICE" or "CT CORPORATION"
- "REGISTERED AGENT" or "STATUTORY AGENT"
- "AGENT SOLUTIONS" or "AGENT LLC"
- "INCORPORATING SERVICES" or "INCORP SERVICES"
- "BUSINESS FILINGS" or "BIZFILINGS"
- "LEGALZOOM" or "NORTHWEST REGISTERED"
- "CSC" (Corporation Service Company)
- Ends with "SERVICES", "SERVICE COMPANY"
- Contains "AGENT" (unless real estate/insurance context)

Individual name patterns (KEEP these):
- 2-4 words
- No business keywords (LLC, INC, CORP, etc.)
- Proper name format
- Examples: "John Smith", "Mary Jane Anderson", "Robert J. Williams"
""")


def main():
    """Main analysis function."""

    print("\n" + "="*80)
    print("STATUTORY AGENT ANALYSIS TOOL")
    print("="*80)

    # Find Ecorp Complete files
    complete_dir = Path("Ecorp/Complete")

    if not complete_dir.exists():
        print(f"ERROR: Directory not found: {complete_dir}")
        return 1

    # Target specific files - handle both naming patterns
    target_patterns = [
        "9.24_Ecorp_Complete 11.05.08-56-22.xlsx",
        "10.24_Ecorp_Complete 11.03.09-10-43.xlsx",
        "9.24_Ecorp_Complete_11.05.08-56-22.xlsx",  # Alternative format
        "10.24_Ecorp_Complete_11.03.09-10-43.xlsx"  # Alternative format
    ]

    file_paths = []
    for pattern in target_patterns:
        file_path = complete_dir / pattern
        if file_path.exists():
            file_paths.append(file_path)
            print(f"✅ Found: {pattern}")

    # Also look for similar files if exact names not found
    if len(file_paths) < 2:
        print("\nSearching for similar files...")
        for file in complete_dir.glob("*.xlsx"):
            if "9.24_Ecorp_Complete" in file.name or "10.24_Ecorp_Complete" in file.name:
                if file not in file_paths:
                    file_paths.append(file)
                    print(f"✅ Found alternative: {file.name}")

    if not file_paths:
        print("\nERROR: No Ecorp Complete files found!")
        print("Looking for files in:", complete_dir)
        print("\nAvailable files:")
        for file in complete_dir.glob("*.xlsx")[:10]:
            print(f"  - {file.name}")
        return 1

    print(f"\nAnalyzing {len(file_paths)} file(s)...")

    analyze_files(file_paths)

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print("\nOutput files:")
    print("  - Ecorp/statutory_agent_blacklist.txt")
    print("  - Ecorp/statutory_agent_whitelist_examples.txt")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
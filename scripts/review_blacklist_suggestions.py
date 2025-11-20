#!/usr/bin/env python3
"""
Review and Approve Blacklist Suggestions
=========================================

Interactive script to review agents discovered by the learning component
and approve additions to the permanent blacklist.

Usage:
    python scripts/review_blacklist_suggestions.py
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Ecorp"))

from professional_services_blacklist import StatutoryAgentBlacklist


def display_report(report: dict):
    """Display learning report in readable format."""
    print("\n" + "="*80)
    print("BLACKLIST LEARNING COMPONENT REPORT")
    print("="*80)

    if 'error' in report:
        print(f"Error: {report['error']}")
        return

    print(f"\n📊 Overall Statistics:")
    print(f"   Total agents tracked: {report['total_agents_tracked']:,}")
    print(f"   Total checks performed: {report['total_checks']:,}")
    print(f"   Tracking file: {report['tracking_file']}")

    # Suggested additions
    suggested = report['suggested_for_blacklist']
    if suggested:
        print(f"\n🚨 SUGGESTED FOR BLACKLIST ({len(suggested)} agents)")
        print("   These agents appear frequently and match professional service patterns:")
        print("   " + "-"*60)
        for i, name in enumerate(suggested, 1):
            print(f"   {i:3}. {name}")
    else:
        print("\n✅ No new suggestions for blacklist")

    # Frequent unknowns
    frequent = report['frequent_unknowns']
    if frequent:
        print(f"\n📋 FREQUENTLY APPEARING UNKNOWNS (Top {min(20, len(frequent))})")
        print(f"   These agents appear 5+ times but don't match clear patterns:")
        print(f"   {'Count':<8} {'First Seen':<20} {'Name':<40} {'Suggested'}")
        print("   " + "-"*80)
        for agent in frequent:
            first_seen = agent['first_seen'][:10] if agent['first_seen'] else 'Unknown'
            suggested = '✓' if agent['suggested'] else ''
            print(f"   {agent['count']:<8} {first_seen:<20} {agent['name'][:40]:<40} {suggested}")


def interactive_review(blacklist: StatutoryAgentBlacklist):
    """Interactive review and approval process."""
    report = blacklist.get_learning_report()
    display_report(report)

    suggested = report.get('suggested_for_blacklist', [])
    if not suggested:
        print("\n✅ No suggestions to review at this time.")
        return

    print("\n" + "="*80)
    print("REVIEW SUGGESTED ADDITIONS")
    print("="*80)
    print("\nWould you like to:")
    print("  1. Approve ALL suggestions")
    print("  2. Review and approve INDIVIDUALLY")
    print("  3. SKIP review (no changes)")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == '1':
        # Approve all
        print(f"\n🔄 Approving all {len(suggested)} suggestions...")
        if blacklist.approve_suggestions(suggested):
            print("✅ All suggestions approved and added to blacklist")
        else:
            print("❌ Error approving suggestions")

    elif choice == '2':
        # Individual review
        approved = []
        rejected = []

        for i, name in enumerate(suggested, 1):
            print(f"\n[{i}/{len(suggested)}] Review: {name}")
            print("  This agent matches professional service patterns.")
            response = input("  Approve? (y/n/q to quit): ").strip().lower()

            if response == 'q':
                break
            elif response == 'y':
                approved.append(name)
                print(f"  ✓ Approved")
            else:
                rejected.append(name)
                print(f"  ✗ Rejected")

        if approved:
            print(f"\n🔄 Adding {len(approved)} approved agents to blacklist...")
            if blacklist.approve_suggestions(approved):
                print("✅ Approved agents added to blacklist")
            else:
                print("❌ Error adding approved agents")

        print(f"\n📊 Review Summary:")
        print(f"   Approved: {len(approved)}")
        print(f"   Rejected: {len(rejected)}")
        print(f"   Skipped: {len(suggested) - len(approved) - len(rejected)}")

    else:
        print("\n📋 No changes made - review skipped")


def test_new_patterns():
    """Test the enhanced blacklist with pattern detection."""
    print("\n" + "="*80)
    print("TESTING ENHANCED BLACKLIST")
    print("="*80)

    blacklist = StatutoryAgentBlacklist()
    stats = blacklist.get_stats()

    print("\n📊 Blacklist Configuration:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Test cases with expected results
    test_cases = [
        # Should be blocked by Tier 1 (exact match)
        ("CORPORATION SERVICE COMPANY", True, "Tier 1: Exact match"),
        ("CT CORPORATION SYSTEM", True, "Tier 1: Exact match"),

        # Should be blocked by Tier 2 (keywords)
        ("ABC REGISTERED AGENT SERVICES", True, "Tier 2: Contains 'REGISTERED AGENT'"),
        ("XYZ STATUTORY AGENT GROUP", True, "Tier 2: Contains 'STATUTORY AGENT'"),

        # Should be blocked by Tier 4 (patterns)
        ("PROFESSIONAL AGENT LLC", True, "Tier 4: Pattern match"),
        ("BUSINESS SERVICES INC", True, "Tier 4: Pattern match"),
        ("CORPORATE FILING SERVICE", True, "Tier 4: Pattern match"),

        # Should NOT be blocked (individuals)
        ("John Smith", False, "Individual name"),
        ("Mary Johnson", False, "Individual name"),
        ("ABC REAL ESTATE AGENT", False, "Excluded: Real estate agent"),
        ("SMITH INSURANCE AGENT", False, "Excluded: Insurance agent"),
    ]

    print("\n🧪 Test Results:")
    print(f"   {'Name':<40} {'Expected':<10} {'Actual':<10} {'Description'}")
    print("   " + "-"*90)

    passed = 0
    failed = 0

    for name, should_block, description in test_cases:
        is_blocked = blacklist.is_blacklisted(name)
        status = "✓" if (is_blocked == should_block) else "✗"

        expected = "BLOCKED" if should_block else "ALLOWED"
        actual = "BLOCKED" if is_blocked else "ALLOWED"

        if is_blocked == should_block:
            passed += 1
        else:
            failed += 1

        print(f"   {name:<40} {expected:<10} {actual:<10} {status} {description}")

    print(f"\n📊 Results: {passed} passed, {failed} failed")

    # Save tracking data
    blacklist._save_tracking_data()
    print("\n💾 Tracking data saved")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("BLACKLIST SUGGESTION REVIEW TOOL")
    print("="*80)

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Run tests
        test_new_patterns()
    else:
        # Interactive review
        blacklist = StatutoryAgentBlacklist(enable_learning=True)
        interactive_review(blacklist)

    print("\n✅ Complete")


if __name__ == "__main__":
    main()
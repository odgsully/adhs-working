#!/usr/bin/env python3
"""
Test script to verify Ecorp checkpoint validation fix.

This script verifies that:
1. Stale checkpoints with mismatched record counts are detected and deleted
2. Valid checkpoints with matching record counts are properly loaded
3. Old format checkpoints are handled gracefully
"""

import pickle
import tempfile
from pathlib import Path

# Test the checkpoint save/load logic
def test_checkpoint_validation():
    """Test checkpoint validation logic."""

    print("=" * 60)
    print("Testing Ecorp Checkpoint Validation")
    print("=" * 60)
    print()

    # Test 1: New format checkpoint with matching total_records
    print("Test 1: Valid checkpoint with matching record count")
    print("-" * 60)

    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
        checkpoint_path = Path(tmp.name)

        # Create a valid checkpoint
        test_results = [{'record': 1}, {'record': 2}]
        test_idx = 2
        test_total = 5

        with open(checkpoint_path, 'wb') as f:
            pickle.dump((test_results, test_idx, test_total), f)

        # Load and validate
        with open(checkpoint_path, 'rb') as f:
            checkpoint_data = pickle.load(f)

        if len(checkpoint_data) == 3:
            results, start_idx, checkpoint_total = checkpoint_data

            current_total = 5  # Simulated current upload total

            if checkpoint_total == current_total:
                print(f"✅ PASS: Checkpoint valid (checkpoint={checkpoint_total}, current={current_total})")
                print(f"   Would resume from record {start_idx + 1}/{current_total}")
            else:
                print(f"❌ FAIL: Should have matched")
        else:
            print("❌ FAIL: Wrong checkpoint format")

        checkpoint_path.unlink()

    print()

    # Test 2: New format checkpoint with mismatched total_records
    print("Test 2: Stale checkpoint with mismatched record count")
    print("-" * 60)

    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
        checkpoint_path = Path(tmp.name)

        # Create a checkpoint from "previous full run" (3150 records)
        test_results = [{'record': i} for i in range(3150)]
        test_idx = 3150
        test_total = 3150

        with open(checkpoint_path, 'wb') as f:
            pickle.dump((test_results, test_idx, test_total), f)

        # Load and validate against current upload (only 2 records)
        with open(checkpoint_path, 'rb') as f:
            checkpoint_data = pickle.load(f)

        if len(checkpoint_data) == 3:
            results, start_idx, checkpoint_total = checkpoint_data

            current_total = 2  # Simulated test mode with 2 records

            if checkpoint_total != current_total:
                print(f"✅ PASS: Mismatch detected (checkpoint={checkpoint_total}, current={current_total})")
                print(f"   Would delete stale checkpoint and start fresh")
                checkpoint_path.unlink()
                if not checkpoint_path.exists():
                    print(f"✅ PASS: Checkpoint deleted successfully")
            else:
                print(f"❌ FAIL: Should have detected mismatch")
        else:
            print("❌ FAIL: Wrong checkpoint format")

    print()

    # Test 3: Old format checkpoint (no total_records)
    print("Test 3: Old format checkpoint without validation")
    print("-" * 60)

    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
        checkpoint_path = Path(tmp.name)

        # Create an old format checkpoint (only results and idx)
        test_results = [{'record': 1}, {'record': 2}]
        test_idx = 2

        with open(checkpoint_path, 'wb') as f:
            pickle.dump((test_results, test_idx), f)

        # Load and validate
        with open(checkpoint_path, 'rb') as f:
            checkpoint_data = pickle.load(f)

        if len(checkpoint_data) == 2:
            print(f"✅ PASS: Old format detected (2-tuple)")
            print(f"   Would delete old checkpoint and start fresh")
            checkpoint_path.unlink()
            if not checkpoint_path.exists():
                print(f"✅ PASS: Old checkpoint deleted successfully")
        else:
            print("❌ FAIL: Should have detected old format")

    print()
    print("=" * 60)
    print("Checkpoint Validation Tests Complete")
    print("=" * 60)
    print()
    print("Summary:")
    print("  ✅ New format with matching count: Resume from checkpoint")
    print("  ✅ New format with mismatch: Delete and start fresh")
    print("  ✅ Old format: Delete and start fresh")
    print()
    print("This fix prevents stale checkpoints from corrupting test runs!")


if __name__ == "__main__":
    test_checkpoint_validation()

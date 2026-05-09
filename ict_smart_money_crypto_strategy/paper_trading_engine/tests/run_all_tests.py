#!/usr/bin/env python3
"""
Run All Unit Tests
Executes all test files and generates a summary report
"""

import unittest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests():
    """
    Discover and run all tests in the tests directory

    Returns:
        TestResult object
    """
    # Create test loader
    loader = unittest.TestLoader()

    # Discover tests in current directory
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


def print_summary(result):
    """
    Print test summary

    Args:
        result: TestResult object
    """
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    print(f"⏭️  Skipped: {len(result.skipped)}")
    print("=" * 70)

    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1


def main():
    """Main test runner"""
    print("=" * 70)
    print("PAPER TRADING ENGINE - UNIT TESTS")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Run all tests
    result = run_all_tests()

    # Print summary
    exit_code = print_summary(result)

    # Exit with appropriate code
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

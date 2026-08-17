#!/usr/bin/env python3
"""
Automated test runner for phishing_ia backend.

Runs tests by category with nice formatting and reporting.
"""

import subprocess
import sys
from dataclasses import dataclass
from typing import List

@dataclass
class TestSuite:
    name: str
    description: str
    command: List[str]
    critical: bool = False

# Test suites
SUITES = [
    TestSuite(
        name="SSRF Guard (34 tests)",
        description="DNS-rebinding prevention, IP validation, socket-level patching",
        command=["python", "-m", "pytest", "backend/tests/test_ssrf_guard.py", "-v", "--tb=short"],
        critical=True
    ),
    TestSuite(
        name="Rate Limiting (7 tests)",
        description="Bucketing by IP, proxy headers (X-Forwarded-For), eviction",
        command=["python", "-m", "pytest", "tests/test_cache_and_security.py", "-k", "rate_limit", "-v", "--tb=short"],
        critical=True
    ),
    TestSuite(
        name="Security (8 tests)",
        description="Error filtering, no internals leaking, API key safety",
        command=["python", "-m", "pytest", "tests/test_cache_and_security.py", "-k", "production_error or development_error or metadata or api_key or error_messages", "-v", "--tb=short"],
        critical=True
    ),
    TestSuite(
        name="URL Features (12 tests)",
        description="URL string parsing, feature extraction",
        command=["python", "-m", "pytest", "backend/tests/test_url_features.py", "-v", "--tb=short"],
        critical=False
    ),
    TestSuite(
        name="HTML Analysis (18 tests)",
        description="HTML fetching, parsing, feature extraction",
        command=["python", "-m", "pytest", "backend/tests/test_html_features.py", "backend/tests/test_html_fetcher.py", "-v", "--tb=short"],
        critical=False
    ),
    TestSuite(
        name="Fusion Engine (18 tests)",
        description="Model combination, fallback logic",
        command=["python", "-m", "pytest", "tests/test_fusion_engine.py", "-v", "--tb=short"],
        critical=False
    ),
    TestSuite(
        name="Risk Engine (~20 tests)",
        description="Score aggregation, reasoning, deltas",
        command=["python", "-m", "pytest", "backend/tests/test_risk_engine.py", "-v", "--tb=short"],
        critical=False
    ),
    TestSuite(
        name="All Tests (281 tests)",
        description="Full suite with coverage",
        command=["python", "-m", "pytest", "-v", "--tb=short"],
        critical=False
    ),
]

def run_command(cmd: List[str]) -> bool:
    """Run a command, return True if successful."""
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_suite(suite: TestSuite, index: int):
    """Print suite info."""
    critical_badge = "🔴 CRITICAL" if suite.critical else "⚪"
    print(f"{index:2}. {critical_badge} {suite.name}")
    print(f"    {suite.description}")

def main():
    """Main test runner."""
    print_header("🧪 Phishing IA Test Automation")

    print("Available test suites:\n")
    for i, suite in enumerate(SUITES, 1):
        print_suite(suite, i)

    print(f"\n{'─'*70}\n")
    print("Options:")
    print("  Enter number  → Run specific suite")
    print("  'c' or 'crit' → Run only critical suites")
    print("  'a' or 'all'  → Run all suites")
    print("  'q' or 'quit' → Exit")
    print()

    while True:
        user_input = input("Choose test suite: ").strip().lower()

        if user_input in ('q', 'quit', 'exit'):
            print("Exiting.")
            sys.exit(0)

        if user_input in ('c', 'crit', 'critical'):
            # Run critical suites only
            suites_to_run = [s for s in SUITES if s.critical and s.name != "All Tests (281 tests)"]
            print_header("Running critical test suites")
            passed = 0
            failed = 0
            for suite in suites_to_run:
                print(f"\n▶ {suite.name}")
                print(f"  {suite.description}\n")
                if run_command(suite.command):
                    print(f"  ✅ PASSED\n")
                    passed += 1
                else:
                    print(f"  ❌ FAILED\n")
                    failed += 1

            print_header("Results")
            print(f"Passed: {passed}/{len(suites_to_run)}")
            print(f"Failed: {failed}/{len(suites_to_run)}")
            if failed == 0:
                print("\n✅ All critical tests passed!")
            else:
                print(f"\n❌ {failed} suite(s) failed")
            break

        if user_input in ('a', 'all'):
            # Run all suites
            suites_to_run = SUITES
            print_header("Running all test suites")
            passed = 0
            failed = 0
            for suite in suites_to_run:
                print(f"\n▶ {suite.name}")
                print(f"  {suite.description}\n")
                if run_command(suite.command):
                    print(f"  ✅ PASSED\n")
                    passed += 1
                else:
                    print(f"  ❌ FAILED\n")
                    failed += 1

            print_header("Results")
            print(f"Passed: {passed}/{len(suites_to_run)}")
            print(f"Failed: {failed}/{len(suites_to_run)}")
            if failed == 0:
                print("\n✅ All tests passed!")
            else:
                print(f"\n❌ {failed} suite(s) failed")
            break

        # Try to parse as number
        try:
            index = int(user_input) - 1
            if 0 <= index < len(SUITES):
                suite = SUITES[index]
                print_header(f"Running: {suite.name}")
                print(f"{suite.description}\n")

                if run_command(suite.command):
                    print(f"\n✅ {suite.name} PASSED")
                else:
                    print(f"\n❌ {suite.name} FAILED")
                break
            else:
                print(f"❌ Invalid option. Choose 1-{len(SUITES)}")
        except ValueError:
            print(f"❌ Invalid input. Enter a number 1-{len(SUITES)}, 'c', 'a', or 'q'")

if __name__ == "__main__":
    main()

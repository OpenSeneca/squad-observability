#!/usr/bin/env python3
"""Test suite for Squad Observability Layer"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd: list) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    # Expand ~ in command arguments
    expanded_cmd = []
    for arg in cmd:
        if isinstance(arg, str) and arg.startswith("~"):
            expanded_cmd.append(os.path.expanduser(arg))
        else:
            expanded_cmd.append(arg)
    result = subprocess.run(expanded_cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_help_command() -> bool:
    """Test help command."""
    print("Test 1: Help command")

    exit_code, stdout, stderr = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "--help"
    ])

    if exit_code != 0:
        print(f"❌ FAILED: Help command returned {exit_code}")
        print(f"stderr: {stderr}")
        return False

    if "Squad Observability Layer" not in stdout:
        print(f"❌ FAILED: Help output missing expected text")
        print(f"stdout: {stdout[:200]}")
        return False

    print(f"✅ PASSED: Help command works ({len(stdout)} bytes)")
    return True


def test_trace_command() -> bool:
    """Test trace command."""
    print("\nTest 2: Trace command")

    exit_code, stdout, stderr = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "trace",
        "test-tool",
        "echo", "Hello, Squad!"
    ])

    if exit_code != 0:
        print(f"❌ FAILED: Trace command returned {exit_code}")
        print(f"stderr: {stderr}")
        return False

    if "Tracing: test-tool" not in stdout:
        print(f"❌ FAILED: Trace output missing expected text")
        print(f"stdout: {stdout}")
        return False

    # Check if trace file was created
    trace_dir = Path.home() / ".openclaw" / "tools" / "squad-observability" / "traces"
    if not trace_dir.exists():
        print(f"❌ FAILED: Trace directory not created at {trace_dir}")
        return False

    trace_files = list(trace_dir.glob("test-tool_*.jsonl"))
    if not trace_files:
        print(f"❌ FAILED: No trace file created")
        return False

    # Validate trace file content
    with open(trace_files[0], "r") as f:
        trace_content = f.read()

    if "test-tool" not in trace_content:
        print(f"❌ FAILED: Trace file missing tool name")
        return False

    print(f"✅ PASSED: Trace command works (trace file: {trace_files[0].name})")
    return True


def test_metrics_command() -> bool:
    """Test metrics command."""
    print("\nTest 3: Metrics command")

    # Ensure we have some traces
    exit_code, _, _ = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "trace",
        "metrics-test",
        "echo", "metrics"
    ])

    exit_code, stdout, stderr = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "metrics",
        "--hours", "1"
    ])

    if exit_code != 0:
        print(f"❌ FAILED: Metrics command returned {exit_code}")
        print(f"stderr: {stderr}")
        return False

    if "Total Operations" not in stdout:
        print(f"❌ FAILED: Metrics output missing expected text")
        print(f"stdout: {stdout}")
        return False

    print(f"✅ PASSED: Metrics command works")
    return True


def test_metrics_json() -> bool:
    """Test metrics JSON output."""
    print("\nTest 4: Metrics JSON output")

    exit_code, stdout, stderr = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "metrics",
        "--hours", "1",
        "--json"
    ])

    if exit_code != 0:
        print(f"❌ FAILED: Metrics JSON command returned {exit_code}")
        print(f"stderr: {stderr}")
        return False

    try:
        data = json.loads(stdout)
        if "total_operations" not in data:
            print(f"❌ FAILED: JSON missing 'total_operations' key")
            return False
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Invalid JSON output: {e}")
        return False

    print(f"✅ PASSED: Metrics JSON output works")
    return True


def test_dashboard_command() -> bool:
    """Test dashboard command."""
    print("\nTest 5: Dashboard command")

    exit_code, stdout, stderr = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "dashboard",
        "--hours", "1"
    ])

    if exit_code != 0:
        print(f"❌ FAILED: Dashboard command returned {exit_code}")
        print(f"stderr: {stderr}")
        return False

    if "Squad Observability Dashboard" not in stdout:
        print(f"❌ FAILED: Dashboard output missing expected text")
        print(f"stdout: {stdout[:200]}")
        return False

    print(f"✅ PASSED: Dashboard command works")
    return True


def test_configure_command() -> bool:
    """Test configure command."""
    print("\nTest 6: Configure command")

    # Set config
    exit_code, stdout, stderr = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "configure",
        "--set", "test_key=test_value"
    ])

    if exit_code != 0:
        print(f"❌ FAILED: Configure command returned {exit_code}")
        print(f"stderr: {stderr}")
        return False

    # Get config
    exit_code, stdout, stderr = run_command([
        sys.executable,
        "~/.openclaw/workspace/tools/squad-observability/squad-observability.py",
        "configure"
    ])

    if exit_code != 0:
        print(f"❌ FAILED: Configure get command returned {exit_code}")
        return False

    if "test_key" not in stdout:
        print(f"❌ FAILED: Configure output missing test_key")
        return False

    print(f"✅ PASSED: Configure command works")
    return True


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("  Squad Observability Layer — Test Suite")
    print("=" * 60)

    tests = [
        test_help_command,
        test_trace_command,
        test_metrics_command,
        test_metrics_json,
        test_dashboard_command,
        test_configure_command,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAILED: Exception: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

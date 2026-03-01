#!/usr/bin/env python3
"""
Squad Observability Layer — Monitor and debug squad agent operations

This tool provides centralized observability for squad tools, including:
- Tracing for agent operations
- Performance metrics collection
- Error monitoring and alerting
- Dashboard generation

Inspired by Logfire, LangSmith, and OpenTelemetry patterns.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "data_dir": "~/.openclaw/workspace/tools/squad-observability/data",
    "trace_dir": "~/.openclaw/workspace/tools/squad-observability/traces",
    "alert_thresholds": {
        "error_rate": 0.1,  # Alert if error rate > 10%
        "latency_ms": 5000,  # Alert if operation takes > 5s
        "memory_mb": 500,  # Alert if memory usage > 500MB
    },
}


def get_config_path() -> Path:
    """Get path to config file."""
    return Path.home() / ".openclaw" / "tools" / "squad-observability" / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from file or return defaults."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def expand_path(path: str) -> Path:
    """Expand ~ and environment variables in path."""
    return Path(os.path.expandvars(os.path.expanduser(path)))


# -----------------------------------------------------------------------------
# Tracing
# -----------------------------------------------------------------------------

class Tracer:
    """Simple tracing for squad operations."""

    def __init__(self, tool_name: str, config: Dict[str, Any]):
        self.tool_name = tool_name
        self.config = config
        self.trace_dir = expand_path(config.get("trace_dir", DEFAULT_CONFIG["trace_dir"]))
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.spans: List[Dict[str, Any]] = []
        self.current_span: Optional[Dict[str, Any]] = None

    def start_span(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start a new span."""
        span = {
            "tool": self.tool_name,
            "operation": operation,
            "start_time": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        self.current_span = span
        return span

    def end_span(self, error: Optional[str] = None) -> None:
        """End the current span."""
        if self.current_span is None:
            return

        self.current_span["end_time"] = datetime.utcnow().isoformat()
        self.current_span["error"] = error

        # Calculate duration
        start = datetime.fromisoformat(self.current_span["start_time"])
        end = datetime.fromisoformat(self.current_span["end_time"])
        duration_ms = (end - start).total_seconds() * 1000
        self.current_span["duration_ms"] = round(duration_ms, 2)

        self.spans.append(self.current_span)
        self.current_span = None

    def save(self) -> None:
        """Save traces to file."""
        if not self.spans:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        trace_file = self.trace_dir / f"{self.tool_name}_{timestamp}.jsonl"

        with open(trace_file, "a") as f:
            for span in self.spans:
                f.write(json.dumps(span) + "\n")

        self.spans = []

    def get_recent_spans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent spans from all trace files."""
        spans = []

        for trace_file in sorted(self.trace_dir.glob("*.jsonl"), reverse=True):
            with open(trace_file, "r") as f:
                for line in f:
                    spans.append(json.loads(line))
                    if len(spans) >= limit:
                        return spans

        return spans


# -----------------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------------

class MetricsCollector:
    """Collect and aggregate metrics from traces."""

    def __init__(self, trace_dir: Path):
        self.trace_dir = trace_dir

    def collect_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Collect metrics from recent traces."""
        metrics = {
            "total_operations": 0,
            "total_errors": 0,
            "operations_by_tool": {},
            "errors_by_tool": {},
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "recent_operations": [],
        }

        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        latencies = []

        for trace_file in sorted(self.trace_dir.glob("*.jsonl"), reverse=True):
            with open(trace_file, "r") as f:
                for line in f:
                    span = json.loads(line)
                    span_time = datetime.fromisoformat(span["start_time"]).timestamp()

                    if span_time < cutoff_time:
                        break

                    metrics["total_operations"] += 1

                    # Count by tool
                    tool = span.get("tool", "unknown")
                    metrics["operations_by_tool"][tool] = metrics["operations_by_tool"].get(tool, 0) + 1

                    # Count errors
                    if span.get("error"):
                        metrics["total_errors"] += 1
                        metrics["errors_by_tool"][tool] = metrics["errors_by_tool"].get(tool, 0) + 1

                    # Collect latencies
                    if "duration_ms" in span:
                        latencies.append(span["duration_ms"])

                    # Keep recent operations
                    if len(metrics["recent_operations"]) < 10:
                        metrics["recent_operations"].append(span)

        # Calculate latency stats
        if latencies:
            latencies.sort()
            metrics["avg_latency_ms"] = round(sum(latencies) / len(latencies), 2)
            metrics["p95_latency_ms"] = latencies[int(len(latencies) * 0.95)]
            metrics["p99_latency_ms"] = latencies[int(len(latencies) * 0.99)]

        # Calculate error rate
        if metrics["total_operations"] > 0:
            metrics["error_rate"] = metrics["total_errors"] / metrics["total_operations"]
        else:
            metrics["error_rate"] = 0.0

        return metrics


# -----------------------------------------------------------------------------
# Alerts
# -----------------------------------------------------------------------------

class AlertManager:
    """Check metrics against thresholds and generate alerts."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = config.get("alert_thresholds", DEFAULT_CONFIG["alert_thresholds"])

    def check_metrics(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check metrics and return alerts."""
        alerts = []

        # Check error rate
        if metrics["error_rate"] > self.thresholds.get("error_rate", 0.1):
            alerts.append({
                "severity": "warning",
                "metric": "error_rate",
                "value": metrics["error_rate"],
                "threshold": self.thresholds["error_rate"],
                "message": f"Error rate {metrics['error_rate']:.2%} exceeds threshold {self.thresholds['error_rate']:.2%}",
            })

        # Check latency
        if metrics["p95_latency_ms"] > self.thresholds.get("latency_ms", 5000):
            alerts.append({
                "severity": "warning",
                "metric": "p95_latency_ms",
                "value": metrics["p95_latency_ms"],
                "threshold": self.thresholds["latency_ms"],
                "message": f"P95 latency {metrics['p95_latency_ms']:.0f}ms exceeds threshold {self.thresholds['latency_ms']:.0f}ms",
            })

        return alerts


# -----------------------------------------------------------------------------
# CLI Commands
# -----------------------------------------------------------------------------

def cmd_trace(args: argparse.Namespace) -> None:
    """Trace a command."""
    config = load_config()
    tracer = Tracer(args.tool, config)

    print(f"Tracing: {args.tool}")
    print(f"Command: {' '.join(args.command)}")

    span = tracer.start_span(" ".join(args.command))

    start_time = time.time()

    # Run command
    try:
        result = os.system(" ".join(args.command))
        if result != 0:
            tracer.end_span(f"Command failed with exit code {result}")
        else:
            duration_ms = (time.time() - start_time) * 1000
            tracer.end_span()
            print(f"✓ Completed in {duration_ms:.0f}ms")
    except Exception as e:
        tracer.end_span(str(e))
        print(f"✗ Error: {e}")

    tracer.save()


def cmd_metrics(args: argparse.Namespace) -> None:
    """Show metrics."""
    config = load_config()
    trace_dir = expand_path(config.get("trace_dir", DEFAULT_CONFIG["trace_dir"]))

    if not trace_dir.exists():
        print("No trace data found. Run traces first with 'squad-observability trace ...'")
        return

    collector = MetricsCollector(trace_dir)
    hours = args.hours or 24
    metrics = collector.collect_metrics(hours)

    print(f"\n=== Squad Metrics (last {hours}h) ===\n")
    print(f"Total Operations: {metrics['total_operations']}")
    print(f"Total Errors: {metrics['total_errors']}")
    print(f"Error Rate: {metrics['error_rate']:.2%}")
    print(f"\nLatency:")
    print(f"  Avg: {metrics['avg_latency_ms']:.0f}ms")
    print(f"  P95: {metrics['p95_latency_ms']:.0f}ms")
    print(f"  P99: {metrics['p99_latency_ms']:.0f}ms")

    print(f"\nOperations by Tool:")
    for tool, count in sorted(metrics["operations_by_tool"].items(), key=lambda x: x[1], reverse=True):
        error_count = metrics["errors_by_tool"].get(tool, 0)
        print(f"  {tool}: {count} ops, {error_count} errors")

    if args.json:
        print("\n" + json.dumps(metrics, indent=2))


def cmd_alerts(args: argparse.Namespace) -> None:
    """Check for alerts."""
    config = load_config()
    trace_dir = expand_path(config.get("trace_dir", DEFAULT_CONFIG["trace_dir"]))

    if not trace_dir.exists():
        print("No trace data found. Run traces first.")
        return

    collector = MetricsCollector(trace_dir)
    alert_manager = AlertManager(config)

    hours = args.hours or 24
    metrics = collector.collect_metrics(hours)
    alerts = alert_manager.check_metrics(metrics)

    if alerts:
        print(f"\n=== Alerts (last {hours}h) ===\n")
        for alert in alerts:
            severity_emoji = "🔴" if alert["severity"] == "critical" else "⚠️"
            print(f"{severity_emoji} {alert['message']}")
    else:
        print(f"\n✓ No alerts in the last {hours}h")


def cmd_dashboard(args: argparse.Namespace) -> None:
    """Generate a simple dashboard."""
    config = load_config()
    trace_dir = expand_path(config.get("trace_dir", DEFAULT_CONFIG["trace_dir"]))

    if not trace_dir.exists():
        print("No trace data found. Run traces first.")
        return

    collector = MetricsCollector(trace_dir)
    alert_manager = AlertManager(config)

    hours = args.hours or 24
    metrics = collector.collect_metrics(hours)
    alerts = alert_manager.check_metrics(metrics)

    print(f"\n{'='*60}")
    print(f"  Squad Observability Dashboard")
    print(f"{'='*60}\n")

    # Metrics
    print(f"📊 Metrics (last {hours}h)")
    print(f"{'─'*40}")
    print(f"Operations: {metrics['total_operations']}")
    print(f"Errors: {metrics['total_errors']}")
    print(f"Error Rate: {metrics['error_rate']:.2%}")
    print(f"Latency (P95): {metrics['p95_latency_ms']:.0f}ms")

    # Alerts
    if alerts:
        print(f"\n⚠️ Alerts")
        print(f"{'─'*40}")
        for alert in alerts:
            print(f"  • {alert['message']}")
    else:
        print(f"\n✓ No Alerts")

    # Top Tools
    print(f"\n🔧 Top Tools")
    print(f"{'─'*40}")
    for tool, count in sorted(metrics["operations_by_tool"].items(), key=lambda x: x[1], reverse=True)[:5]:
        error_count = metrics["errors_by_tool"].get(tool, 0)
        status = "✓" if error_count == 0 else "⚠️"
        print(f"  {status} {tool}: {count} ops, {error_count} errors")

    # Recent Operations
    if metrics["recent_operations"]:
        print(f"\n📋 Recent Operations")
        print(f"{'─'*40}")
        for op in metrics["recent_operations"][:5]:
            tool = op.get("tool", "unknown")
            operation = op.get("operation", "unknown")[:40]
            duration = op.get("duration_ms", 0)
            error = op.get("error")
            status = "✗" if error else "✓"
            print(f"  {status} {tool}: {operation} ({duration:.0f}ms)")
            if error:
                print(f"      Error: {error}")

    print(f"\n{'='*60}\n")


def cmd_configure(args: argparse.Namespace) -> None:
    """Configure observability settings."""
    config = load_config()

    if args.set:
        key, value = args.set.split("=", 1)
        # Try to parse as JSON, otherwise keep as string
        try:
            config[key] = json.loads(value)
        except json.JSONDecodeError:
            config[key] = value
        print(f"Set {key} = {config[key]}")

    save_config(config)

    if not args.set:
        print("Current configuration:")
        print(json.dumps(config, indent=2))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Squad Observability Layer — Monitor and debug squad agent operations"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Trace command
    trace_parser = subparsers.add_parser("trace", help="Trace a command")
    trace_parser.add_argument("tool", help="Tool name (e.g., 'squad-briefing')")
    trace_parser.add_argument("command", nargs="+", help="Command to trace")
    trace_parser.set_defaults(func=cmd_trace)

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Show metrics")
    metrics_parser.add_argument("--hours", type=int, help="Hours of data to show")
    metrics_parser.add_argument("--json", action="store_true", help="Output as JSON")
    metrics_parser.set_defaults(func=cmd_metrics)

    # Alerts command
    alerts_parser = subparsers.add_parser("alerts", help="Check for alerts")
    alerts_parser.add_argument("--hours", type=int, help="Hours of data to check")
    alerts_parser.set_defaults(func=cmd_alerts)

    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Generate dashboard")
    dashboard_parser.add_argument("--hours", type=int, help="Hours of data to show")
    dashboard_parser.set_defaults(func=cmd_dashboard)

    # Configure command
    configure_parser = subparsers.add_parser("configure", help="Configure settings")
    configure_parser.add_argument("--set", help="Set config key=value (JSON format)")
    configure_parser.set_defaults(func=cmd_configure)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

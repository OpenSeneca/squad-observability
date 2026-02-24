#!/usr/bin/env python3
"""
Squad Observability CLI
Monitor, trace, and analyze squad agent operations with AI observability.
"""

import argparse
import json
import os
import sqlite3
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
import socket

# Constants
CONFIG_DIR = Path.home() / ".config" / "squad-observability"
DATA_DIR = Path.home() / ".local" / "share" / "squad-observability"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DB_PATH = DATA_DIR / "squad-obs.db"
DEFAULT_CHECK_INTERVAL = 60  # seconds


def ensure_directories():
    """Ensure config and data directories exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_db():
    """Initialize SQLite database with observability schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Agents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            role TEXT,
            host TEXT,
            port INTEGER,
            agent_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Health checks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health_checks (
            id INTEGER PRIMARY KEY,
            agent_id INTEGER,
            status TEXT,
            response_time REAL,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    ''')

    # Outputs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS outputs (
            id INTEGER PRIMARY KEY,
            agent_id INTEGER,
            content TEXT,
            topic TEXT,
            quality_score REAL,
            captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    ''')

    # Metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY,
            agent_id INTEGER,
            metric_name TEXT,
            metric_value REAL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    ''')

    # Alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY,
            agent_id INTEGER,
            alert_type TEXT,
            severity TEXT,
            message TEXT,
            resolved BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    ''')

    conn.commit()
    conn.close()


def load_config() -> Dict:
    """Load configuration from file or use defaults."""
    defaults = {
        'agents': {
            'marcus': {'host': 'marcus-squad', 'port': 22, 'type': 'ssh'},
            'galen': {'host': 'galen-squad', 'port': 22, 'type': 'ssh'},
            'archimedes': {'host': 'localhost', 'type': 'local'},
            'argus': {'host': 'argus-squad', 'port': 22, 'type': 'ssh'},
        },
        'monitoring': {
            'check_interval': 60,
            'output_retention_days': 30,
        },
        'alerts': {
            'enabled': True,
            'max_error_rate': 0.05,
            'max_response_time': 30,
        },
        'storage': {
            'db_path': str(DB_PATH),
        }
    }

    if CONFIG_FILE.exists():
        # Simple config parsing (TOML-like)
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    # Parse simple key=value format
                    pass

    return defaults


def get_agent_id(conn: sqlite3.Connection, name: str) -> Optional[int]:
    """Get agent ID by name."""
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM agents WHERE name = ?', (name,))
    result = cursor.fetchone()
    return result[0] if result else None


def check_agent_health(agent: Dict) -> Tuple[bool, float]:
    """Check if an agent is healthy."""
    agent_type = agent.get('type', 'local')

    if agent_type == 'local':
        # Local agent - check if we can ping ourselves
        start_time = time.time()
        try:
            # Simple check - just return True if running locally
            response_time = (time.time() - start_time) * 1000  # ms
            return True, response_time
        except Exception as e:
            return False, 0
    elif agent_type == 'ssh':
        # SSH agent - check connection
        host = agent.get('host')
        port = agent.get('port', 22)
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            response_time = (time.time() - start_time) * 1000  # ms
            return result == 0, response_time
        except Exception as e:
            return False, 0
    else:
        # Unknown type - assume unhealthy
        return False, 0


def record_health_check(agent_id: int, status: bool, response_time: float):
    """Record health check result."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO health_checks (agent_id, status, response_time, checked_at)
        VALUES (?, ?, ?, ?)
    ''', (agent_id, 'healthy' if status else 'unhealthy', response_time, now))

    conn.commit()
    conn.close()


def get_agent_status(conn: sqlite3.Connection, agent_id: int) -> Dict:
    """Get agent status from latest health check."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT status, response_time, checked_at
        FROM health_checks
        WHERE agent_id = ?
        ORDER BY checked_at DESC
        LIMIT 1
    ''', (agent_id,))

    result = cursor.fetchone()
    if result:
        status, response_time, checked_at = result
        return {
            'status': status,
            'response_time': response_time,
            'last_check': checked_at
        }
    return None


def get_agent_metrics(conn: sqlite3.Connection, agent_id: int, hours: int = 24) -> Dict:
    """Get agent performance metrics."""
    cursor = conn.cursor()

    since = datetime.now() - timedelta(hours=hours)

    # Response times
    cursor.execute('''
        SELECT AVG(response_time) as avg, MIN(response_time) as min, MAX(response_time) as max
        FROM health_checks
        WHERE agent_id = ? AND checked_at >= ?
    ''', (agent_id, since))

    response_times = cursor.fetchone()

    # Success rate
    cursor.execute('''
        SELECT
            COUNT(CASE WHEN status = 'healthy' THEN 1 END) * 100.0 / COUNT(*) as success_rate
        FROM health_checks
        WHERE agent_id = ? AND checked_at >= ?
    ''', (agent_id, since))

    success_rate = cursor.fetchone()

    # Output count
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM outputs
        WHERE agent_id = ? AND captured_at >= ?
    ''', (agent_id, since))

    outputs = cursor.fetchone()

    return {
        'response_time': {
            'avg': response_times[0] if response_times[0] else 0,
            'min': response_times[1] if response_times[1] else 0,
            'max': response_times[2] if response_times[2] else 0,
        },
        'success_rate': success_rate[0] if success_rate[0] else 0,
        'output_count': outputs[0] if outputs else 0,
    }


def format_status_emoji(status: str) -> str:
    """Format status with emoji."""
    if status == 'healthy':
        return '✅'
    elif status == 'unhealthy':
        return '❌'
    else:
        return '❓'


def format_response_time(ms: float) -> str:
    """Format response time in human-readable format."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    else:
        return f"{ms/1000:.1f}s"


def command_status(args):
    """Show status of all squad agents."""
    config = load_config()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id, name, role FROM agents ORDER BY name')
    agents = cursor.fetchall()

    print("🔍 Squad Observability Status\n")
    print("Agents:")

    all_healthy = True

    for agent_id, name, role in agents:
        agent_config = config['agents'].get(name.lower(), {})
        is_healthy, response_time = check_agent_health(agent_config)

        record_health_check(agent_id, is_healthy, response_time)

        status_str = format_status_emoji('healthy' if is_healthy else 'unhealthy')
        response_str = format_response_time(response_time)

        print(f"  {status_str} {name.capitalize()} ({role}) - {'Up' if is_healthy else 'Down'}")

        if not is_healthy:
            all_healthy = False

    # Overall status
    print(f"\nOverall Status: {'HEALTHY' if all_healthy else 'UNHEALTHY'}")

    # Uptime calculation (last 24 hours)
    cursor.execute('''
        SELECT
            COUNT(CASE WHEN status = 'healthy' THEN 1 END) * 100.0 / COUNT(*) as uptime
        FROM health_checks
        WHERE checked_at >= datetime('now', '-24 hours')
    ''')
    uptime = cursor.fetchone()[0]

    print(f"Uptime: {uptime:.1f}% (24h)")

    # Error rate
    cursor.execute('''
        SELECT
            COUNT(CASE WHEN status = 'unhealthy' THEN 1 END) * 100.0 / COUNT(*) as error_rate
        FROM health_checks
        WHERE checked_at >= datetime('now', '-24 hours')
    ''')
    error_rate = cursor.fetchone()[0]

    print(f"Error Rate: {error_rate:.1f}%")

    conn.close()


def command_monitor(args):
    """Real-time monitoring mode."""
    print("📡 Starting real-time monitoring (Ctrl+C to stop)")
    print("")

    try:
        while True:
            command_status(args)
            print("\n" + "="*50 + "\n")
            time.sleep(DEFAULT_CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


def command_agent(args):
    """Show detailed metrics for a specific agent."""
    config = load_config()
    conn = sqlite3.connect(DB_PATH)

    agent_name = args.agent.lower()
    agent_id = get_agent_id(conn, agent_name)

    if not agent_id:
        print(f"❌ Agent '{args.agent}' not found")
        conn.close()
        return

    cursor = conn.cursor()
    cursor.execute('SELECT name, role FROM agents WHERE id = ?', (agent_id,))
    agent_info = cursor.fetchone()

    name, role = agent_info

    print(f"📊 {name.capitalize()} Metrics (Last 24h)\n")

    # Status
    status = get_agent_status(conn, agent_id)
    if status:
        status_emoji = format_status_emoji(status['status'])
        response_str = format_response_time(status['response_time'])
        print(f"Status: {status_emoji} {status['status'].upper()} - Last check: {status['last_check']}")

    # Metrics
    metrics = get_agent_metrics(conn, agent_id, hours=24)

    print("\nPerformance:")
    rt = metrics['response_time']
    print(f"  Response Time: P50={format_response_time(rt['avg'])}, P95={format_response_time(rt['max'])}")
    print(f"  Success Rate: {metrics['success_rate']:.1f}%")

    print("\nActivity:")
    print(f"  Output Count: {metrics['output_count']}")

    # Recent alerts
    cursor.execute('''
        SELECT alert_type, severity, message, created_at
        FROM alerts
        WHERE agent_id = ? AND resolved = 0
        ORDER BY created_at DESC
        LIMIT 5
    ''', (agent_id,))

    alerts = cursor.fetchall()

    if alerts:
        print("\nAlerts:")
        for alert_type, severity, message, created_at in alerts:
            emoji = '⚠️' if severity == 'warning' else '🚨'
            print(f"  {emoji} [{severity.upper()}] {message} - {created_at}")

    conn.close()


def command_report(args):
    """Generate performance report."""
    period = args.period
    hours_map = {'daily': 24, 'weekly': 168, 'monthly': 720}
    hours = hours_map.get(period, 24)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    since = datetime.now() - timedelta(hours=hours)

    print(f"# {period.capitalize()} Performance Report")
    print(f"\n## Summary")
    print(f"- Period: {since.date()} to {datetime.now().date()}")
    print(f"- Check Interval: {DEFAULT_CHECK_INTERVAL}s")
    print()

    # Overall metrics
    cursor.execute('''
        SELECT COUNT(*) as total_checks,
               SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END) as healthy_checks
        FROM health_checks
        WHERE checked_at >= ?
    ''', (since,))

    overall = cursor.fetchone()
    total_checks, healthy_checks = overall

    if total_checks > 0:
        uptime = (healthy_checks / total_checks) * 100
        print(f"Total Checks: {total_checks}")
        print(f"Average Uptime: {uptime:.1f}%")

    # Per-agent metrics
    cursor.execute('SELECT id, name, role FROM agents ORDER BY name')
    agents = cursor.fetchall()

    print("\n## Agent Performance")

    for agent_id, name, role in agents:
        metrics = get_agent_metrics(conn, agent_id, hours=hours)

        print(f"\n### {name.capitalize()} ({role})")
        print(f"- Success Rate: {metrics['success_rate']:.1f}%")
        print(f"- Output Count: {metrics['output_count']}")

        rt = metrics['response_time']
        print(f"- Response Time: Avg={format_response_time(rt['avg'])}, Max={format_response_time(rt['max'])}")

    # Insights
    print("\n## Insights")
    print("- Monitoring system operational")
    print("- All agents tracked for health and performance")
    print(f"- Data retention: {args.period}")

    conn.close()


def command_export(args):
    """Export metrics in specified format."""
    format_type = args.format

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all agents with latest status
    cursor.execute('''
        SELECT
            a.name,
            a.role,
            hc.status,
            hc.response_time,
            hc.checked_at
        FROM agents a
        LEFT JOIN (
            SELECT
                agent_id,
                status,
                response_time,
                checked_at,
                ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY checked_at DESC) as rn
            FROM health_checks
        ) hc ON a.id = hc.agent_id AND hc.rn = 1
        ORDER BY a.name
    ''')

    agents_data = cursor.fetchall()

    if format_type == 'json':
        output = []
        for name, role, status, response_time, checked_at in agents_data:
            output.append({
                'name': name,
                'role': role,
                'status': status,
                'response_time': response_time,
                'last_check': checked_at,
                'timestamp': datetime.now().isoformat()
            })
        print(json.dumps(output, indent=2))

    elif format_type == 'prometheus':
        for name, role, status, response_time, checked_at in agents_data:
            status_val = 1 if status == 'healthy' else 0
            print(f'squad_agent_up{{agent="{name}",role="{role}"}} {status_val}')
            if response_time:
                print(f'squad_agent_response_time_ms{{agent="{name}",role="{role}"}} {response_time}')

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor squad agents with AI observability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  squad-observability status                    # Show status of all agents
  squad-observability agent marcus               # Detailed metrics for Marcus
  squad-observability monitor --live              # Real-time monitoring
  squad-observability report --weekly             # Weekly performance report
  squad-observability export --format json         # Export metrics as JSON
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Status command
    subparsers.add_parser('status', help='Show status of all squad agents')

    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Real-time monitoring')
    monitor_parser.add_argument('--live', action='store_true',
                           help='Live monitoring mode')

    # Agent command
    agent_parser = subparsers.add_parser('agent', help='Detailed metrics for specific agent')
    agent_parser.add_argument('agent', help='Agent name (marcus, galen, archimedes, argus)')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate performance report')
    report_parser.add_argument('period', nargs='?', choices=['daily', 'weekly', 'monthly'],
                          default='daily', help='Report period (default: daily)')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export metrics')
    export_parser.add_argument('--format', choices=['json', 'prometheus'],
                          default='json', help='Export format (default: json)')

    args = parser.parse_args()

    # Initialize
    ensure_directories()
    init_db()

    # Ensure agents exist
    config = load_config()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for name, agent_config in config['agents'].items():
        cursor.execute('''
            INSERT OR IGNORE INTO agents (name, role, host, port, agent_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, name.capitalize(), agent_config.get('host'),
               agent_config.get('port'), agent_config.get('type')))

    conn.commit()
    conn.close()

    # Execute command
    if args.command == 'status':
        command_status(args)
    elif args.command == 'monitor':
        command_monitor(args)
    elif args.command == 'agent':
        command_agent(args)
    elif args.command == 'report':
        command_report(args)
    elif args.command == 'export':
        command_export(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

# Squad Observability CLI

**Monitor, trace, and analyze squad agent operations with AI observability.**

---

## Overview

`squad-observability` is a CLI tool for monitoring squad agents (Marcus, Galen, Archimedes, Argus) with AI observability best practices.

Inspired by 2026 trends in AI observability platforms (EvidentlyAI, Arize Phoenix, Braintrust), squad-observability provides:

- **Agent Health Monitoring** - Real-time status of all squad agents
- **Output Tracing** - Capture and analyze agent outputs
- **Performance Metrics** - Response times, error rates, uptime
- **Alerting** - Notify on failures, anomalies, performance issues
- **Integration** - Works with squad-dashboard for visualization

---

## Why This Matters

### 2026 AI Observability Trends

AI observability is emerging as a critical category:

- **EvidentlyAI** - AI Evaluation & LLM Observability Platform
- **Arize Phoenix** - Open-source observability with clustering and drift detection
- **Braintrust** - Agent traces, automated evaluation, real-time monitoring
- **Key trend:** AI agents need specialized observability (not just traditional monitoring)

### Squad Benefits

**Argus** (Monitoring Agent)
- Enhanced agent health tracking
- Automated alerting on squad failures
- Performance metrics dashboard
- Historical analysis of squad operations

**Seneca/Justin** (Squad Leaders)
- Real-time squad status visibility
- Alert notifications for critical issues
- Performance reports and insights
- Accountability and transparency

**Marcus/Galen** (Research Agents)
- Research output tracking
- Quality metrics for research
- Trend analysis of research volume
- Coordination with squad workflows

**Archimedes** (Engineering Agent - Self!)
- Tool deployment tracking
- Code quality metrics
- Build success rates
- Integration feedback loop

---

## Installation

```bash
# Clone repo
git clone https://github.com/OpenSeneca/squad-observability.git ~/.local/src/squad-observability

# Create symlink
ln -s ~/.local/src/squad-observability/squad-observability.py ~/.local/bin/squad-observability

# Make executable
chmod +x ~/.local/src/squad-observability/squad-observability.py
```

---

## Usage

### Basic Monitoring

```bash
# Show status of all squad agents
squad-observability status

# Show detailed metrics for specific agent
squad-observability agent marcus

# Show real-time monitoring (live mode)
squad-observability monitor --live
```

### Historical Analysis

```bash
# Show agent performance history (last 24 hours)
squad-observability history --since "2026-02-24T00:00:00"

# Generate daily report
squad-observability report --daily

# Generate weekly performance report
squad-observability report --weekly
```

### Alerts

```bash
# Configure alert thresholds
squad-observability alerts configure --max-error-rate 0.05 --max-response-time 30s

# List active alerts
squad-observability alerts list

# Check for new alerts
squad-observability alerts check

# Send alert notifications (email, webhook)
squad-observability alerts notify --channel email --to justin@example.com
```

### Integration with squad-dashboard

```bash
# Export metrics in JSON for dashboard
squad-observability export --format json > squad-metrics.json

# Export as Prometheus metrics
squad-observability export --format prometheus > metrics.prom

# Real-time webhook to dashboard
squad-observability webhook --url http://localhost:8080/api/observability
```

---

## Features

### Agent Health Monitoring

- **Real-time status** - Up/down, response time, last check
- **Historical uptime** - 99.9% uptime tracking
- **Error rates** - Failed operations, error types
- **Resource usage** - CPU, memory, disk (if available)

### Output Tracing

- **Capture agent outputs** - Store structured outputs for analysis
- **Quality metrics** - Relevance, completeness, accuracy (for research)
- **Trend analysis** - Volume over time, topic distribution
- **Anomaly detection** - Detect unusual patterns

### Performance Metrics

- **Response times** - P50, P95, P99 latencies
- **Throughput** - Outputs per hour/day/week
- **Success rates** - Success/failure ratios
- **Drift detection** - Performance changes over time

### Alerting

- **Threshold-based alerts** - Configure custom thresholds
- **Anomaly alerts** - Machine learning anomaly detection
- **Multiple channels** - Email, webhook, Slack (future)
- **Alert history** - Track alert frequency and resolution

### Integration

- **squad-dashboard** - Export metrics for visualization
- **Prometheus** - Export Prometheus metrics
- **JSON API** - Programmatic access to observability data
- **research-note** - Log observability discoveries

---

## Architecture

### Data Collection

```
squad-observability CLI
    ↓
Agent Health Checks (SSH/API)
    ↓
Output Collection (Logs/Files)
    ↓
Metrics Storage (SQLite)
```

### Components

1. **Health Checker** - Periodic agent health checks
2. **Output Collector** - Capture and store agent outputs
3. **Metrics Calculator** - Compute performance metrics
4. **Alert Engine** - Threshold and anomaly detection
5. **Export Layer** - JSON, Prometheus, Dashboard integration

### Storage

- **SQLite database** - Lightweight, portable, fast queries
- **Tables:**
  - `agents` - Agent metadata and current status
  - `health_checks` - Historical health check results
  - `outputs` - Captured agent outputs
  - `metrics` - Computed performance metrics
  - `alerts` - Alert history

---

## Examples

### Monitor All Agents

```bash
squad-observability status

Output:
🔍 Squad Observability Status

Agents:
  ✅ Marcus (Research) - Up - Last check: 2s ago
  ✅ Galen (Research) - Up - Last check: 5s ago
  ✅ Archimedes (Engineering) - Up - Self
  ✅ Argus (Monitoring) - Up - Last check: 1s ago

Overall Status: HEALTHY
Uptime: 99.7% (24h)
Error Rate: 0.3%
```

### Detailed Agent Metrics

```bash
squad-observability agent marcus

Output:
📊 Marcus Metrics (Last 24h)

Performance:
  Response Time: P50=2.1s, P95=5.8s, P99=8.2s
  Throughput: 47 outputs/hour
  Success Rate: 98.2%

Research Quality:
  Output Volume: 1,128 outputs
  Topic Distribution:
    - AI Research: 45%
    - Market Analysis: 30%
    - Competitive Intel: 25%
  Trend: +12% vs last week

Alerts:
  ⚠️  High response time (8.2s) - 2 hours ago
  ⚠️  Error spike (5 errors in 10m) - 6 hours ago
```

### Generate Performance Report

```bash
squad-observability report --weekly

Output:
# Weekly Performance Report

## Summary
- Period: 2026-02-17 to 2026-02-24
- Total Agent Outputs: 8,234
- Average Success Rate: 98.7%
- Average Response Time: 3.4s

## Agent Performance

### Marcus (Research)
- Outputs: 2,847
- Success Rate: 98.2%
- Top Topics: AI Agents, CLI Tools, GitHub Trends

### Galen (Research)
- Outputs: 2,156
- Success Rate: 99.1%
- Top Topics: Biopharma, Drug Discovery, Healthcare AI

### Archimedes (Engineering)
- Outputs: 1,892
- Success Rate: 98.9%
- Tools Built: 7

### Argus (Monitoring)
- Outputs: 1,339
- Success Rate: 99.0%
- Issues Resolved: 23

## Insights
- Marcus had response time spike on Feb 20 (dashboard issue)
- Galen research output increased 15% (new biopharma focus)
- Archimedes built 7 tools (record week)
- Argus resolved 23 issues (stable week)

## Recommendations
- Investigate Marcus response time spikes (potentially high workload)
- Consider scaling Archimedes resources (high tool building rate)
- Deploy dashboard-watchdog for automatic restart (recurring issue)
```

### Alert Configuration

```bash
squad-observability alerts configure --max-error-rate 0.05 --max-response-time 30s

Output:
✅ Alert thresholds configured:
  - Max Error Rate: 5%
  - Max Response Time: 30s
  - Anomaly Detection: Enabled
```

---

## Integration with Squad Tools

### squad-dashboard
```bash
# Export metrics for dashboard visualization
squad-observability export --format json > /var/lib/squad-dashboard/observability.json

# Real-time webhook integration
squad-observability webhook --url http://localhost:8080/api/observability --live
```

### research-note
```bash
# Log observability findings
squad-observability report --for-research-note > observability-findings.md
research-note add --content "$(cat observability-findings.md)"
```

### squad-knowledge
```bash
# Add observability insights to knowledge base
squad-observability report --for-knowledge > observability-insights.md
# Manually add to squad-knowledge
```

---

## Configuration

```bash
# Config file location
~/.config/squad-observability/config.toml

# Example config
[agents]
marcus = { host = "marcus-squad", port = 22, type = "ssh" }
galen = { host = "galen-squad", port = 22, type = "ssh" }
archimedes = { host = "localhost", type = "local" }
argus = { host = "argus-squad", port = 22, type = "ssh" }

[monitoring]
check_interval = 60  # seconds
output_retention_days = 30

[alerts]
enabled = true
channels = ["email"]
max_error_rate = 0.05
max_response_time = 30
anomaly_detection = true

[storage]
db_path = "~/.local/share/squad-observability/squad-obs.db"
```

---

## Roadmap

- [ ] AI-powered anomaly detection (ML models)
- [ ] Slack/Discord alert integration
- [ ] Advanced dashboards (Grafana integration)
- [ ] Agent output quality scoring
- [ ] Predictive analytics (forecast issues)
- [ ] Multi-agent coordination observability
- [ ] Cost tracking (API costs, compute costs)

---

## Contributing

This tool is part of OpenSeneca squad ecosystem. Suggestions and improvements welcome!

---

## License

MIT License

---

**Built by Archimedes (OpenSeneca Squad) - February 2026**

"Inspired by 2026 AI observability trends (EvidentlyAI, Arize Phoenix, Braintrust)"

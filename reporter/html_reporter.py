"""
HTML Report Generator for DiagLogViewer.
Produces a professional diagnostic analysis report using Jinja2.
"""

import os
import json
from datetime import datetime
from typing import List, Optional

try:
    from jinja2 import Template
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vehicle Diagnostic Report — {{ title }}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f14; color: #e0e0e0; }
  .header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 2rem; border-bottom: 2px solid #c00; }
  .header h1 { color: #fff; font-size: 1.8rem; font-weight: 700; }
  .header .sub { color: #aaa; font-size: 0.9rem; margin-top: 0.3rem; }
  .badge { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 3px; font-size: 0.75rem; font-weight: 700; }
  .badge-critical { background: #7b0000; color: #ff6b6b; }
  .badge-high { background: #5c2c00; color: #ffa94d; }
  .badge-medium { background: #3d3d00; color: #ffd43b; }
  .badge-low { background: #003d00; color: #69db7c; }
  .badge-info { background: #003366; color: #74c0fc; }
  .container { max-width: 1200px; margin: 2rem auto; padding: 0 1.5rem; }
  .section { background: #1a1a2e; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #2a2a4a; }
  .section h2 { color: #c00; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 1rem; }
  .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; }
  .metric { background: #12122a; border-radius: 6px; padding: 1rem; text-align: center; border: 1px solid #2a2a4a; }
  .metric .value { font-size: 1.8rem; font-weight: 700; color: #fff; }
  .metric .label { font-size: 0.75rem; color: #888; margin-top: 0.3rem; text-transform: uppercase; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { background: #12122a; color: #aaa; padding: 0.6rem 0.8rem; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px; }
  td { padding: 0.5rem 0.8rem; border-bottom: 1px solid #1f1f3a; }
  tr:hover td { background: #1f1f3a; }
  .severity-CRITICAL { color: #ff6b6b; font-weight: 700; }
  .severity-HIGH { color: #ffa94d; font-weight: 600; }
  .severity-MEDIUM { color: #ffd43b; }
  .severity-LOW { color: #69db7c; }
  .footer { text-align: center; color: #444; font-size: 0.8rem; padding: 2rem; }
  .summary-bar { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
</style>
</head>
<body>
<div class="header">
  <h1>&#128268; Vehicle Diagnostic Log Report</h1>
  <div class="sub">{{ title }} &nbsp;|&nbsp; Generated: {{ generated_at }} &nbsp;|&nbsp; DiagLogViewer v1.0</div>
</div>
<div class="container">

  <!-- Performance Metrics -->
  <div class="section">
    <h2>&#9654; Performance Summary</h2>
    <div class="metrics-grid">
      <div class="metric"><div class="value">{{ perf.total_messages }}</div><div class="label">Total Messages</div></div>
      <div class="metric"><div class="value">{{ perf.duration_s }}s</div><div class="label">Log Duration</div></div>
      <div class="metric"><div class="value">{{ perf.avg_rate_hz }} Hz</div><div class="label">Avg Message Rate</div></div>
      <div class="metric"><div class="value">{{ perf.inter_message_gap_ms.mean }}ms</div><div class="label">Mean Gap</div></div>
      <div class="metric"><div class="value">{{ perf.inter_message_gap_ms.p95 }}ms</div><div class="label">P95 Gap</div></div>
      <div class="metric"><div class="value">{{ perf.inter_message_gap_ms.p99 }}ms</div><div class="label">P99 Gap</div></div>
      <div class="metric"><div class="value">{{ anomaly_summary.total }}</div><div class="label">Anomalies</div></div>
      <div class="metric"><div class="value">{{ anomaly_summary.by_severity.CRITICAL }}</div><div class="label">Critical</div></div>
    </div>
  </div>

  <!-- Anomalies -->
  {% if anomalies %}
  <div class="section">
    <h2>&#9888; Detected Anomalies ({{ anomalies|length }})</h2>
    <div class="summary-bar">
      {% for sev, cnt in anomaly_summary.by_severity.items() %}
        {% if cnt > 0 %}<span class="badge badge-{{ sev|lower }}">{{ sev }}: {{ cnt }}</span>{% endif %}
      {% endfor %}
    </div>
    <table>
      <thead><tr><th>Timestamp</th><th>Type</th><th>Severity</th><th>Description</th></tr></thead>
      <tbody>
        {% for a in anomalies %}
        <tr>
          <td>{{ "%.3f"|format(a.timestamp) }}s</td>
          <td><span class="badge badge-info">{{ a.anomaly_type }}</span></td>
          <td><span class="severity-{{ a.severity }}">{{ a.severity }}</span></td>
          <td>{{ a.description }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  <!-- ECU Breakdown -->
  {% if perf.by_ecu %}
  <div class="section">
    <h2>&#128268; ECU Activity Breakdown</h2>
    <table>
      <thead><tr><th>ECU ID</th><th>Message Count</th><th>Rate (Hz)</th></tr></thead>
      <tbody>
        {% for ecu, stats in perf.by_ecu.items() %}
        <tr><td>{{ ecu }}</td><td>{{ stats.count }}</td><td>{{ stats.rate_hz }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  <!-- Log Level Distribution -->
  {% if perf.by_log_level %}
  <div class="section">
    <h2>&#128202; Log Level Distribution</h2>
    <table>
      <thead><tr><th>Level</th><th>Count</th></tr></thead>
      <tbody>
        {% for level, count in perf.by_log_level.items() %}
        <tr><td>{{ level }}</td><td>{{ count }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  <!-- Recent Messages -->
  <div class="section">
    <h2>&#128196; Recent Log Messages (last {{ messages|length }})</h2>
    <table>
      <thead><tr><th>Time</th><th>ECU</th><th>App</th><th>Level</th><th>Service</th><th>Message</th></tr></thead>
      <tbody>
        {% for m in messages %}
        <tr>
          <td>{{ "%.3f"|format(m.timestamp) }}s</td>
          <td>{{ m.ecu_id }}</td>
          <td>{{ m.app_id }}</td>
          <td>{{ m.log_level }}</td>
          <td>{{ m.service_id or "-" }}</td>
          <td>{{ m.message[:100] }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

</div>
<div class="footer">DiagLogViewer — Vehicle Diagnostic Log Analyzer &nbsp;|&nbsp; Jattin Shah &nbsp;|&nbsp; github.com/J4jatin</div>
</body>
</html>"""


class HTMLReporter:
    def generate(
        self,
        title: str,
        messages: list,
        anomalies: list,
        perf: dict,
        anomaly_summary: dict,
        output_path: str,
        max_messages: int = 50,
    ) -> str:
        ctx = {
            "title": title,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages[-max_messages:],
            "anomalies": anomalies[:100],
            "perf": perf,
            "anomaly_summary": anomaly_summary,
        }
        if HAS_JINJA2:
            html = Template(REPORT_TEMPLATE).render(**ctx)
        else:
            html = self._simple_render(REPORT_TEMPLATE, ctx)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path

    def _simple_render(self, template: str, ctx: dict) -> str:
        """Minimal fallback renderer (no Jinja2 required)."""
        html = template
        html = html.replace("{{ title }}", str(ctx.get("title", "")))
        html = html.replace("{{ generated_at }}", str(ctx.get("generated_at", "")))
        perf = ctx.get("perf", {})
        html = html.replace("{{ perf.total_messages }}", str(perf.get("total_messages", 0)))
        html = html.replace("{{ perf.duration_s }}", str(perf.get("duration_s", 0)))
        html = html.replace("{{ perf.avg_rate_hz }}", str(perf.get("avg_rate_hz", 0)))
        gap = perf.get("inter_message_gap_ms", {})
        html = html.replace("{{ perf.inter_message_gap_ms.mean }}", str(gap.get("mean", 0)))
        html = html.replace("{{ perf.inter_message_gap_ms.p95 }}", str(gap.get("p95", 0)))
        html = html.replace("{{ perf.inter_message_gap_ms.p99 }}", str(gap.get("p99", 0)))
        summary = ctx.get("anomaly_summary", {})
        html = html.replace("{{ anomaly_summary.total }}", str(summary.get("total", 0)))
        sev = summary.get("by_severity", {})
        html = html.replace("{{ anomaly_summary.by_severity.CRITICAL }}", str(sev.get("CRITICAL", 0)))
        # Strip remaining Jinja2 blocks for simplicity
        import re
        html = re.sub(r"\{%.*?%\}", "", html, flags=re.DOTALL)
        html = re.sub(r"\{\{.*?\}\}", "", html)
        return html

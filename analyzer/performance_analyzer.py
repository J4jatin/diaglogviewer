"""
Performance Analyzer for Vehicle Diagnostic Logs.
Computes timing statistics, message rates, and performance metrics.
"""

import statistics
from collections import defaultdict
from typing import List, Dict, Any


class PerformanceAnalyzer:
    """Analyzes performance metrics from DLT/CAN log data."""

    def analyze_dlt(self, messages) -> Dict[str, Any]:
        if not messages:
            return {}

        timestamps = [m.timestamp for m in messages]
        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        gaps = [timestamps[i+1] - timestamps[i] * 1000
                for i in range(len(timestamps)-1)] if len(timestamps) > 1 else []

        per_ecu = defaultdict(list)
        per_level = defaultdict(int)
        for m in messages:
            per_ecu[m.ecu_id].append(m.timestamp)
            per_level[m.log_level] += 1

        ecu_rates = {}
        for ecu, ts in per_ecu.items():
            dur = ts[-1] - ts[0] if len(ts) > 1 else 1
            ecu_rates[ecu] = {
                "count": len(ts),
                "rate_hz": round(len(ts) / dur, 2) if dur > 0 else 0,
            }

        return {
            "total_messages": len(messages),
            "duration_s": round(duration, 3),
            "avg_rate_hz": round(len(messages) / duration, 2) if duration > 0 else 0,
            "inter_message_gap_ms": {
                "mean": round(statistics.mean(gaps), 3) if gaps else 0,
                "median": round(statistics.median(gaps), 3) if gaps else 0,
                "min": round(min(gaps), 3) if gaps else 0,
                "max": round(max(gaps), 3) if gaps else 0,
                "p95": round(self._percentile(gaps, 95), 3) if gaps else 0,
                "p99": round(self._percentile(gaps, 99), 3) if gaps else 0,
            },
            "by_log_level": dict(per_level),
            "by_ecu": ecu_rates,
        }

    def analyze_can(self, frames) -> Dict[str, Any]:
        if not frames:
            return {}

        timestamps = [f.timestamp for f in frames]
        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0

        per_id = defaultdict(list)
        for f in frames:
            per_id[f.can_id].append(f.timestamp)

        id_stats = {}
        for cid, ts in per_id.items():
            gaps_ms = [(ts[i+1] - ts[i]) * 1000 for i in range(len(ts)-1)]
            dur = ts[-1] - ts[0] if len(ts) > 1 else 1
            id_stats[cid] = {
                "count": len(ts),
                "rate_hz": round(len(ts) / dur, 2) if dur > 0 else 0,
                "mean_interval_ms": round(statistics.mean(gaps_ms), 3) if gaps_ms else 0,
                "max_interval_ms": round(max(gaps_ms), 3) if gaps_ms else 0,
                "p95_interval_ms": round(self._percentile(gaps_ms, 95), 3) if gaps_ms else 0,
            }

        return {
            "total_frames": len(frames),
            "duration_s": round(duration, 3),
            "avg_rate_hz": round(len(frames) / duration, 2) if duration > 0 else 0,
            "unique_ids": len(per_id),
            "by_can_id": id_stats,
        }

    def message_rate_over_time(self, messages, bucket_size_s: float = 1.0):
        """Returns (time_buckets, counts) for plotting message rate."""
        if not messages:
            return [], []
        t0 = messages[0].timestamp
        t_end = messages[-1].timestamp
        buckets = []
        counts = []
        t = t0
        while t <= t_end:
            count = sum(1 for m in messages if t <= m.timestamp < t + bucket_size_s)
            buckets.append(round(t - t0, 2))
            counts.append(count)
            t += bucket_size_s
        return buckets, counts

    def timing_series(self, messages):
        """Returns (timestamps, inter-message gaps in ms) for timeline plot."""
        ts = [m.timestamp for m in messages]
        gaps = [0.0] + [(ts[i] - ts[i-1]) * 1000 for i in range(1, len(ts))]
        return [t - ts[0] for t in ts], gaps

    @staticmethod
    def _percentile(data: list, pct: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * pct / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]


class __init__:
    pass

"""
Anomaly Detector for Vehicle Diagnostic Logs.
Detects timing anomalies, error bursts, and OTA-related issues.
"""

from dataclasses import dataclass
from typing import List, Tuple
import statistics


@dataclass
class Anomaly:
    timestamp: float
    anomaly_type: str
    description: str
    severity: str  # LOW / MEDIUM / HIGH / CRITICAL


class AnomalyDetector:
    """Detects anomalies in DLT and CAN log data."""

    def __init__(
        self,
        gap_threshold_ms: float = 500.0,
        error_burst_window: float = 1.0,
        error_burst_count: int = 3,
        timing_sigma: float = 3.0,
    ):
        self.gap_threshold_ms = gap_threshold_ms
        self.error_burst_window = error_burst_window
        self.error_burst_count = error_burst_count
        self.timing_sigma = timing_sigma

    def detect_dlt(self, messages) -> List[Anomaly]:
        anomalies: List[Anomaly] = []
        anomalies.extend(self._detect_gaps(messages))
        anomalies.extend(self._detect_error_bursts(messages))
        anomalies.extend(self._detect_ota_issues(messages))
        anomalies.extend(self._detect_security_events(messages))
        return sorted(anomalies, key=lambda a: a.timestamp)

    def detect_can(self, frames) -> List[Anomaly]:
        anomalies: List[Anomaly] = []
        anomalies.extend(self._detect_can_timing(frames))
        anomalies.extend(self._detect_can_errors(frames))
        return sorted(anomalies, key=lambda a: a.timestamp)

    # ── DLT anomaly detectors ─────────────────────────────────────────────────

    def _detect_gaps(self, messages) -> List[Anomaly]:
        result = []
        for i in range(1, len(messages)):
            gap_ms = (messages[i].timestamp - messages[i-1].timestamp) * 1000
            if gap_ms > self.gap_threshold_ms:
                severity = "HIGH" if gap_ms > 2000 else "MEDIUM"
                result.append(Anomaly(
                    timestamp=messages[i].timestamp,
                    anomaly_type="LOG_GAP",
                    description=f"Log gap of {gap_ms:.1f}ms between messages (threshold: {self.gap_threshold_ms}ms)",
                    severity=severity,
                ))
        return result

    def _detect_error_bursts(self, messages) -> List[Anomaly]:
        result = []
        error_msgs = [m for m in messages if m.log_level in ("ERROR", "FATAL")]
        i = 0
        while i < len(error_msgs):
            window_end = error_msgs[i].timestamp + self.error_burst_window
            burst = [m for m in error_msgs if error_msgs[i].timestamp <= m.timestamp <= window_end]
            if len(burst) >= self.error_burst_count:
                result.append(Anomaly(
                    timestamp=error_msgs[i].timestamp,
                    anomaly_type="ERROR_BURST",
                    description=f"{len(burst)} errors within {self.error_burst_window}s window",
                    severity="CRITICAL" if len(burst) >= 5 else "HIGH",
                ))
                i += len(burst)
            else:
                i += 1
        return result

    def _detect_ota_issues(self, messages) -> List[Anomaly]:
        result = []
        ota_msgs = [m for m in messages if "ota" in m.message.lower() or "OTA" in m.ecu_id]
        for msg in ota_msgs:
            txt = msg.message.lower()
            if any(kw in txt for kw in ("fail", "error", "timeout", "invalid", "reject")):
                result.append(Anomaly(
                    timestamp=msg.timestamp,
                    anomaly_type="OTA_FAILURE",
                    description=f"OTA issue detected: {msg.message[:80]}",
                    severity="CRITICAL",
                ))
            elif "checksum" in txt and "ok" not in txt:
                result.append(Anomaly(
                    timestamp=msg.timestamp,
                    anomaly_type="OTA_CHECKSUM",
                    description=f"OTA checksum concern: {msg.message[:80]}",
                    severity="HIGH",
                ))
        return result

    def _detect_security_events(self, messages) -> List[Anomaly]:
        result = []
        for msg in messages:
            txt = msg.message.lower()
            if "0x27" in txt or "securityaccess" in txt:
                if any(kw in txt for kw in ("denied", "fail", "invalid", "locked")):
                    result.append(Anomaly(
                        timestamp=msg.timestamp,
                        anomaly_type="SECURITY_VIOLATION",
                        description=f"SecurityAccess failure: {msg.message[:80]}",
                        severity="HIGH",
                    ))
        return result

    # ── CAN anomaly detectors ─────────────────────────────────────────────────

    def _detect_can_timing(self, frames) -> List[Anomaly]:
        from collections import defaultdict
        result = []
        groups = defaultdict(list)
        for f in frames:
            groups[f.can_id].append(f.timestamp)

        for can_id, timestamps in groups.items():
            if len(timestamps) < 5:
                continue
            gaps = [(timestamps[i+1] - timestamps[i]) * 1000
                    for i in range(len(timestamps)-1)]
            mean = statistics.mean(gaps)
            stdev = statistics.stdev(gaps) if len(gaps) > 1 else 0
            threshold = mean + self.timing_sigma * stdev

            for i, gap in enumerate(gaps):
                if gap > threshold and gap > 20:
                    result.append(Anomaly(
                        timestamp=timestamps[i+1],
                        anomaly_type="CAN_TIMING_VIOLATION",
                        description=(
                            f"CAN ID {can_id}: gap {gap:.1f}ms "
                            f"exceeds {self.timing_sigma}σ threshold ({threshold:.1f}ms)"
                        ),
                        severity="MEDIUM" if gap < 200 else "HIGH",
                    ))
        return result

    def _detect_can_errors(self, frames) -> List[Anomaly]:
        result = []
        for f in frames:
            if f.decoded and any(kw in f.decoded.lower() for kw in ("error", "nrc", "negative")):
                result.append(Anomaly(
                    timestamp=f.timestamp,
                    anomaly_type="CAN_PROTOCOL_ERROR",
                    description=f"Protocol error on CAN ID {f.can_id}: {f.decoded}",
                    severity="HIGH",
                ))
        return result

    def summary(self, anomalies: List[Anomaly]) -> dict:
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        types = {}
        for a in anomalies:
            counts[a.severity] = counts.get(a.severity, 0) + 1
            types[a.anomaly_type] = types.get(a.anomaly_type, 0) + 1
        return {"total": len(anomalies), "by_severity": counts, "by_type": types}

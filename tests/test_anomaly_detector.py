"""Tests for anomaly detector."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from parser.dlt_parser import DLTParser
from analyzer.anomaly_detector import AnomalyDetector

SAMPLE_WITH_ANOMALIES = """
0.001 ECM DIAG CTX1 4 Normal operation
0.002 TCM CTRL CTX2 4 Normal message
1.600 BCM COMM CTX1 2 Large gap after this
1.601 ABS DIAG CTX3 2 Error message one
1.602 ABS DIAG CTX3 2 Error message two
1.603 ABS DIAG CTX3 2 Error message three
2.000 OTA UPDT CTX1 4 OTA update chunk received
2.001 OTA UPDT CTX1 2 OTA validation checksum failed
2.100 ECM DIAG CTX1 4 SecurityAccess 0x27 denied
"""

def get_messages():
    p = DLTParser()
    return p.parse_text(SAMPLE_WITH_ANOMALIES)

def test_detects_gap():
    msgs = get_messages()
    d = AnomalyDetector(gap_threshold_ms=500)
    anomalies = d.detect_dlt(msgs)
    types = [a.anomaly_type for a in anomalies]
    assert "LOG_GAP" in types

def test_detects_error_burst():
    msgs = get_messages()
    d = AnomalyDetector(error_burst_count=3)
    anomalies = d.detect_dlt(msgs)
    types = [a.anomaly_type for a in anomalies]
    assert "ERROR_BURST" in types

def test_detects_ota_failure():
    msgs = get_messages()
    d = AnomalyDetector()
    anomalies = d.detect_dlt(msgs)
    types = [a.anomaly_type for a in anomalies]
    assert "OTA_FAILURE" in types

def test_detects_security_violation():
    msgs = get_messages()
    d = AnomalyDetector()
    anomalies = d.detect_dlt(msgs)
    types = [a.anomaly_type for a in anomalies]
    assert "SECURITY_VIOLATION" in types

def test_anomaly_severity_values():
    msgs = get_messages()
    d = AnomalyDetector()
    anomalies = d.detect_dlt(msgs)
    valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    for a in anomalies:
        assert a.severity in valid

def test_summary_keys():
    msgs = get_messages()
    d = AnomalyDetector()
    anomalies = d.detect_dlt(msgs)
    summary = d.summary(anomalies)
    assert "total" in summary
    assert "by_severity" in summary
    assert "by_type" in summary

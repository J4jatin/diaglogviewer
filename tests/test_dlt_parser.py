"""Tests for DLT parser."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from parser.dlt_parser import DLTParser, generate_demo_dlt

SAMPLE = """
0.001 ECM DIAG CTX1 4 DiagnosticSessionControl 0x10 requested
0.050 TCM CTRL CTX2 4 ReadDataByIdentifier 0x22 - VIN data read
0.100 BCM COMM CTX1 2 SecurityAccess 0x27 - seed requested
0.600 ABS DIAG CTX3 3 CAN frame timeout on node 0x1A
1.200 OTA UPDT CTX1 4 OTA update chunk received: 1024 bytes
1.201 OTA UPDT CTX1 2 OTA validation checksum failed
"""

def test_parse_text_count():
    p = DLTParser()
    msgs = p.parse_text(SAMPLE)
    assert len(msgs) == 6

def test_ecu_ids():
    p = DLTParser()
    p.parse_text(SAMPLE)
    ecu_ids = p.get_ecu_ids()
    assert "ECM" in ecu_ids
    assert "OTA" in ecu_ids

def test_log_levels():
    p = DLTParser()
    msgs = p.parse_text(SAMPLE)
    levels = {m.log_level for m in msgs}
    assert "INFO" in levels
    assert "ERROR" in levels

def test_uds_service_extraction():
    p = DLTParser()
    msgs = p.parse_text(SAMPLE)
    services = [m.service_id for m in msgs if m.service_id]
    assert len(services) > 0

def test_filter_by_ecu():
    p = DLTParser()
    p.parse_text(SAMPLE)
    filtered = p.filter(ecu_id="ECM")
    assert all(m.ecu_id == "ECM" for m in filtered)

def test_filter_by_level():
    p = DLTParser()
    p.parse_text(SAMPLE)
    filtered = p.filter(log_level="ERROR")
    assert all(m.log_level == "ERROR" for m in filtered)

def test_filter_by_keyword():
    p = DLTParser()
    p.parse_text(SAMPLE)
    filtered = p.filter(keyword="OTA")
    assert len(filtered) >= 1

def test_filter_by_time():
    p = DLTParser()
    p.parse_text(SAMPLE)
    filtered = p.filter(t_start=0.0, t_end=0.2)
    assert all(0.0 <= m.timestamp <= 0.2 for m in filtered)

def test_demo_generates_messages():
    demo = generate_demo_dlt()
    p = DLTParser()
    msgs = p.parse_text(demo)
    assert len(msgs) > 50

def test_timestamps_are_float():
    p = DLTParser()
    msgs = p.parse_text(SAMPLE)
    for m in msgs:
        assert isinstance(m.timestamp, float)

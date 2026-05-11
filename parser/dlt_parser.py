"""
DLT (Diagnostic Log and Trace) Parser
AUTOSAR DLT format parser for vehicle diagnostic logs.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class DLTMessage:
    timestamp: float
    ecu_id: str
    app_id: str
    context_id: str
    log_level: str
    message: str
    service_id: Optional[str] = None
    raw_line: str = ""


LOG_LEVEL_MAP = {
    "0": "OFF", "1": "FATAL", "2": "ERROR",
    "3": "WARN", "4": "INFO", "5": "DEBUG", "6": "VERBOSE"
}

# UDS service IDs for decoding
UDS_SERVICES = {
    "0x10": "DiagnosticSessionControl",
    "0x11": "ECUReset",
    "0x14": "ClearDiagnosticInformation",
    "0x19": "ReadDTCInformation",
    "0x22": "ReadDataByIdentifier",
    "0x23": "ReadMemoryByAddress",
    "0x27": "SecurityAccess",
    "0x28": "CommunicationControl",
    "0x2E": "WriteDataByIdentifier",
    "0x2F": "InputOutputControlByIdentifier",
    "0x31": "RoutineControl",
    "0x34": "RequestDownload",
    "0x35": "RequestUpload",
    "0x36": "TransferData",
    "0x37": "RequestTransferExit",
    "0x3E": "TesterPresent",
    "0x85": "ControlDTCSetting",
}


class DLTParser:
    """Parser for AUTOSAR DLT log files."""

    def __init__(self):
        self.messages: List[DLTMessage] = []
        self._pattern = re.compile(
            r"(\d+\.\d+)\s+"       # timestamp
            r"(\w+)\s+"            # ECU ID
            r"(\w+)\s+"            # APP ID
            r"(\w+)\s+"            # Context ID
            r"(\w+)\s+"            # log level
            r"(.*)"                # message
        )

    def parse_file(self, filepath: str) -> List[DLTMessage]:
        self.messages = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    msg = self._parse_line(line)
                    if msg:
                        self.messages.append(msg)
        except FileNotFoundError:
            raise FileNotFoundError(f"DLT file not found: {filepath}")
        return self.messages

    def parse_text(self, text: str) -> List[DLTMessage]:
        """Parse DLT log from a text string (for demo/testing)."""
        self.messages = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            msg = self._parse_line(line)
            if msg:
                self.messages.append(msg)
        return self.messages

    def _parse_line(self, line: str) -> Optional[DLTMessage]:
        m = self._pattern.match(line)
        if not m:
            return None
        timestamp, ecu_id, app_id, ctx_id, level, message = m.groups()
        service_id = self._extract_uds_service(message)
        return DLTMessage(
            timestamp=float(timestamp),
            ecu_id=ecu_id.upper(),
            app_id=app_id.upper(),
            context_id=ctx_id.upper(),
            log_level=LOG_LEVEL_MAP.get(level, level.upper()),
            message=message.strip(),
            service_id=service_id,
            raw_line=line,
        )

    def _extract_uds_service(self, message: str) -> Optional[str]:
        for sid, name in UDS_SERVICES.items():
            if sid.lower() in message.lower() or name.lower() in message.lower():
                return f"{sid} ({name})"
        return None

    def get_ecu_ids(self) -> List[str]:
        return sorted(set(m.ecu_id for m in self.messages))

    def get_app_ids(self) -> List[str]:
        return sorted(set(m.app_id for m in self.messages))

    def get_log_levels(self) -> List[str]:
        return sorted(set(m.log_level for m in self.messages))

    def filter(
        self,
        ecu_id: Optional[str] = None,
        app_id: Optional[str] = None,
        log_level: Optional[str] = None,
        keyword: Optional[str] = None,
        t_start: Optional[float] = None,
        t_end: Optional[float] = None,
    ) -> List[DLTMessage]:
        result = self.messages
        if ecu_id and ecu_id != "ALL":
            result = [m for m in result if m.ecu_id == ecu_id]
        if app_id and app_id != "ALL":
            result = [m for m in result if m.app_id == app_id]
        if log_level and log_level != "ALL":
            result = [m for m in result if m.log_level == log_level]
        if keyword:
            kw = keyword.lower()
            result = [m for m in result if kw in m.message.lower()]
        if t_start is not None:
            result = [m for m in result if m.timestamp >= t_start]
        if t_end is not None:
            result = [m for m in result if m.timestamp <= t_end]
        return result


def generate_demo_dlt() -> str:
    """Generate realistic demo DLT log data."""
    import random
    ecus = ["ECM", "TCM", "BCM", "ABS", "OTA"]
    apps = ["DIAG", "COMM", "CTRL", "UPDT", "SAFE"]
    ctxs = ["CTX1", "CTX2", "CTX3"]
    levels = ["4", "4", "4", "3", "2", "5"]
    messages = [
        "DiagnosticSessionControl 0x10 requested",
        "ReadDataByIdentifier 0x22 - VIN data read",
        "SecurityAccess 0x27 - seed requested",
        "WriteDataByIdentifier 0x2E - odometer updated",
        "ECUReset 0x11 triggered",
        "OTA update chunk received: 1024 bytes",
        "CAN frame timeout on node 0x1A",
        "Voltage within nominal range: 13.8V",
        "DTC P0300 detected - random misfire",
        "TesterPresent 0x3E keepalive sent",
        "RoutineControl 0x31 - self-test passed",
        "RequestDownload 0x34 - flash session started",
        "TransferData 0x36 block 001 OK",
        "ClearDiagnosticInformation 0x14 executed",
        "OTA validation checksum OK",
    ]
    lines = []
    t = 0.0
    for i in range(200):
        t += round(random.uniform(0.01, 0.5), 3)
        ecu = random.choice(ecus)
        app = random.choice(apps)
        ctx = random.choice(ctxs)
        lvl = random.choice(levels)
        msg = random.choice(messages)
        lines.append(f"{t:.3f} {ecu} {app} {ctx} {lvl} {msg}")
    return "\n".join(lines)

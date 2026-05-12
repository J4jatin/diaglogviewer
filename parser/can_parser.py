"""
CAN Bus Log Parser (.asc format)
Parses Vector CANalyzer/CANoe ASCII log files used in vehicle network diagnostics.
Also interfaces with the C++ CAN frame parser for low-level frame decoding.
"""

import re
import subprocess
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CANFrame:
    timestamp: float
    channel: int
    can_id: str
    direction: str  # Rx / Tx
    dlc: int
    data: List[str]  # hex bytes
    decoded: Optional[str] = None


class CANParser:
    """Parser for CAN .asc log files."""

    def __init__(self):
        self.frames: List[CANFrame] = []
        self._cpp_parser_path = os.path.join(
            os.path.dirname(__file__), "can_frame_parser"
        )
        # Pattern: timestamp channel ID Rx/Tx d DLC byte0 byte1 ...
        self._pattern = re.compile(
            r"^\s*(\d+\.\d+)\s+"   # timestamp
            r"(\d+)\s+"            # channel
            r"([0-9A-Fa-f]+)\s+"   # CAN ID
            r"(Rx|Tx)\s+"          # direction
            r"d\s+"                # data indicator
            r"(\d)\s+"             # DLC
            r"((?:[0-9A-Fa-f]{2}\s*)*)"  # data bytes
        )

    def parse_file(self, filepath: str) -> List[CANFrame]:
        self.frames = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    frame = self._parse_line(line)
                    if frame:
                        self.frames.append(frame)
        except FileNotFoundError:
            raise FileNotFoundError(f"CAN log file not found: {filepath}")
        return self.frames

    def parse_text(self, text: str) -> List[CANFrame]:
        self.frames = []
        for line in text.strip().splitlines():
            frame = self._parse_line(line)
            if frame:
                self.frames.append(frame)
        return self.frames

    def _parse_line(self, line: str) -> Optional[CANFrame]:
        m = self._pattern.match(line)
        if not m:
            return None
        ts, ch, can_id, direction, dlc, data_str = m.groups()
        data_bytes = data_str.strip().split()
        decoded = self._decode_frame(can_id, data_bytes)
        return CANFrame(
            timestamp=float(ts),
            channel=int(ch),
            can_id=can_id.upper(),
            direction=direction,
            dlc=int(dlc),
            data=data_bytes,
            decoded=decoded,
        )

    def _decode_frame(self, can_id: str, data: List[str]) -> str:
        """Basic OBD-II / UDS frame decoding."""
        if not data:
            return ""
        # Try C++ parser first
        decoded = self._call_cpp_parser(can_id, data)
        if decoded:
            return decoded
        # Fallback: simple OBD-II PID decode
        try:
            cid = int(can_id, 16)
            if 0x7E8 <= cid <= 0x7EF and len(data) >= 3:
                mode = int(data[1], 16)
                pid = int(data[2], 16)
                return f"OBD Mode {mode:#04x} PID {pid:#04x}"
        except (ValueError, IndexError):
            pass
        return ""

    def _call_cpp_parser(self, can_id: str, data: List[str]) -> str:
        """Invoke compiled C++ CAN frame parser."""
        if not os.path.exists(self._cpp_parser_path):
            return ""
        try:
            args = [self._cpp_parser_path, can_id] + data
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=1
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def get_can_ids(self) -> List[str]:
        return sorted(set(f.can_id for f in self.frames))

    def filter(
        self,
        can_id: Optional[str] = None,
        direction: Optional[str] = None,
        t_start: Optional[float] = None,
        t_end: Optional[float] = None,
    ) -> List[CANFrame]:
        result = self.frames
        if can_id and can_id != "ALL":
            result = [f for f in result if f.can_id == can_id]
        if direction and direction != "ALL":
            result = [f for f in result if f.direction == direction]
        if t_start is not None:
            result = [f for f in result if f.timestamp >= t_start]
        if t_end is not None:
            result = [f for f in result if f.timestamp <= t_end]
        return result

    def get_timing_stats(self) -> dict:
        """Compute inter-frame timing statistics per CAN ID."""
        from collections import defaultdict
        import statistics
        groups = defaultdict(list)
        for f in self.frames:
            groups[f.can_id].append(f.timestamp)
        stats = {}
        for cid, timestamps in groups.items():
            if len(timestamps) < 2:
                continue
            gaps = [timestamps[i+1] - timestamps[i]
                    for i in range(len(timestamps)-1)]
            stats[cid] = {
                "count": len(timestamps),
                "mean_interval_ms": round(statistics.mean(gaps) * 1000, 3),
                "min_interval_ms": round(min(gaps) * 1000, 3),
                "max_interval_ms": round(max(gaps) * 1000, 3),
                "stdev_ms": round(statistics.stdev(gaps) * 1000, 3) if len(gaps) > 1 else 0,
            }
        return stats


def generate_demo_can() -> str:
    """Generate realistic demo CAN .asc log data."""
    import random
    can_ids = ["7DF", "7E8", "18DB33F1", "0CF00400", "18FEF100"]
    directions = ["Rx", "Tx"]
    lines = ["begin measurement"]
    t = 0.0
    for _ in range(150):
        t += round(random.uniform(0.005, 0.1), 4)
        cid = random.choice(can_ids)
        d = random.choice(directions)
        dlc = random.randint(4, 8)
        data = " ".join(f"{random.randint(0, 255):02X}" for _ in range(dlc))
        lines.append(f"   {t:.4f} 1 {cid} {d} d {dlc} {data}")
    lines.append("end measurement")
    return "\n".join(lines)

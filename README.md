# DiagLogViewer — Vehicle Diagnostic Log Analyzer

> **Desktop GUI tool for parsing, filtering, and analyzing vehicle diagnostic logs**  
> AUTOSAR DLT | CAN Bus | UDS | OBD-II | J1939 | C++ Frame Parser | Anomaly Detection

![CI](https://github.com/J4jatin/diaglogviewer/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![C++](https://img.shields.io/badge/C%2B%2B-17-orange)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?logo=streamlit)](https://cunetperftes-qxuyabpwbytevbeovwgeeo.streamlit.app)

---

## Overview

Working with automotive diagnostic logs during my MSc, I kept running into the same problem: no good open-source tool existed for visually parsing and filtering AUTOSAR DLT and CAN bus logs together. Most workflows involved grep, manual scripts, and Excel — slow and error-prone.

DiagLogViewer fixes that. It's a PyQt5 desktop app that parses DLT and CAN `.asc` logs, decodes UDS service calls, detects anomalies automatically, and generates HTML reports — all in one window.

---

## Features

| Feature | Details |
|---------|---------|
| **DLT Log Parser** | AUTOSAR Diagnostic Log and Trace format with UDS service decoding |
| **CAN Bus Parser** | Vector CANalyzer .asc format, OBD-II PID decoding, J1939 PGN decoding |
| **C++ Frame Decoder** | Native C++17 parser for UDS/OBD-II/J1939 — called from Python via subprocess |
| **Anomaly Detection** | Log gaps, error bursts, OTA failures, SecurityAccess violations |
| **Performance Analysis** | Mean/P95/P99 inter-message gap, message rate, per-ECU breakdown |
| **Visualization** | Embedded matplotlib charts (timing series, message rate histogram) |
| **HTML Report Export** | Jinja2-rendered professional diagnostic report |
| **Real-time Filtering** | ECU ID, App ID, Log Level, Keyword, Time Range |

---

## Architecture

```
DiagLogViewer/
├── main.py                    # PyQt5 GUI main window
├── parser/
│   ├── dlt_parser.py          # AUTOSAR DLT format parser + UDS service decoder
│   ├── can_parser.py          # CAN .asc parser + Python-side OBD-II decode
│   └── can_frame_parser.cpp   # C++17 low-level CAN frame decoder (UDS/OBD/J1939)
├── analyzer/
│   ├── anomaly_detector.py    # Gap, error burst, OTA, security anomaly detection
│   └── performance_analyzer.py # Timing stats: mean, P95, P99, per-ECU rate
├── reporter/
│   └── html_reporter.py       # Jinja2 HTML diagnostic report generator
├── tests/
│   ├── test_dlt_parser.py     # 10 unit tests for DLT parser
│   └── test_anomaly_detector.py # 6 unit tests for anomaly detection
└── .github/workflows/ci.yml   # GitHub Actions CI (lint + test + C++ compile)
```

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install PyQt5 matplotlib jinja2

# 2. Compile the C++ CAN frame parser (optional but recommended)
cd parser
g++ -O2 -std=c++17 -o can_frame_parser can_frame_parser.cpp

# 3. Run the GUI
python main.py
```

The app loads with **demo DLT data** automatically — no log file needed to explore features.

---

## Usage

1. **Open DLT Log** — load an AUTOSAR `.dlt` or `.txt` log file
2. **Open CAN Log** — load a Vector CANalyzer `.asc` file
3. **Load Demo** — explore with realistic synthetic vehicle diagnostic data
4. **Filter** — filter by ECU ID, App ID, Log Level, keyword, or time range
5. **Anomalies tab** — view detected anomalies with severity ratings
6. **Performance Stats tab** — view timing metrics (mean, P95, P99, per-ECU rate)
7. **Charts** — visualize inter-message gap or message rate over time
8. **Export HTML Report** — generate a professional diagnostic report

---

## UDS Services Decoded

| Service ID | Name |
|-----------|------|
| 0x10 | DiagnosticSessionControl |
| 0x22 | ReadDataByIdentifier |
| 0x27 | SecurityAccess |
| 0x2E | WriteDataByIdentifier |
| 0x34 | RequestDownload (OTA) |
| 0x36 | TransferData (OTA) |
| 0x7F | NegativeResponse |
| ... | 15+ services total |

---

## Testing

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=.
```

16 unit tests covering parser, anomaly detection, and performance analysis.

---

## Author

**Jattin Shah** — MSc Applied AI, TU Dresden  
[github.com/J4jatin](https://github.com/J4jatin) | [linkedin.com/in/jattin-shah](https://linkedin.com/in/jattin-shah)

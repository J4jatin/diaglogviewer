import streamlit as st
import random
import re
import statistics
from datetime import datetime, timedelta

st.set_page_config(
    page_title="DiagLogViewer — Vehicle Diagnostic Log Analyzer",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 DiagLogViewer")
st.markdown("**Vehicle Diagnostic Log Analyzer** — AUTOSAR DLT · CAN Bus · UDS · Anomaly Detection")

UDS_SERVICES = {
    "0x10": "DiagnosticSessionControl",
    "0x11": "ECUReset",
    "0x19": "ReadDTCInformation",
    "0x22": "ReadDataByIdentifier",
    "0x27": "SecurityAccess",
    "0x28": "CommunicationControl",
    "0x2E": "WriteDataByIdentifier",
    "0x2F": "InputOutputControlByIdentifier",
    "0x31": "RoutineControl",
    "0x34": "RequestDownload (OTA)",
    "0x36": "TransferData (OTA)",
    "0x37": "RequestTransferExit (OTA)",
    "0x3E": "TesterPresent",
    "0x7F": "NegativeResponse",
}

ECU_NODES = ["ECM", "TCM", "BCM", "ABS", "OTA"]

def generate_sample_dlt():
    random.seed(42)
    lines = []
    t = datetime(2024, 3, 15, 9, 0, 0)
    services = list(UDS_SERVICES.keys())
    for i in range(80):
        ecu = random.choice(ECU_NODES)
        svc = random.choice(services)
        gap = random.gauss(50, 15)
        if i == 30:
            gap = 620  # anomaly: log gap
        if i == 55:
            svc = "0x7F"  # negative response burst
        t += timedelta(milliseconds=max(1, gap))
        level = "ERROR" if svc == "0x7F" else random.choice(["INFO", "INFO", "INFO", "DEBUG", "WARN"])
        lines.append(f"{t.strftime('%H:%M:%S.%f')[:-3]} {ecu} {level} UDS {svc} {UDS_SERVICES.get(svc, 'Unknown')} seq={i:04d}")
    return "\n".join(lines)

def generate_sample_asc():
    random.seed(99)
    lines = ["date Mon Mar 15 09:00:00 2024", "base hex timestamps absolute", "no internal events logged", ""]
    t = 0.001
    can_ids = ["7E0", "7E1", "7E2", "7E3", "7E4"]
    for i in range(60):
        t += random.uniform(0.001, 0.05)
        can_id = random.choice(can_ids)
        dlc = random.randint(1, 8)
        data = " ".join(f"{random.randint(0,255):02X}" for _ in range(dlc))
        lines.append(f"  {t:.6f} 1  {can_id}             Rx   d {dlc} {data}")
    return "\n".join(lines)

def parse_dlt(content):
    entries, anomalies = [], []
    prev_time = None
    lines = content.strip().split("\n")
    for line in lines:
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            ts = datetime.strptime(parts[0], "%H:%M:%S.%f")
            ecu, level, proto, svc = parts[1], parts[2], parts[3], parts[4]
            service_name = " ".join(parts[5:]).split("seq=")[0].strip()
            entries.append({"time": ts, "ecu": ecu, "level": level, "service": svc, "name": service_name})
            if prev_time:
                gap_ms = (ts - prev_time).total_seconds() * 1000
                if gap_ms > 500:
                    anomalies.append({"type": "Log Gap", "detail": f"{gap_ms:.0f}ms gap before {ecu} {svc}", "severity": "HIGH"})
            if level == "ERROR":
                anomalies.append({"type": "Error", "detail": f"{ecu} returned NegativeResponse ({svc})", "severity": "MEDIUM"})
            prev_time = ts
        except Exception:
            continue
    return entries, anomalies

def parse_asc(content):
    frames, ecu_map = [], {"7E0": "ECM", "7E1": "TCM", "7E2": "BCM", "7E3": "ABS", "7E4": "OTA"}
    for line in content.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) >= 6 and re.match(r'^\d+\.\d+$', parts[0]):
            try:
                ts = float(parts[0])
                can_id = parts[2]
                dlc = int(parts[5]) if parts[4] == 'd' else 0
                frames.append({"ts": ts, "can_id": can_id, "ecu": ecu_map.get(can_id, can_id), "dlc": dlc})
            except Exception:
                continue
    return frames

# Sidebar
st.sidebar.header("📁 Log File")
mode = st.sidebar.radio("Input Mode", ["Use Sample DLT Log", "Use Sample CAN (.asc) Log", "Upload Your File"])

log_content = ""
log_type = "dlt"

if mode == "Use Sample DLT Log":
    log_content = generate_sample_dlt()
    log_type = "dlt"
    st.sidebar.success("Sample AUTOSAR DLT log loaded (80 messages)")
elif mode == "Use Sample CAN (.asc) Log":
    log_content = generate_sample_asc()
    log_type = "asc"
    st.sidebar.success("Sample CAN bus .asc log loaded (60 frames)")
else:
    uploaded = st.sidebar.file_uploader("Upload .dlt or .asc file", type=["dlt", "asc", "txt", "log"])
    if uploaded:
        log_content = uploaded.read().decode("utf-8", errors="ignore")
        log_type = "asc" if uploaded.name.endswith(".asc") else "dlt"
        st.sidebar.success(f"Loaded: {uploaded.name}")

if st.sidebar.button("🔍 Analyze", type="primary", use_container_width=True) or mode != "Upload Your File":

    if not log_content:
        st.info("Upload a log file or select a sample above.")
        st.stop()

    if log_type == "dlt":
        entries, anomalies = parse_dlt(log_content)

        # Summary
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Messages", len(entries))
        col2.metric("ECUs Active", len(set(e["ecu"] for e in entries)))
        col3.metric("Anomalies", len(anomalies))
        errors = sum(1 for e in entries if e["level"] == "ERROR")
        col4.metric("Errors", errors)

        # Anomalies
        if anomalies:
            st.markdown("---")
            st.subheader("⚠️ Anomalies Detected")
            for a in anomalies:
                color = "#ff4444" if a["severity"] == "HIGH" else "#ff9800"
                st.markdown(f'<div style="background:#1a1a2e;border-left:3px solid {color};padding:0.6rem 1rem;margin:0.3rem 0;border-radius:4px"><b>{a["type"]}</b> — {a["detail"]} <span style="color:{color};float:right">{a["severity"]}</span></div>', unsafe_allow_html=True)

        # UDS breakdown
        st.markdown("---")
        st.subheader("📋 UDS Service Breakdown")
        import pandas as pd
        svc_counts = {}
        for e in entries:
            key = f"{e['service']} {e['name']}"
            svc_counts[key] = svc_counts.get(key, 0) + 1
        df_svc = pd.DataFrame(list(svc_counts.items()), columns=["Service", "Count"]).sort_values("Count", ascending=False)
        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(df_svc, hide_index=True, use_container_width=True)
        with col2:
            st.bar_chart(df_svc.set_index("Service")["Count"])

        # Per-ECU
        st.markdown("---")
        st.subheader("🔧 Per-ECU Message Count")
        ecu_counts = {}
        for e in entries:
            ecu_counts[e["ecu"]] = ecu_counts.get(e["ecu"], 0) + 1
        st.bar_chart(ecu_counts)

        # Raw log
        st.markdown("---")
        with st.expander("📄 Raw Log"):
            st.code(log_content, language="text")

    else:  # ASC
        frames = parse_asc(log_content)

        col1, col2, col3 = st.columns(3)
        col1.metric("CAN Frames", len(frames))
        col2.metric("ECUs Active", len(set(f["ecu"] for f in frames)))
        if frames:
            duration = frames[-1]["ts"] - frames[0]["ts"]
            col3.metric("Throughput", f"{len(frames)/duration:.1f} frames/s" if duration > 0 else "—")

        import pandas as pd
        if frames:
            st.markdown("---")
            st.subheader("📊 Frames per ECU")
            ecu_counts = {}
            for f in frames:
                ecu_counts[f["ecu"]] = ecu_counts.get(f["ecu"], 0) + 1
            st.bar_chart(ecu_counts)

            st.markdown("---")
            st.subheader("📄 CAN Frame Table (first 30)")
            df = pd.DataFrame(frames[:30])
            st.dataframe(df, hide_index=True, use_container_width=True)

        with st.expander("📄 Raw .asc Log"):
            st.code(log_content, language="text")

st.markdown("---")
st.markdown("Built by **Jattin Shah** · MSc Applied AI, TU Dresden · [github.com/J4jatin/diaglogviewer](https://github.com/J4jatin/diaglogviewer)")

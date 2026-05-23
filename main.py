"""
DiagLogViewer — Vehicle Diagnostic Log Analyzer
================================================
Desktop GUI application for parsing and analyzing vehicle diagnostic logs.
Supports AUTOSAR DLT format and CAN bus .asc log files.

Features:
  - DLT log parsing with UDS service decoding
  - CAN bus .asc log parsing with OBD-II / J1939 decoding
  - C++ CAN frame parser integration
  - Real-time filtering by ECU, App, Log Level, Keyword, Time Range
  - Performance timeline visualization (matplotlib)
  - Anomaly detection (gap, error burst, OTA, security)
  - HTML diagnostic report export

Requirements: pip install PyQt5 matplotlib jinja2
Author: Jattin Shah
"""

import sys
import os
import webbrowser
import tempfile
from datetime import datetime

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
        QLabel, QPushButton, QComboBox, QLineEdit, QFileDialog, QStatusBar,
        QGroupBox, QDoubleSpinBox, QTextEdit, QMessageBox, QProgressBar,
        QAction, QToolBar, QFrame,
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QColor, QFont, QIcon, QPalette
    HAS_QT = True
except ImportError:
    HAS_QT = False
    print("PyQt5 not installed. Run: pip install PyQt5")

try:
    import matplotlib
    matplotlib.use("Qt5Agg")
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from parser import DLTParser, CANParser, generate_demo_dlt, generate_demo_can
from analyzer import AnomalyDetector, PerformanceAnalyzer
from reporter import HTMLReporter


# ── Dark theme stylesheet ─────────────────────────────────────────────────────
DARK_STYLE = """
QMainWindow, QWidget { background-color: #0f0f14; color: #e0e0e0; }
QMenuBar { background: #1a1a2e; border-bottom: 1px solid #2a2a4a; }
QMenuBar::item:selected { background: #c00; }
QToolBar { background: #1a1a2e; border-bottom: 1px solid #2a2a4a; spacing: 4px; }
QTabWidget::pane { border: 1px solid #2a2a4a; background: #0f0f14; }
QTabBar::tab { background: #1a1a2e; color: #aaa; padding: 6px 16px; border: 1px solid #2a2a4a; margin-right: 2px; }
QTabBar::tab:selected { background: #c00; color: #fff; font-weight: bold; }
QTableWidget { background: #12122a; gridline-color: #1f1f3a; border: none; font-size: 12px; }
QTableWidget::item { padding: 3px 6px; }
QTableWidget::item:selected { background: #c00; color: #fff; }
QHeaderView::section { background: #1a1a2e; color: #aaa; padding: 5px; border: 1px solid #2a2a4a; font-size: 11px; font-weight: bold; text-transform: uppercase; }
QGroupBox { border: 1px solid #2a2a4a; border-radius: 4px; margin-top: 8px; padding-top: 8px; font-weight: bold; color: #aaa; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #c00; }
QPushButton { background: #c00; color: #fff; border: none; padding: 6px 16px; border-radius: 3px; font-weight: bold; min-width: 80px; }
QPushButton:hover { background: #e00; }
QPushButton:pressed { background: #900; }
QPushButton#secondary { background: #1a1a2e; color: #aaa; border: 1px solid #2a2a4a; }
QPushButton#secondary:hover { background: #2a2a4a; color: #fff; }
QComboBox, QLineEdit, QDoubleSpinBox { background: #1a1a2e; border: 1px solid #2a2a4a; color: #e0e0e0; padding: 4px 8px; border-radius: 3px; }
QComboBox::drop-down { border: none; }
QStatusBar { background: #1a1a2e; color: #888; border-top: 1px solid #2a2a4a; }
QSplitter::handle { background: #2a2a4a; width: 2px; }
QTextEdit { background: #12122a; border: 1px solid #2a2a4a; color: #ccc; font-family: Consolas, monospace; font-size: 11px; }
QScrollBar:vertical { background: #1a1a2e; width: 8px; }
QScrollBar::handle:vertical { background: #2a2a4a; border-radius: 4px; }
"""

LOG_LEVEL_COLORS = {
    "FATAL": "#ff4444",
    "ERROR": "#ff6b6b",
    "WARN":  "#ffd43b",
    "INFO":  "#e0e0e0",
    "DEBUG": "#74c0fc",
    "VERBOSE": "#888888",
    "OFF":   "#555555",
}

SEVERITY_COLORS = {
    "CRITICAL": "#ff4444",
    "HIGH":     "#ffa94d",
    "MEDIUM":   "#ffd43b",
    "LOW":      "#69db7c",
}


class ChartWidget(QWidget):
    """Embedded matplotlib chart for message timing visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(8, 3), facecolor="#0f0f14")
            self.canvas = FigureCanvas(self.fig)
            layout.addWidget(self.canvas)
            self.ax = self.fig.add_subplot(111)
            self._style_ax()
        else:
            layout.addWidget(QLabel("matplotlib not installed — charts unavailable"))

    def _style_ax(self):
        self.ax.set_facecolor("#12122a")
        self.ax.tick_params(colors="#888", labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color("#2a2a4a")
        self.fig.tight_layout(pad=1.0)

    def plot_timing(self, timestamps, gaps, title="Inter-Message Gap (ms)"):
        if not HAS_MATPLOTLIB:
            return
        self.ax.clear()
        self._style_ax()
        if timestamps and gaps:
            self.ax.plot(timestamps, gaps, color="#c00", linewidth=0.8, alpha=0.85)
            self.ax.fill_between(timestamps, gaps, alpha=0.15, color="#c00")
            mean_val = sum(gaps) / len(gaps)
            self.ax.axhline(mean_val, color="#ffd43b", linewidth=1, linestyle="--", label=f"Mean {mean_val:.1f}ms")
            self.ax.set_xlabel("Time (s)", color="#888", fontsize=8)
            self.ax.set_ylabel("Gap (ms)", color="#888", fontsize=8)
            self.ax.set_title(title, color="#aaa", fontsize=9)
            self.ax.legend(fontsize=7, facecolor="#1a1a2e", labelcolor="#aaa", edgecolor="#2a2a4a")
        self.canvas.draw()

    def plot_rate(self, buckets, counts, title="Message Rate over Time (msg/s)"):
        if not HAS_MATPLOTLIB:
            return
        self.ax.clear()
        self._style_ax()
        if buckets and counts:
            self.ax.bar(buckets, counts, width=0.8, color="#c00", alpha=0.75)
            self.ax.set_xlabel("Time (s)", color="#888", fontsize=8)
            self.ax.set_ylabel("Messages/s", color="#888", fontsize=8)
            self.ax.set_title(title, color="#aaa", fontsize=9)
        self.canvas.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DiagLogViewer — Vehicle Diagnostic Log Analyzer")
        self.setMinimumSize(1200, 750)
        self.dlt_parser = DLTParser()
        self.can_parser = CANParser()
        self.anomaly_detector = AnomalyDetector()
        self.perf_analyzer = PerformanceAnalyzer()
        self.reporter = HTMLReporter()
        self._current_messages = []
        self._current_anomalies = []
        self._current_perf = {}
        self._build_ui()
        self.setStyleSheet(DARK_STYLE)
        self._load_demo()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Toolbar
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        self._btn_open_dlt = QPushButton("Open DLT Log")
        self._btn_open_can = QPushButton("Open CAN Log")
        self._btn_demo = QPushButton("Load Demo")
        self._btn_demo.setObjectName("secondary")
        self._btn_export = QPushButton("Export HTML Report")
        self._btn_export.setObjectName("secondary")

        for btn in (self._btn_open_dlt, self._btn_open_can, self._btn_demo, self._btn_export):
            tb.addWidget(btn)

        self._btn_open_dlt.clicked.connect(self._open_dlt)
        self._btn_open_can.clicked.connect(self._open_can)
        self._btn_demo.clicked.connect(self._load_demo)
        self._btn_export.clicked.connect(self._export_report)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Filter panel
        main_layout.addWidget(self._build_filter_panel())

        # Splitter: table + chart
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_tabs())
        splitter.addWidget(self._build_chart_panel())
        splitter.setSizes([500, 200])
        main_layout.addWidget(splitter)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — Load a DLT or CAN log file to begin analysis")

    def _build_filter_panel(self):
        grp = QGroupBox("Filters")
        layout = QHBoxLayout(grp)

        self._combo_ecu = QComboBox(); self._combo_ecu.setMinimumWidth(100)
        self._combo_app = QComboBox(); self._combo_app.setMinimumWidth(100)
        self._combo_level = QComboBox(); self._combo_level.setMinimumWidth(90)
        self._txt_keyword = QLineEdit(); self._txt_keyword.setPlaceholderText("Keyword search...")
        self._spin_tstart = QDoubleSpinBox(); self._spin_tstart.setRange(0, 99999); self._spin_tstart.setDecimals(3); self._spin_tstart.setPrefix("From: ")
        self._spin_tend = QDoubleSpinBox(); self._spin_tend.setRange(0, 99999); self._spin_tend.setDecimals(3); self._spin_tend.setValue(99999); self._spin_tend.setPrefix("To: ")
        btn_apply = QPushButton("Apply"); btn_apply.clicked.connect(self._apply_filter)
        btn_clear = QPushButton("Clear"); btn_clear.setObjectName("secondary"); btn_clear.clicked.connect(self._clear_filter)

        for lbl, w in [("ECU:", self._combo_ecu), ("App:", self._combo_app), ("Level:", self._combo_level)]:
            layout.addWidget(QLabel(lbl)); layout.addWidget(w)
        layout.addWidget(self._txt_keyword)
        layout.addWidget(self._spin_tstart)
        layout.addWidget(self._spin_tend)
        layout.addWidget(btn_apply)
        layout.addWidget(btn_clear)
        return grp

    def _build_tabs(self):
        tabs = QTabWidget()
        tabs.addTab(self._build_dlt_table(), "DLT Messages")
        tabs.addTab(self._build_anomaly_table(), "Anomalies")
        tabs.addTab(self._build_perf_tab(), "Performance Stats")
        return tabs

    def _build_dlt_table(self):
        self._dlt_table = QTableWidget()
        self._dlt_table.setColumnCount(6)
        self._dlt_table.setHorizontalHeaderLabels(["Timestamp", "ECU ID", "App ID", "Level", "UDS Service", "Message"])
        self._dlt_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self._dlt_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._dlt_table.setSortingEnabled(True)
        self._dlt_table.verticalHeader().setVisible(False)
        return self._dlt_table

    def _build_anomaly_table(self):
        self._anomaly_table = QTableWidget()
        self._anomaly_table.setColumnCount(4)
        self._anomaly_table.setHorizontalHeaderLabels(["Timestamp", "Type", "Severity", "Description"])
        self._anomaly_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._anomaly_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._anomaly_table.verticalHeader().setVisible(False)
        return self._anomaly_table

    def _build_perf_tab(self):
        self._perf_text = QTextEdit()
        self._perf_text.setReadOnly(True)
        return self._perf_text

    def _build_chart_panel(self):
        grp = QGroupBox("Performance Timeline")
        layout = QVBoxLayout(grp)
        btn_row = QHBoxLayout()
        self._btn_chart_gap = QPushButton("Inter-Message Gap"); self._btn_chart_gap.setObjectName("secondary")
        self._btn_chart_rate = QPushButton("Message Rate"); self._btn_chart_rate.setObjectName("secondary")
        self._btn_chart_gap.clicked.connect(self._plot_gap)
        self._btn_chart_rate.clicked.connect(self._plot_rate)
        btn_row.addWidget(self._btn_chart_gap)
        btn_row.addWidget(self._btn_chart_rate)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self._chart = ChartWidget()
        layout.addWidget(self._chart)
        return grp

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_demo(self):
        demo_dlt = generate_demo_dlt()
        messages = self.dlt_parser.parse_text(demo_dlt)
        self._load_messages(messages, source="Demo DLT Log")

    def _open_dlt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open DLT Log", "", "DLT Files (*.dlt *.txt *.log);;All Files (*)")
        if path:
            try:
                messages = self.dlt_parser.parse_file(path)
                self._load_messages(messages, source=os.path.basename(path))
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _open_can(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CAN Log", "", "CAN ASC Files (*.asc);;All Files (*)")
        if path:
            try:
                frames = self.can_parser.parse_file(path)
                self._load_can_frames(frames, source=os.path.basename(path))
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _load_messages(self, messages, source=""):
        self._current_messages = messages
        self._current_anomalies = self.anomaly_detector.detect_dlt(messages)
        self._current_perf = self.perf_analyzer.analyze_dlt(messages)
        self._populate_filters(messages)
        self._populate_dlt_table(messages)
        self._populate_anomaly_table(self._current_anomalies)
        self._populate_perf_text(self._current_perf)
        self._plot_gap()
        n = len(messages)
        a = len(self._current_anomalies)
        crit = sum(1 for x in self._current_anomalies if x.severity == "CRITICAL")
        self.status.showMessage(f"{source} — {n} messages | {a} anomalies ({crit} critical) | Duration: {self._current_perf.get('duration_s', 0)}s")

    def _load_can_frames(self, frames, source=""):
        messages_like = []
        for f in frames:
            from parser.dlt_parser import DLTMessage
            messages_like.append(DLTMessage(
                timestamp=f.timestamp,
                ecu_id=f"CAN_{f.can_id}",
                app_id=f.direction,
                context_id="CAN",
                log_level="INFO",
                message=f"ID={f.can_id} DLC={f.dlc} DATA={' '.join(f.data)} {f.decoded or ''}",
                service_id=f.decoded or None,
            ))
        self._load_messages(messages_like, source=source)

    # ── Filters ───────────────────────────────────────────────────────────────

    def _populate_filters(self, messages):
        for combo, getter in [(self._combo_ecu, self.dlt_parser.get_ecu_ids),
                               (self._combo_app, self.dlt_parser.get_app_ids),
                               (self._combo_level, self.dlt_parser.get_log_levels)]:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("ALL")
            for item in getter():
                combo.addItem(item)
            combo.blockSignals(False)

    def _apply_filter(self):
        filtered = self.dlt_parser.filter(
            ecu_id=self._combo_ecu.currentText(),
            app_id=self._combo_app.currentText(),
            log_level=self._combo_level.currentText(),
            keyword=self._txt_keyword.text().strip() or None,
            t_start=self._spin_tstart.value() or None,
            t_end=self._spin_tend.value() if self._spin_tend.value() < 99998 else None,
        )
        self._populate_dlt_table(filtered)
        self.status.showMessage(f"Filter applied — showing {len(filtered)} of {len(self._current_messages)} messages")

    def _clear_filter(self):
        self._combo_ecu.setCurrentIndex(0)
        self._combo_app.setCurrentIndex(0)
        self._combo_level.setCurrentIndex(0)
        self._txt_keyword.clear()
        self._spin_tstart.setValue(0)
        self._spin_tend.setValue(99999)
        self._populate_dlt_table(self._current_messages)

    # ── Table population ──────────────────────────────────────────────────────

    def _populate_dlt_table(self, messages):
        self._dlt_table.setRowCount(0)
        self._dlt_table.setSortingEnabled(False)
        for msg in messages:
            row = self._dlt_table.rowCount()
            self._dlt_table.insertRow(row)
            items = [
                f"{msg.timestamp:.3f}",
                msg.ecu_id,
                msg.app_id,
                msg.log_level,
                msg.service_id or "",
                msg.message,
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == 3:
                    color = LOG_LEVEL_COLORS.get(msg.log_level, "#e0e0e0")
                    item.setForeground(QColor(color))
                self._dlt_table.setItem(row, col, item)
        self._dlt_table.setSortingEnabled(True)

    def _populate_anomaly_table(self, anomalies):
        self._anomaly_table.setRowCount(0)
        for a in anomalies:
            row = self._anomaly_table.rowCount()
            self._anomaly_table.insertRow(row)
            for col, text in enumerate([f"{a.timestamp:.3f}", a.anomaly_type, a.severity, a.description]):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == 2:
                    item.setForeground(QColor(SEVERITY_COLORS.get(a.severity, "#fff")))
                self._anomaly_table.setItem(row, col, item)

    def _populate_perf_text(self, perf):
        if not perf:
            return
        lines = ["── Performance Analysis ──\n"]
        lines.append(f"  Total Messages : {perf.get('total_messages', 0)}")
        lines.append(f"  Duration       : {perf.get('duration_s', 0)} s")
        lines.append(f"  Avg Rate       : {perf.get('avg_rate_hz', 0)} Hz")
        gap = perf.get("inter_message_gap_ms", {})
        lines.append(f"\n── Inter-Message Gap (ms) ──")
        lines.append(f"  Mean   : {gap.get('mean', 0)}")
        lines.append(f"  Median : {gap.get('median', 0)}")
        lines.append(f"  Min    : {gap.get('min', 0)}")
        lines.append(f"  Max    : {gap.get('max', 0)}")
        lines.append(f"  P95    : {gap.get('p95', 0)}")
        lines.append(f"  P99    : {gap.get('p99', 0)}")
        lines.append(f"\n── ECU Breakdown ──")
        for ecu, stats in perf.get("by_ecu", {}).items():
            lines.append(f"  {ecu:10s} : {stats['count']:4d} msgs @ {stats['rate_hz']} Hz")
        lines.append(f"\n── Log Level Distribution ──")
        for lvl, cnt in perf.get("by_log_level", {}).items():
            lines.append(f"  {lvl:8s} : {cnt}")
        self._perf_text.setPlainText("\n".join(lines))

    # ── Charts ────────────────────────────────────────────────────────────────

    def _plot_gap(self):
        if not self._current_messages:
            return
        ts, gaps = self.perf_analyzer.timing_series(self._current_messages)
        self._chart.plot_timing(ts, gaps)

    def _plot_rate(self):
        if not self._current_messages:
            return
        buckets, counts = self.perf_analyzer.message_rate_over_time(self._current_messages)
        self._chart.plot_rate(buckets, counts)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_report(self):
        if not self._current_messages:
            QMessageBox.information(self, "No Data", "Load a log file first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save HTML Report", "diagnostic_report.html", "HTML Files (*.html)")
        if not path:
            return
        summary = self.anomaly_detector.summary(self._current_anomalies)
        out = self.reporter.generate(
            title=datetime.now().strftime("%Y-%m-%d %H:%M"),
            messages=self._current_messages,
            anomalies=self._current_anomalies,
            perf=self._current_perf,
            anomaly_summary=summary,
            output_path=path,
        )
        webbrowser.open(f"file://{os.path.abspath(out)}")
        self.status.showMessage(f"Report exported: {out}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not HAS_QT:
        print("ERROR: PyQt5 is required. Install with: pip install PyQt5 matplotlib jinja2")
        sys.exit(1)
    app = QApplication(sys.argv)
    app.setApplicationName("DiagLogViewer")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

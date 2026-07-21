from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from safetwin.core.risk_utils import zone_type_to_risk_score
from safetwin.core.signals import bus


class HeatmapWidget(QWidget):
    """Render the current zone state as a live zone-status list with hotspot markers."""

    def __init__(self, parent=None, title: str = "Zone Heatmap"):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._pending_zone_map = None
        self._pending_hotspots = []
        self._render_scheduled = False

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            "background-color: rgba(2, 48, 89, 220); color: white; padding: 6px; border-radius: 4px;"
        )

        # Smaller figure to better fit dashboard layout
        self.figure = Figure(figsize=(3.5, 2.6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.18, right=0.96, top=0.90, bottom=0.12)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.canvas, stretch=1)

        bus.RISK_UPDATE.connect(self.handle_risk_update)
        self._render_placeholder()

    def handle_risk_update(self, payload: dict):
        zone_map = payload.get("zone_map")
        if zone_map is None:
            return

        self.update_heatmap(zone_map, payload.get("hotspots", []))

    def update_heatmap(self, zone_map, hotspots: Sequence | None = None):
        self._pending_zone_map = zone_map
        self._pending_hotspots = list(hotspots or [])

        if self._render_scheduled:
            return

        self._render_scheduled = True
        QTimer.singleShot(0, self._render_pending)

    def clear(self):
        self._pending_zone_map = None
        self._pending_hotspots = []
        self._render_placeholder()

    def _render_pending(self):
        self._render_scheduled = False

        if self._pending_zone_map is None:
            self._render_placeholder()
            return

        if isinstance(self._pending_zone_map, dict) or isinstance(self._pending_zone_map, list):
            if isinstance(self._pending_zone_map, list):
                zone_entries = self._pending_zone_map
            else:
                zone_entries = self._pending_zone_map.get("zones", [])
            labels = []
            intensities = []
            colors = []
            for entry in zone_entries:
                zone_id = entry.get('id', 'zone')
                zone_type = entry.get('type', 'CAUTION')
                risk_score = entry.get('risk_score')
                if isinstance(risk_score, (int, float)):
                    value = float(np.clip(risk_score, 0.0, 1.0))
                else:
                    value = self._zone_value(zone_type)
                labels.append(f"{zone_id}: {zone_type} ({value:.2f})")
                intensities.append(value)
                if value < 0.35:
                    colors.append("#10b981")
                elif value < 0.70:
                    colors.append("#f59e0b")
                else:
                    colors.append("#ef4444")
            self.ax.clear()
            bars = self.ax.barh(labels, intensities, color=colors, edgecolor="white", linewidth=0.6)
            # Make text/ticks visible on dark UI
            self.ax.set_facecolor("#0f3557")
            self.ax.set_title("Zone Risk Scores", fontsize=10, pad=6, color="white")
            self.ax.set_xlabel("Risk Intensity", color="white")
            self.ax.set_xlim(0, 1.0)
            self.ax.invert_yaxis()
            self.ax.tick_params(colors="white")
            for label in self.ax.get_yticklabels():
                label.set_color("white")
                label.set_fontsize(9)
            for label in self.ax.get_xticklabels():
                label.set_color("white")
                label.set_fontsize(9)
            # remove spines color to soften contrast
            for spine in self.ax.spines.values():
                spine.set_edgecolor("white")
            self.figure.patch.set_facecolor("#0f3557")
            for bar, value in zip(bars, intensities):
                bar_width = bar.get_width()
                text_color = "white" if bar_width >= 0.35 else "black"
                self.ax.text(
                    bar_width + 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    f"{bar_width:.2f}",
                    va="center",
                    ha="left",
                    fontsize=8,
                    color=text_color,
                    fontweight="bold",
                    bbox={"facecolor": "#0f3557", "edgecolor": "none", "pad": 0.9, "alpha": 0.8},
                )
            self.figure.tight_layout()
            self.canvas.draw_idle()
            return

        zone_array = np.asarray(self._pending_zone_map)
        if zone_array.ndim != 2:
            self._render_placeholder("Unsupported zone map shape")
            return

        heatmap_data = self._zone_map_to_numeric(zone_array)
        self.ax.clear()
        image = self.ax.imshow(heatmap_data, cmap="inferno", interpolation="nearest", aspect="auto")
        self.figure.colorbar(image, ax=self.ax, fraction=0.046, pad=0.04)

        rows, columns = heatmap_data.shape
        self.ax.set_xticks(np.arange(columns))
        self.ax.set_yticks(np.arange(rows))
        self.ax.set_xticklabels([str(index + 1) for index in range(columns)], fontsize=8, color="white")
        self.ax.set_yticklabels([str(index + 1) for index in range(rows)], fontsize=8, color="white")
        self.ax.set_xlabel("Zone Column", color="white")
        self.ax.set_ylabel("Zone Row", color="white")
        self.ax.set_title("Live Risk Heatmap", fontsize=9, pad=6, color="white")
        self.ax.set_xticks(np.arange(-0.5, columns, 1), minor=True)
        self.ax.set_yticks(np.arange(-0.5, rows, 1), minor=True)
        self.ax.grid(which="minor", color="white", linestyle="-", linewidth=0.6, alpha=0.35)
        self.ax.tick_params(which="minor", bottom=False, left=False)
        self.ax.tick_params(colors="white")

        self._annotate_cells(zone_array)
        self._plot_hotspots(self._pending_hotspots)
        self.canvas.draw_idle()

    def _render_placeholder(self, message: str = "Waiting for risk updates..."):
        self.ax.clear()
        self.ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            fontsize=12,
            color="white",
            transform=self.ax.transAxes,
        )
        self.ax.set_axis_off()
        self.canvas.draw_idle()

    def _zone_map_to_numeric(self, zone_array: np.ndarray) -> np.ndarray:
        if zone_array.dtype.kind in "ifuc":
            return zone_array.astype(float)

        def to_numeric(value):
            return zone_type_to_risk_score(value)

        return np.vectorize(to_numeric)(zone_array).astype(float)

    def _zone_value(self, zone_type):
        return zone_type_to_risk_score(zone_type)

    def _annotate_cells(self, zone_array: np.ndarray):
        rows, columns = zone_array.shape
        if rows * columns > 64:
            return

        for row_index in range(rows):
            for column_index in range(columns):
                value = str(zone_array[row_index, column_index])
                label = value.replace("/", "\n") if len(value) > 10 else value
                self.ax.text(
                    column_index,
                    row_index,
                    label,
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                )

    def _plot_hotspots(self, hotspots: Iterable):
        if not hotspots:
            return

        rows = []
        columns = []
        for hotspot in hotspots:
            row_index, column_index = self._parse_hotspot(hotspot)
            if row_index is None or column_index is None:
                continue
            rows.append(row_index)
            columns.append(column_index)

        if rows and columns:
            self.ax.scatter(columns, rows, s=160, c="#00e5ff", edgecolors="black", linewidths=1.2, marker="o")

    def _parse_hotspot(self, hotspot):
        if isinstance(hotspot, dict):
            row_index = hotspot.get("row", hotspot.get("by", hotspot.get("y")))
            column_index = hotspot.get("column", hotspot.get("bx", hotspot.get("x")))
        elif isinstance(hotspot, (tuple, list)) and len(hotspot) >= 2:
            row_index, column_index = hotspot[0], hotspot[1]
        else:
            return None, None

        try:
            return int(row_index), int(column_index)
        except (TypeError, ValueError):
            return None, None

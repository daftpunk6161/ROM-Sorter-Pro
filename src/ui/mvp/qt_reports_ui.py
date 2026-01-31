"""Reports UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReportsInputs:
    btn_library_report: Any
    btn_library_report_save: Any
    btn_export_scan_csv: Any
    btn_export_scan_json: Any
    btn_export_plan_csv: Any
    btn_export_plan_json: Any
    btn_export_audit_csv: Any
    btn_export_audit_json: Any
    btn_export_frontend_es: Any
    btn_export_frontend_launchbox: Any
    btn_export_frontend_retroarch: Any
    btn_feature_refresh: Any
    btn_feature_badges: Any
    btn_feature_media: Any
    btn_feature_normalize: Any
    btn_feature_library: Any


@dataclass(frozen=True)
class ReportsUI:
    library_report_summary: Any
    library_top_systems: Any
    library_top_regions: Any
    feature_analytics_label: Any
    feature_badges_label: Any
    feature_media_label: Any
    feature_normalize_label: Any
    feature_library_label: Any


def build_reports_ui(QtWidgets, reports_layout, inputs: ReportsInputs) -> ReportsUI:
    reports_title = QtWidgets.QLabel("Reports & Export")
    reports_title.setStyleSheet("font-size: 16px; font-weight: 600;")
    reports_layout.addWidget(reports_title)

    library_group = QtWidgets.QGroupBox("Bibliothek-Report")
    library_layout = QtWidgets.QVBoxLayout(library_group)
    library_report_summary = QtWidgets.QLabel(
        "Gesamt: -   |   Erkannt: -   |   Unbekannt: -"
    )
    library_report_summary.setWordWrap(True)
    library_layout.addWidget(library_report_summary)

    library_stats = QtWidgets.QGridLayout()
    library_stats.addWidget(QtWidgets.QLabel("Top Systeme:"), 0, 0)
    library_top_systems = QtWidgets.QLabel("-")
    library_top_systems.setWordWrap(True)
    library_stats.addWidget(library_top_systems, 0, 1)
    library_stats.addWidget(QtWidgets.QLabel("Top Regionen:"), 1, 0)
    library_top_regions = QtWidgets.QLabel("-")
    library_top_regions.setWordWrap(True)
    library_stats.addWidget(library_top_regions, 1, 1)
    library_stats.setColumnStretch(1, 1)
    library_layout.addLayout(library_stats)

    library_btn_row = QtWidgets.QHBoxLayout()
    library_btn_row.addWidget(inputs.btn_library_report)
    library_btn_row.addWidget(inputs.btn_library_report_save)
    library_btn_row.addStretch(1)
    library_layout.addLayout(library_btn_row)
    reports_layout.addWidget(library_group)

    export_group = QtWidgets.QGroupBox("Export")
    export_layout = QtWidgets.QGridLayout(export_group)
    export_layout.setHorizontalSpacing(6)
    export_layout.setVerticalSpacing(6)
    export_layout.addWidget(QtWidgets.QLabel("Scan-Ergebnisse:"), 0, 0)
    export_layout.addWidget(inputs.btn_export_scan_csv, 0, 1)
    export_layout.addWidget(inputs.btn_export_scan_json, 0, 2)
    export_layout.addWidget(QtWidgets.QLabel("Sortierplan:"), 1, 0)
    export_layout.addWidget(inputs.btn_export_plan_csv, 1, 1)
    export_layout.addWidget(inputs.btn_export_plan_json, 1, 2)
    export_layout.addWidget(QtWidgets.QLabel("Audit-Ergebnisse:"), 2, 0)
    export_layout.addWidget(inputs.btn_export_audit_csv, 2, 1)
    export_layout.addWidget(inputs.btn_export_audit_json, 2, 2)
    export_layout.setColumnStretch(3, 1)
    reports_layout.addWidget(export_group)

    frontend_group = QtWidgets.QGroupBox("Frontend-Export")
    frontend_layout = QtWidgets.QHBoxLayout(frontend_group)
    frontend_layout.addWidget(inputs.btn_export_frontend_es)
    frontend_layout.addWidget(inputs.btn_export_frontend_launchbox)
    frontend_layout.addWidget(inputs.btn_export_frontend_retroarch)
    frontend_layout.addStretch(1)
    reports_layout.addWidget(frontend_group)

    feature_group = QtWidgets.QGroupBox("Feature Hub")
    feature_layout = QtWidgets.QGridLayout(feature_group)
    feature_layout.setHorizontalSpacing(8)
    feature_layout.setVerticalSpacing(6)

    feature_analytics_label = QtWidgets.QLabel("Analytics: -")
    feature_badges_label = QtWidgets.QLabel("Badges: -")
    feature_media_label = QtWidgets.QLabel("Media-Preview: -")
    feature_normalize_label = QtWidgets.QLabel("AI-Normalizer: -")
    feature_library_label = QtWidgets.QLabel("Multi-Library: -")
    for label in (
        feature_analytics_label,
        feature_badges_label,
        feature_media_label,
        feature_normalize_label,
        feature_library_label,
    ):
        label.setWordWrap(True)

    feature_layout.addWidget(QtWidgets.QLabel("Analytics"), 0, 0)
    feature_layout.addWidget(feature_analytics_label, 0, 1)
    feature_layout.addWidget(inputs.btn_feature_refresh, 0, 2)

    feature_layout.addWidget(QtWidgets.QLabel("Badges"), 1, 0)
    feature_layout.addWidget(feature_badges_label, 1, 1)
    feature_layout.addWidget(inputs.btn_feature_badges, 1, 2)

    feature_layout.addWidget(QtWidgets.QLabel("AI-Normalizer"), 2, 0)
    feature_layout.addWidget(feature_normalize_label, 2, 1)
    feature_layout.addWidget(inputs.btn_feature_normalize, 2, 2)

    feature_layout.addWidget(QtWidgets.QLabel("Media-Preview"), 3, 0)
    feature_layout.addWidget(feature_media_label, 3, 1)
    feature_layout.addWidget(inputs.btn_feature_media, 3, 2)

    feature_layout.addWidget(QtWidgets.QLabel("Multi-Library"), 4, 0)
    feature_layout.addWidget(feature_library_label, 4, 1)
    feature_layout.addWidget(inputs.btn_feature_library, 4, 2)

    feature_layout.setColumnStretch(1, 1)
    reports_layout.addWidget(feature_group)
    reports_layout.addStretch(1)

    return ReportsUI(
        library_report_summary=library_report_summary,
        library_top_systems=library_top_systems,
        library_top_regions=library_top_regions,
        feature_analytics_label=feature_analytics_label,
        feature_badges_label=feature_badges_label,
        feature_media_label=feature_media_label,
        feature_normalize_label=feature_normalize_label,
        feature_library_label=feature_library_label,
    )

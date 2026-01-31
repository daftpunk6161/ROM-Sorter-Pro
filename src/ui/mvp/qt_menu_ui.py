from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MenuActions:
    export_scan_csv: Any
    export_scan_json: Any
    export_plan_csv: Any
    export_plan_json: Any
    export_frontend_es: Any
    export_frontend_launchbox: Any
    export_frontend_retroarch: Any
    export_audit_csv: Any
    export_audit_json: Any


def build_menu_bar(QtGui, parent) -> MenuActions:
    menu_bar = parent.menuBar()
    export_menu = menu_bar.addMenu("Export")

    export_scan_csv = QtGui.QAction("Scan CSV", parent)
    export_scan_json = QtGui.QAction("Scan JSON", parent)
    export_plan_csv = QtGui.QAction("Plan CSV", parent)
    export_plan_json = QtGui.QAction("Plan JSON", parent)
    export_frontend_es = QtGui.QAction("Frontend EmulationStation", parent)
    export_frontend_launchbox = QtGui.QAction("Frontend LaunchBox", parent)
    export_frontend_retroarch = QtGui.QAction("Frontend RetroArch", parent)
    export_audit_csv = QtGui.QAction("Audit CSV", parent)
    export_audit_json = QtGui.QAction("Audit JSON", parent)

    export_menu.addAction(export_scan_csv)
    export_menu.addAction(export_scan_json)
    export_menu.addSeparator()
    export_menu.addAction(export_plan_csv)
    export_menu.addAction(export_plan_json)
    export_menu.addSeparator()
    export_menu.addAction(export_frontend_es)
    export_menu.addAction(export_frontend_launchbox)
    export_menu.addAction(export_frontend_retroarch)
    export_menu.addSeparator()
    export_menu.addAction(export_audit_csv)
    export_menu.addAction(export_audit_json)

    return MenuActions(
        export_scan_csv=export_scan_csv,
        export_scan_json=export_scan_json,
        export_plan_csv=export_plan_csv,
        export_plan_json=export_plan_json,
        export_frontend_es=export_frontend_es,
        export_frontend_launchbox=export_frontend_launchbox,
        export_frontend_retroarch=export_frontend_retroarch,
        export_audit_csv=export_audit_csv,
        export_audit_json=export_audit_json,
    )

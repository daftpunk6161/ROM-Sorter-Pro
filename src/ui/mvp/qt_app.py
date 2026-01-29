"""Qt GUI entrypoint wrapper.

The implementation lives in qt_app_impl.py to keep this module lean.
"""

from __future__ import annotations

from .qt_app_impl import _load_qt, handle_worker_failure, run

__all__ = ["run", "handle_worker_failure", "_load_qt"]

if False:
    r'''
"""ROM Sorter Pro - MVP Qt GUI (GUI-first).

MVP features:
"""Qt GUI entrypoint wrapper.

The implementation lives in qt_app_impl.py to keep this module lean.
"""

from __future__ import annotations

from .qt_app_impl import handle_worker_failure, run

__all__ = ["run", "handle_worker_failure"]
- Source folder picker
- Destination folder picker
- Buttons: Scan, Preview Sort (Dry-run), Execute Sort, Cancel
- Progress bar + live log (ring buffer)
- Result table: InputPath, DetectedConsole/Type, Confidence, Signals, Candidates, PlannedTargetPath, Action, Status/Error

Threading model:
- QThread + QObject worker
- UI updates only via Qt signals

Qt binding preference (deterministic):
- PySide6 (preferred)
- PyQt5
"""

from __future__ import annotations

import importlib
import os
import logging
import time
import sqlite3
import sys
import traceback
import threading
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

logger = logging.getLogger(__name__)


from ...version import load_version


def handle_worker_failure(
    message: str,
    traceback_text: str,
    log_cb,
    dialog_cb,
) -> None:
    """Log worker failures and route them to an error dialog callback.

    The implementation lives in qt_app_impl.py to keep this module lean.
    ###

    from __future__ import annotations

    from .qt_app_impl import handle_worker_failure, run

    __all__ = ["run", "handle_worker_failure"]
    if log_cb is not None:
        if message:
            log_cb(message)
        if traceback_text:
            log_cb(traceback_text)
    """Qt GUI entrypoint wrapper.

    The implementation lives in qt_app_impl.py to keep this module lean.
    ###

    from __future__ import annotations

    from .qt_app_impl import handle_worker_failure, run

    __all__ = ["run", "handle_worker_failure"]
                    }
                self.tools_signal.emit(payload)

            threading.Thread(target=task, daemon=True).start()

        def _on_tools_status(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            wud2app = payload.get("wud2app") or {}
            wudcompress = payload.get("wudcompress") or {}
            self.wud2app_version.setText(str(wud2app.get("version") or "unknown"))
            self.wud2app_probe.setText(str(wud2app.get("message") or ""))
            self.wudcompress_version.setText(str(wudcompress.get("version") or "unknown"))
            self.wudcompress_probe.setText(str(wudcompress.get("message") or ""))

        def closeEvent(self, event):
            self._remove_log_handler()
            try:
                if self._log_flush_timer is not None:
                    self._log_flush_timer.stop()
                    self._flush_log()
            except Exception:
                pass
            try:
                if self._backend_worker is not None:
                    self._backend_worker.cancel()
                if self._export_cancel_token is not None:
                    self._export_cancel_token.cancel()
                if self._thread is not None:
                    self._thread.quit()
                    self._thread.wait(5000)
                if self._export_thread is not None:
                    self._export_thread.quit()
                    self._export_thread.wait(5000)
            except Exception:
                pass
            self._save_window_size()
            return super().closeEvent(event)

        def _install_log_handler(self) -> None:
            root_logger = logging.getLogger()
            for handler in list(root_logger.handlers):
                if getattr(handler, "_qt_gui_handler", False):
                    root_logger.removeHandler(handler)

            handler = QtLogHandler(self.log_signal.emit)
            handler._qt_gui_handler = True
            handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            root_logger.addHandler(handler)
            self._log_handler = handler

        def _remove_log_handler(self) -> None:
            root_logger = logging.getLogger()
            handler = getattr(self, "_log_handler", None)
            if handler is not None:
                try:
                    root_logger.removeHandler(handler)
                except Exception:
                    pass
            for handler in list(root_logger.handlers):
                if getattr(handler, "_qt_gui_handler", False):
                    try:
                        root_logger.removeHandler(handler)
                    except Exception:
                        pass

        def _on_filters_changed(self, _value: str = "") -> None:
            self._enforce_all_exclusive(self.lang_filter)
            self._enforce_all_exclusive(self.region_filter)
            # Changing filters invalidates existing plan.
            if self._sort_plan is not None:
                self._sort_plan = None
                self._append_log("Filters changed: sort plan invalidated. Please run Preview Sort again.")

            if self._scan_result is not None:
                # Keep table in sync with current filter selection.
                self._populate_scan_table(self._get_filtered_scan_result())
                self._last_view = "scan"

        def _format_reason(self, item: ScanItem) -> str:
            raw = item.raw or {}
            reason = raw.get("reason") or raw.get("policy") or ""
            if not reason:
                reason = str(item.detection_source or "")
            min_conf = self._get_min_confidence()
            if str(item.detection_source) == "policy-low-confidence":
                reason = f"low-confidence (<{min_conf:.2f})"
            return str(reason or "")

        def _format_normalization_hint(self, input_path: str, platform_id: str) -> str:
            if not input_path:
                return "-"
            try:
                norm = normalize_input(input_path, platform_hint=str(platform_id or ""))
                if norm.issues:
                    return "; ".join(issue.message for issue in norm.issues)
                return "ok"
            except Exception as exc:
                return f"Fehler: {exc}"

        def _show_why_unknown(self) -> None:
            try:
                view_index = self.table.currentIndex()
                source_index = self.results_proxy.mapToSource(view_index)
                row = source_index.row()
            except Exception:
                row = -1
            if row < 0 or row >= len(self._table_items):
                QtWidgets.QMessageBox.information(self, "Why Unknown", "Keine Scan-Zeile ausgewählt.")
                return
            item = self._table_items[row]
            raw = item.raw or {}
            reason = self._format_reason(item) or "-"
            signals = ", ".join(raw.get("signals") or []) if isinstance(raw.get("signals"), list) else "-"
            candidates = ", ".join(raw.get("candidates") or []) if isinstance(raw.get("candidates"), list) else "-"
            source = str(item.detection_source or "-")
            confidence = self._format_confidence(item.detection_confidence)
            exact = "ja" if getattr(item, "is_exact", False) else "nein"
            normalization_hint = self._format_normalization_hint(item.input_path, item.detected_system)
            msg = (
                f"System: {item.detected_system}\n"
                f"Reason: {reason}\n"
                f"Quelle: {source}\n"
                f"Sicherheit: {confidence}\n"
                f"Exact: {exact}\n"
                f"Signale: {signals}\n"
                f"Kandidaten: {candidates}\n"
                f"Normalisierung: {normalization_hint}"
            )
            QtWidgets.QMessageBox.information(self, "Why Unknown", msg)

        def _clear_filters(self) -> None:
            def _set_combo(combo, value: str) -> None:
                idx = combo.findText(value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(0)

            self._select_filter_values(self.lang_filter, ["All"])
            _set_combo(self.ver_filter, "All")
            self._select_filter_values(self.region_filter, ["All"])
            self.ext_filter_edit.clear()
            self.min_size_edit.clear()
            self.max_size_edit.clear()
            self.dedupe_checkbox.setChecked(True)
            self.hide_unknown_checkbox.setChecked(False)
            self._on_filters_changed()

        def _collect_preset_values(self) -> dict:
            return {
                "sort": {
                    "mode": str(self.mode_combo.currentText()),
                    "conflict": str(self.conflict_combo.currentText()),
                    "console_folders": bool(self.chk_console_folders.isChecked()),
                    "region_subfolders": bool(self.chk_region_subfolders.isChecked()),
                    "preserve_structure": bool(self.chk_preserve_structure.isChecked()),
                },
                "filters": {
                    "languages": self._get_selected_filter_values(self.lang_filter),
                    "version": str(self.ver_filter.currentText() or "All"),
                    "regions": self._get_selected_filter_values(self.region_filter),
                    "extension": str(self.ext_filter_edit.text() or ""),
                    "min_size": str(self.min_size_edit.text() or ""),
                    "max_size": str(self.max_size_edit.text() or ""),
                    "dedupe": bool(self.dedupe_checkbox.isChecked()),
                    "hide_unknown": bool(self.hide_unknown_checkbox.isChecked()),
                },
            }

        def _apply_preset_values(self, payload: dict) -> None:
            sort_cfg = payload.get("sort") or {}
            filters_cfg = payload.get("filters") or {}

            if str(sort_cfg.get("mode")) in ("copy", "move"):
                idx = self.mode_combo.findText(str(sort_cfg.get("mode")))
                if idx >= 0:
                    self.mode_combo.setCurrentIndex(idx)
            if str(sort_cfg.get("conflict")) in ("rename", "skip", "overwrite"):
                idx = self.conflict_combo.findText(str(sort_cfg.get("conflict")))
                if idx >= 0:
                    self.conflict_combo.setCurrentIndex(idx)
            self.chk_console_folders.setChecked(bool(sort_cfg.get("console_folders", True)))
            self.chk_region_subfolders.setChecked(bool(sort_cfg.get("region_subfolders", False)))
            self.chk_preserve_structure.setChecked(bool(sort_cfg.get("preserve_structure", False)))

            self._select_filter_values(self.lang_filter, filters_cfg.get("languages") or ["All"])
            ver_value = str(filters_cfg.get("version") or "All")
            ver_idx = self.ver_filter.findText(ver_value)
            self.ver_filter.setCurrentIndex(ver_idx if ver_idx >= 0 else 0)
            self._select_filter_values(self.region_filter, filters_cfg.get("regions") or ["All"])
            self.ext_filter_edit.setText(str(filters_cfg.get("extension") or ""))
            self.min_size_edit.setText(str(filters_cfg.get("min_size") or ""))
            self.max_size_edit.setText(str(filters_cfg.get("max_size") or ""))
            self.dedupe_checkbox.setChecked(bool(filters_cfg.get("dedupe", True)))
            self.hide_unknown_checkbox.setChecked(bool(filters_cfg.get("hide_unknown", False)))
            self._on_filters_changed()

        def _load_presets_from_config(self) -> None:
            self._presets = {}
            try:
                cfg = load_config()
                gui_cfg = cfg.get("gui_settings", {}) if isinstance(cfg, dict) else {}
                presets = gui_cfg.get("presets", []) or []
                for preset in presets:
                    name = str(preset.get("name") or "").strip()
                    if not name:
                        continue
                    self._presets[name] = preset
            except Exception:
                self._presets = {}
            self._refresh_presets_combo()

        def _save_presets_to_config(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg["presets"] = list(self._presets.values())
                cfg["gui_settings"] = gui_cfg
                self._save_config_async(cfg)
            except Exception:
                return

        def _refresh_presets_combo(self) -> None:
            self.preset_combo.blockSignals(True)
            self.preset_combo.clear()
            self.preset_combo.addItem("-")
            for name in sorted(self._presets.keys()):
                self.preset_combo.addItem(name)
            self.preset_combo.blockSignals(False)

        def _apply_selected_preset(self) -> None:
            name = str(self.preset_combo.currentText() or "").strip()
            if not name or name == "-":
                QtWidgets.QMessageBox.information(self, "Preset", "Bitte ein Preset wählen.")
                return
            preset = self._presets.get(name)
            if not isinstance(preset, dict):
                return
            self._apply_preset_values(preset)

        def _save_preset(self) -> None:
            name = str(self.preset_name_edit.text() or "").strip()
            if not name:
                QtWidgets.QMessageBox.information(self, "Preset", "Bitte einen Namen eingeben.")
                return
            self._presets[name] = {"name": name, **self._collect_preset_values()}
            self._save_presets_to_config()
            self._refresh_presets_combo()
            self.preset_combo.setCurrentText(name)

        def _delete_selected_preset(self) -> None:
            name = str(self.preset_combo.currentText() or "").strip()
            if not name or name == "-":
                return
            if name in self._presets:
                self._presets.pop(name, None)
                self._save_presets_to_config()
                self._refresh_presets_combo()

        def _get_selected_plan_indices(self) -> List[int]:
            try:
                selection = self.table.selectionModel().selectedRows()
            except Exception:
                selection = []
            indices: List[int] = []
            for idx in selection:
                try:
                    source_index = self.results_proxy.mapToSource(idx)
                    row = source_index.row()
                except Exception:
                    row = idx.row()
                row_data = self.results_model.get_row(row)
                if row_data is None:
                    continue
                if int(row_data.meta_index) < 0:
                    continue
                indices.append(int(row_data.meta_index))
            return sorted(set(indices))

        def _start_execute_selected(self) -> None:
            if self._sort_plan is None or self._last_view != "plan":
                QtWidgets.QMessageBox.information(self, "Auswahl ausführen", "Bitte zuerst einen Sortierplan anzeigen.")
                return
            indices = self._get_selected_plan_indices()
            if not indices:
                QtWidgets.QMessageBox.information(self, "Auswahl ausführen", "Bitte Zeilen in der Tabelle auswählen.")
                return
            if not self._confirm_execute_if_warnings():
                return
            self._start_operation("execute", only_indices=indices, conversion_mode="skip")

        def _build_library_report(self) -> dict:
            return build_library_report(self._scan_result, self._sort_plan)

        def _format_library_report_text(self, report: dict) -> str:
            lines: List[str] = []
            scan = report.get("scan") or {}
            plan = report.get("plan") or {}
            if scan:
                lines.append("Scan")
                lines.append(f"Quelle: {scan.get('source_path', '-')}")
                lines.append(f"Gesamt: {scan.get('total_items', 0)}")
                lines.append(f"Unknown: {scan.get('unknown_items', 0)}")
                systems = scan.get("systems") or {}
                if systems:
                    top = list(systems.items())[:5]
                    lines.append("Top Systeme: " + ", ".join(f"{k}={v}" for k, v in top))
                regions = scan.get("regions") or {}
                if regions:
                    top = list(regions.items())[:5]
                    lines.append("Top Regionen: " + ", ".join(f"{k}={v}" for k, v in top))
                lines.append("")
            if plan:
                lines.append("Plan")
                lines.append(f"Ziel: {plan.get('dest_path', '-')}")
                lines.append(f"Aktionen gesamt: {plan.get('total_actions', 0)}")
                actions = plan.get("actions") or {}
                if actions:
                    lines.append("Aktionen: " + ", ".join(f"{k}={v}" for k, v in actions.items()))
                statuses = plan.get("statuses") or {}
                if statuses:
                    lines.append("Status: " + ", ".join(f"{k}={v}" for k, v in statuses.items()))
            if not lines:
                return "Kein Report verfügbar. Bitte zuerst scannen oder planen."
            return "\n".join(lines)

        def _show_library_report(self) -> None:
            report = self._build_library_report()
            text = self._format_library_report_text(report)
            QtWidgets.QMessageBox.information(self, "Bibliothek-Report", text)

        def _save_library_report(self) -> None:
            report = self._build_library_report()
            if not report:
                QtWidgets.QMessageBox.information(self, "Bibliothek-Report", "Kein Report verfügbar.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Report speichern",
                "library_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            try:
                write_json(report, filename)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Bibliothek-Report", f"Speichern fehlgeschlagen:\n{exc}")

        def _get_selected_filter_values(self, widget: object) -> List[str]:
            widget_list = cast(Any, widget)
            selected = [item.text() for item in widget_list.selectedItems()]
            return selected if selected else ["All"]

        def _select_filter_values(self, widget: object, values: Iterable[str]) -> None:
            widget_list = cast(Any, widget)
            widget_list.blockSignals(True)
            widget_list.clearSelection()
            values_set = {str(v) for v in values if str(v)} or {"All"}
            for idx in range(widget_list.count()):
                item = widget_list.item(idx)
                if item.text() in values_set:
                    item.setSelected(True)
            if not widget_list.selectedItems():
                for idx in range(widget_list.count()):
                    item = widget_list.item(idx)
                    if item.text() == "All":
                        item.setSelected(True)
                        break
            widget_list.blockSignals(False)

        def _enforce_all_exclusive(self, widget: object) -> None:
            widget_list = cast(Any, widget)
            selected = [item.text() for item in widget_list.selectedItems()]
            if "All" in selected and len(selected) > 1:
                self._select_filter_values(widget_list, ["All"])

        def _get_filtered_scan_result(self) -> ScanResult:
            if self._scan_result is None:
                raise RuntimeError("No scan result available")

            lang = self._get_selected_filter_values(self.lang_filter)
            ver = str(self.ver_filter.currentText() or "All")
            region = self._get_selected_filter_values(self.region_filter)
            dedupe = bool(self.dedupe_checkbox.isChecked())
            hide_unknown = bool(self.hide_unknown_checkbox.isChecked())
            ext_filter = str(self.ext_filter_edit.text() or "").strip()
            min_size_mb = self._parse_size_mb(self.min_size_edit.text())
            max_size_mb = self._parse_size_mb(self.max_size_edit.text())

            filtered_items = filter_scan_items(
                list(self._scan_result.items),
                language_filter=lang,
                version_filter=ver,
                region_filter=region,
                extension_filter=ext_filter,
                min_size_mb=min_size_mb,
                max_size_mb=max_size_mb,
                dedupe_variants=dedupe,
            )

            if hide_unknown:
                min_conf = self._get_min_confidence()
                filtered_items = [it for it in filtered_items if self._is_confident_for_display(it, min_conf)]

            return ScanResult(
                source_path=self._scan_result.source_path,
                items=filtered_items,
                stats=dict(self._scan_result.stats),
                cancelled=bool(self._scan_result.cancelled),
            )

        def _parse_size_mb(self, value: str) -> Optional[float]:
            try:
                raw = (value or "").strip()
                if not raw:
                    return None
                return float(raw.replace(",", "."))
            except Exception:
                return None

        def _get_min_confidence(self) -> float:
            try:
                cfg = load_config()
            except Exception:
                return 0.95
            try:
                sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
                return float(sorting_cfg.get("confidence_threshold", 0.95))
            except Exception:
                return 0.95

        def _is_confident_for_display(self, item: ScanItem, min_confidence: float) -> bool:
            system = (item.detected_system or "Unknown").strip()
            if not system or system == "Unknown":
                return False
            source = str(item.detection_source or "").lower()
            if source.startswith("dat:"):
                return True
            try:
                conf = float(item.detection_confidence or 0.0)
            except Exception:
                conf = 0.0
            return conf >= min_confidence

        def _refresh_filter_options(self) -> None:
            if self._scan_result is None:
                lang_defaults, ver_defaults, region_defaults = self._load_filter_defaults()
                self.lang_filter.clear()
                self.lang_filter.addItems(lang_defaults)
                self._select_filter_values(self.lang_filter, ["All"])
                self.ver_filter.clear()
                self.ver_filter.addItems(ver_defaults)
                self.region_filter.clear()
                self.region_filter.addItems(region_defaults)
                self._select_filter_values(self.region_filter, ["All"])
                return

            langs = set()
            has_unknown_lang = False
            vers = set()
            has_unknown_ver = False

            regions = set()
            has_unknown_region = False

            for item in self._scan_result.items:
                item_langs = getattr(item, "languages", ()) or ()
                if not item_langs:
                    try:
                        inferred_langs, inferred_ver = infer_languages_and_version_from_name(item.input_path)
                        if inferred_langs:
                            item_langs = inferred_langs
                        if inferred_ver and not getattr(item, "version", None):
                            vers.add(str(inferred_ver))
                    except Exception:
                        pass
                if not item_langs:
                    has_unknown_lang = True
                else:
                    langs.update(item_langs)

                v = getattr(item, "version", None)
                if not v:
                    has_unknown_ver = True
                else:
                    vers.add(str(v))

                r = getattr(item, "region", None)
                if not r:
                    # Fallback parse for older scan items
                    try:
                        r = infer_region_from_name(item.input_path)
                    except Exception:
                        r = None
                if not r or str(r) == "Unknown":
                    has_unknown_region = True
                else:
                    regions.add(str(r))

            current_langs = self._get_selected_filter_values(self.lang_filter)
            current_ver = str(self.ver_filter.currentText() or "All")
            current_regions = self._get_selected_filter_values(self.region_filter)

            self.lang_filter.blockSignals(True)
            self.lang_filter.clear()
            self.lang_filter.addItem("All")
            if has_unknown_lang:
                self.lang_filter.addItem("Unknown")
            for lang in sorted(langs):
                self.lang_filter.addItem(str(lang))
            self.lang_filter.blockSignals(False)
            self._select_filter_values(self.lang_filter, current_langs)

            self.ver_filter.blockSignals(True)
            self.ver_filter.clear()
            self.ver_filter.addItem("All")
            if has_unknown_ver:
                self.ver_filter.addItem("Unknown")
            for v in sorted(vers):
                self.ver_filter.addItem(str(v))
            idx2 = self.ver_filter.findText(current_ver)
            self.ver_filter.setCurrentIndex(idx2 if idx2 >= 0 else 0)
            self.ver_filter.blockSignals(False)

            self.region_filter.blockSignals(True)
            self.region_filter.clear()
            self.region_filter.addItem("All")
            if has_unknown_region:
                self.region_filter.addItem("Unknown")
            for r in sorted(regions):
                self.region_filter.addItem(str(r))
            self.region_filter.blockSignals(False)
            self._select_filter_values(self.region_filter, current_regions)

        def _load_filter_defaults(self) -> Tuple[List[str], List[str], List[str]]:
            lang_values = ["All", "Unknown"]
            ver_values = ["All", "Unknown"]
            region_values = ["All", "Unknown"]

            try:
                cfg = load_config()
                prioritization = cfg.get("prioritization", {}) or {}
                langs = prioritization.get("language_order", []) or []
                regions = prioritization.get("region_order", []) or []
                lang_priority = prioritization.get("language_priorities", {}) or {}
                region_priority = prioritization.get("region_priorities", {}) or {}
                for lang in langs:
                    if str(lang) not in lang_values:
                        lang_values.append(str(lang))
                for region in regions:
                    if str(region) not in region_values:
                        region_values.append(str(region))
                for lang in lang_priority.keys():
                    if str(lang) not in lang_values:
                        lang_values.append(str(lang))
                for region in region_priority.keys():
                    if str(region) not in region_values:
                        region_values.append(str(region))
            except Exception:
                pass

            return lang_values, ver_values, region_values

        def _append_summary_row(self, report: SortReport) -> None:
            text = (
                f"Processed: {report.processed} | Copied: {report.copied} | Moved: {report.moved} | "
                f"Skipped: {report.skipped} | Errors: {len(report.errors)} | Cancelled: {report.cancelled}"
            )
            tooltip = "\n".join(report.errors) if report.errors else ""
            self.results_model.append_row(
                ResultRow(
                    status=text,
                    action=str(report.mode),
                    input_path="(Summary)",
                    name="",
                    detected_system="",
                    security="",
                    signals="",
                    candidates="",
                    planned_target=str(report.dest_path or ""),
                    normalization="",
                    reason="",
                    meta_index=-1,
                    status_tooltip=tooltip,
                )
            )

        def _update_results_empty_state(self) -> None:
            try:
                has_rows = self.results_proxy.rowCount() > 0
                filter_text = str(self.quick_filter_edit.text() or "").strip()
                if not has_rows:
                    if filter_text:
                        self.results_empty_label.setText("Keine Treffer für den aktuellen Filter.")
                    else:
                        self.results_empty_label.setText(
                            "Noch keine Ergebnisse. Starte mit Scan oder Vorschau, um Einträge zu sehen."
                        )
                self.results_empty_label.setVisible(not has_rows)
                self.table.setVisible(has_rows)
            except Exception:
                return

        def _append_log(self, text: str) -> None:
            if not text:
                return
            self._log_helper.append(str(text))

        def _flush_log(self) -> None:
            self._log_helper.flush()

        def _apply_log_filter(self) -> None:
            text = str(self.log_filter_edit.text() or "").strip().lower()
            self._log_helper.apply_filter(text)

        def _on_log_autoscroll_changed(self, _value: int) -> None:
            enabled = bool(self.log_autoscroll_checkbox.isChecked())
            self._log_autoscroll = enabled
            self._log_helper.set_autoscroll(enabled)

        def _apply_quick_filter(self) -> None:
            text = str(self.quick_filter_edit.text() or "").strip()
            if not text:
                try:
                    self.results_proxy.setFilterRegularExpression(QtCore.QRegularExpression())
                except Exception:
                    self.results_proxy.setFilterFixedString("")
                self._update_results_empty_state()
                return
            try:
                pattern = QtCore.QRegularExpression.escape(text)
                regex = QtCore.QRegularExpression(
                    pattern,
                    QtCore.QRegularExpression.PatternOption.CaseInsensitiveOption,
                )
                self.results_proxy.setFilterRegularExpression(regex)
            except Exception:
                self.results_proxy.setFilterFixedString(text)
            self._update_results_empty_state()

        def _get_selected_source_rows(self) -> List[int]:
            rows: List[int] = []
            try:
                selection = self.table.selectionModel().selectedRows()
            except Exception:
                return rows
            for idx in selection:
                try:
                    source_index = self.results_proxy.mapToSource(idx)
                    rows.append(int(source_index.row()))
                except Exception:
                    rows.append(int(idx.row()))
            return sorted(set(rows))

        def _on_table_selection_changed(self, *_args) -> None:
            rows = self._get_selected_source_rows()
            if not rows:
                self.details_input_label.setText("-")
                self.details_target_label.setText("-")
                self.details_status_label.setText("-")
                self.details_system_label.setText("-")
                self.details_reason_label.setText("-")
                return
            row_data = self.results_model.get_row(rows[0])
            if row_data is None:
                return
            self.details_input_label.setText(row_data.input_path or "-")
            self.details_target_label.setText(row_data.planned_target or "-")
            self.details_status_label.setText(row_data.status or "-")
            self.details_system_label.setText(row_data.detected_system or "-")
            self.details_reason_label.setText(row_data.reason or "-")

        def _open_table_context_menu(self, pos) -> None:
            index = self.table.indexAt(pos)
            if not index.isValid():
                return
            try:
                source_index = self.results_proxy.mapToSource(index)
                row = source_index.row()
            except Exception:
                row = index.row()
            row_data = self.results_model.get_row(row)
            if row_data is None:
                return
            menu = QtWidgets.QMenu(self)
            action_copy_path = menu.addAction("Pfad kopieren")
            action_open_input = menu.addAction("Eingabe in Explorer öffnen")
            action_open_target = menu.addAction("Ziel öffnen")
            action_reveal_target = menu.addAction("Zielordner zeigen")
            chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
            if chosen == action_copy_path:
                QtWidgets.QApplication.clipboard().setText(row_data.input_path or "")
            elif chosen == action_open_input:
                self._open_path_in_explorer(row_data.input_path)
            elif chosen == action_open_target:
                self._open_path_in_explorer(row_data.planned_target)
            elif chosen == action_reveal_target:
                target = row_data.planned_target or ""
                if target:
                    self._open_path_in_explorer(str(Path(target).parent))

        def _open_path_in_explorer(self, path: Optional[str]) -> None:
            if not path:
                return
            try:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
            except Exception:
                return

        def _open_command_palette(self) -> None:
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Command Palette")
            dialog.setModal(True)
            dialog.resize(520, 360)
            layout = QtWidgets.QVBoxLayout(dialog)
            filter_edit = QtWidgets.QLineEdit()
            filter_edit.setPlaceholderText("Befehl suchen…")
            list_widget = QtWidgets.QListWidget()
            layout.addWidget(filter_edit)
            layout.addWidget(list_widget, 1)

            actions = self._get_command_actions()

            def refresh():
                query = filter_edit.text().strip().lower()
                list_widget.clear()
                for label, callback in actions:
                    if query and query not in label.lower():
                        continue
                    item = QtWidgets.QListWidgetItem(label)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, callback)
                    list_widget.addItem(item)

            def run_selected():
                item = list_widget.currentItem()
                if item is None:
                    return
                func = item.data(QtCore.Qt.ItemDataRole.UserRole)
                dialog.accept()
                try:
                    func()
                except Exception:
                    return

            filter_edit.textChanged.connect(refresh)
            list_widget.itemActivated.connect(lambda _item: run_selected())
            filter_edit.returnPressed.connect(run_selected)
            refresh()
            filter_edit.setFocus()
            dialog.exec()

        def _get_command_actions(self) -> List[Tuple[str, object]]:
            return [
                ("Navigation: Dashboard", lambda: self.tabs.setCurrentIndex(int(self._tab_index_dashboard))),
                ("Navigation: Sortierung", lambda: self.tabs.setCurrentIndex(int(self._tab_index_sort))),
                ("Navigation: Konvertierungen", lambda: self.tabs.setCurrentIndex(int(self._tab_index_conversions))),
                ("Navigation: IGIR", lambda: self.tabs.setCurrentIndex(int(self._tab_index_igir))),
                ("Navigation: Datenbank", lambda: self.tabs.setCurrentIndex(int(self._tab_index_db))),
                ("Navigation: Einstellungen", lambda: self.tabs.setCurrentIndex(int(self._tab_index_settings))),
                ("Aktion: Scan starten", self._start_scan),
                ("Aktion: Preview Sort (Dry-run)", self._start_preview),
                ("Aktion: Execute Sort", self._start_execute),
                ("Aktion: Cancel", self._cancel),
                ("Log umschalten", self._toggle_log_visibility),
                ("Toggle External Tools", lambda: self.external_tools_checkbox.setChecked(not self.external_tools_checkbox.isChecked())),
                ("Toggle Review Gate", lambda: self.review_gate_checkbox.setChecked(not self.review_gate_checkbox.isChecked())),
                ("Theme: Neo Dark", lambda: self._set_theme_by_name("Neo Dark")),
                ("Theme: Nord Frost", lambda: self._set_theme_by_name("Nord Frost")),
                ("Theme: Solar Light", lambda: self._set_theme_by_name("Solar Light")),
            ]

        def _set_theme_by_name(self, name: str) -> None:
            if name in self._theme_manager.get_theme_names():
                self.theme_combo.setCurrentText(name)
                return
            if self._qt_theme_display and name in self._qt_theme_display:
                self.theme_combo.setCurrentText(name)

        def _init_shell_layout(self) -> None:
            if UIShellController is None or ShellThemeManager is None:
                return
            try:
                cfg = load_config()
                gui_cfg = cfg.get("gui_settings", {}) if isinstance(cfg, dict) else {}
                use_shell = bool(gui_cfg.get("use_shell_layout", True))
            except Exception:
                use_shell = True
            if not use_shell:
                return
            app_instance = QtWidgets.QApplication.instance()
            if app_instance is None:
                return
            try:
                self._shell_controller = UIShellController(
                    theme_mgr=ShellThemeManager(app_instance),
                    pages=self._shell_pages,
                    on_action_scan=self._start_scan,
                    on_action_preview=self._start_preview,
                    on_action_execute=self._start_execute,
                    on_action_cancel=self._cancel,
                )
                if self.layout_combo is not None:
                    try:
                        key = getattr(self._shell_controller, "layout_key", None)
                        idx = self.layout_combo.findData(key)
                        if idx >= 0:
                            self.layout_combo.setCurrentIndex(idx)
                    except Exception:
                        pass
                self._mount_shell_root()
                try:
                    combo = getattr(self._shell_controller, "layout_combo", None)
                    if combo is not None:
                        combo.currentIndexChanged.connect(lambda _idx: self._mount_shell_root())
                except Exception:
                    pass
            except Exception:
                self._shell_controller = None

        def _mount_shell_root(self) -> None:
            controller = self._shell_controller
            if not controller:
                return
            try:
                build_root = getattr(controller, "build_root", None)
                if build_root is None:
                    return
                root = build_root()
                if root is None:
                    return
                if self._shell_stack is None:
                    base = self._base_central or self.centralWidget()
                    if base is None:
                        self.setCentralWidget(root)
                        self._apply_ui_scale(self._ui_scale, force=True)
                        return
                    self._base_central = base
                    stack = QtWidgets.QStackedWidget()
                    stack.addWidget(base)
                    stack.addWidget(root)
                    stack.setCurrentWidget(root)
                    self._shell_stack = stack
                    self.setCentralWidget(stack)
                    self._apply_ui_scale(self._ui_scale, force=True)
                    return
                current = self._shell_stack.currentWidget()
                if current is not None and current is not self._base_central:
                    try:
                        self._shell_stack.removeWidget(current)
                        current.deleteLater()
                    except Exception:
                        pass
                self._shell_stack.addWidget(root)
                self._shell_stack.setCurrentWidget(root)
                self._apply_ui_scale(self._ui_scale, force=True)
            except Exception:
                return

        def _is_qt_widget_alive(self, widget: object | None) -> bool:
            if widget is None:
                return False
            try:
                getattr(widget, "objectName", lambda: "")()
                return True
            except RuntimeError:
                return False
            except Exception:
                return True

        def _on_header_theme_changed(self, name: str) -> None:
            if self._syncing_theme:
                return
            self._syncing_theme = True
            try:
                combo = self.theme_combo
                if combo is not None and combo.currentText() != name:
                    combo.setCurrentText(name)
            finally:
                self._syncing_theme = False

        def _sync_theme_combos(self) -> None:
            if self._syncing_theme:
                return
            self._syncing_theme = True
            try:
                if not self._is_qt_widget_alive(self.theme_combo):
                    return
                combo = self.theme_combo
                current = combo.currentText() if combo is not None else ""
                header_combo = self.header_theme_combo
                if not self._is_qt_widget_alive(header_combo):
                    self.header_theme_combo = None
                    return
                if header_combo is not None and header_combo.currentText() != current:
                    header_combo.setCurrentText(current)
            finally:
                self._syncing_theme = False

        def _build_theme_previews(self) -> None:
            try:
                self.theme_preview_list.clear()
            except Exception:
                return
            for name in self._theme_manager.get_theme_names():
                theme = self._theme_manager.get_theme(name)
                item = QtWidgets.QListWidgetItem(name)
                try:
                    if theme and theme.colors:
                        item.setBackground(QtGui.QColor(theme.colors.background))
                        item.setForeground(QtGui.QColor(theme.colors.text))
                except Exception:
                    pass
                self.theme_preview_list.addItem(item)

        def _on_review_gate_changed(self, _value: int) -> None:
            self._update_safety_pill()

        def _on_external_tools_changed(self, _value: int) -> None:
            self._set_external_tools_enabled(bool(self.external_tools_checkbox.isChecked()))

        def _set_external_tools_enabled(self, enabled: bool) -> None:
            self._external_tools_enabled = bool(enabled)
            for btn in (
                self.btn_igir_plan,
                self.btn_igir_execute,
                self.btn_igir_probe,
                self.btn_igir_browse,
            ):
                try:
                    btn.setEnabled(self._external_tools_enabled)
                except Exception:
                    continue
            try:
                igir_running = self._igir_thread is not None and self._igir_thread.isRunning()
            except Exception:
                igir_running = False
            try:
                self.btn_igir_cancel.setEnabled(igir_running or self._external_tools_enabled)
            except Exception:
                pass
            if hasattr(self, "tools_group"):
                self.tools_group.setEnabled(self._external_tools_enabled)
            self._update_safety_pill()

        def _confirm_execute_if_warnings(self) -> bool:
            if not self.review_gate_checkbox.isChecked():
                return True
            if not self._has_warnings:
                return True
            result = QtWidgets.QMessageBox.warning(
                self,
                "Review Gate",
                "Es gibt Warnungen oder unsichere Einträge im Plan. Trotzdem ausführen?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            return result == QtWidgets.QMessageBox.StandardButton.Yes

        def _update_safety_pill(self) -> None:
            if not self.review_gate_checkbox.isChecked():
                self.pill_safety.setText("Gate: Off")
                self.pill_safety.setStyleSheet("padding: 2px 8px; border-radius: 10px; background: #f5c542;")
                return
            if self._has_warnings:
                self.pill_safety.setText("Warnings")
                self.pill_safety.setStyleSheet("padding: 2px 8px; border-radius: 10px; background: #f28b82;")
            else:
                self.pill_safety.setText("Safe")
                self.pill_safety.setStyleSheet("padding: 2px 8px; border-radius: 10px; background: #d7f7c2;")

        def _update_stepper(self, phase: str) -> None:
            active_style = "padding: 4px 8px; border-radius: 10px; background: #cfe8ff;"
            inactive_style = "padding: 4px 8px; border-radius: 10px; background: #f0f0f0;"
            if phase == "scan":
                self.stepper_scan.setStyleSheet(active_style)
                self.stepper_plan.setStyleSheet(inactive_style)
                self.stepper_execute.setStyleSheet(inactive_style)
            elif phase == "plan":
                self.stepper_scan.setStyleSheet(inactive_style)
                self.stepper_plan.setStyleSheet(active_style)
                self.stepper_execute.setStyleSheet(inactive_style)
            elif phase == "execute":
                self.stepper_scan.setStyleSheet(inactive_style)
                self.stepper_plan.setStyleSheet(inactive_style)
                self.stepper_execute.setStyleSheet(active_style)
            else:
                self.stepper_scan.setStyleSheet(inactive_style)
                self.stepper_plan.setStyleSheet(inactive_style)
                self.stepper_execute.setStyleSheet(inactive_style)

        def _priority_value(self, label: str) -> int:
            value = str(label or "").strip().lower()
            if value == "high":
                return 0
            if value == "low":
                return 2
            return 1

        def _queue_or_run(self, op: str, label: str, func) -> None:
            priority = self._priority_value(self.queue_priority_combo.currentText())
            if self.queue_mode_checkbox.isChecked() or self._job_active is not None:
                self._enqueue_job(op, label, func, priority)
                return
            func()

        def _job_int(self, value: object, default: int = 0) -> int:
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return int(default)
                try:
                    return int(float(text))
                except Exception:
                    return int(default)
            return int(default)

        def _activate_main_tab(self) -> None:
            try:
                if hasattr(self, "tabs") and hasattr(self, "_tab_index_main"):
                    self.tabs.setCurrentIndex(int(self._tab_index_main))
            except Exception:
                return

        def _enqueue_job(self, op: str, label: str, func, priority: int) -> None:
            self._job_counter += 1
            job = {
                "id": self._job_counter,
                "op": op,
                "label": label,
                "priority": priority,
                "status": "queued",
                "func": func,
            }
            self._job_queue.append(job)
            sort_job_queue(self._job_queue)
            self._refresh_job_queue()
            self._maybe_start_next_job()

        def _maybe_start_next_job(self) -> None:
            if self._job_active is not None:
                return
            if self._job_paused:
                return
            if not self._job_queue:
                return
            job = self._job_queue[0]
            job["status"] = "running"
            self._job_active = job
            self._refresh_job_queue()
            try:
                job_func = job.get("func")
                if callable(job_func):
                    job_func()
            except Exception:
                job["status"] = "error"
                self._job_active = None
                self._refresh_job_queue()

        def _complete_job(self, op: str) -> None:
            if not self._job_active:
                return
            if str(self._job_active.get("op")) != str(op):
                return
            try:
                self._job_queue.remove(self._job_active)
            except Exception:
                pass
            self._job_active = None
            if self._current_op == op:
                self._current_op = None
            self._refresh_job_queue()
            self._maybe_start_next_job()

        def _refresh_job_queue(self) -> None:
            try:
                self.queue_list.clear()
                for job in self._job_queue:
                    priority = self._job_int(job.get("priority", 1), 1)
                    label = str(job.get("label", "job"))
                    status = str(job.get("status", "queued"))
                    pid = self._job_int(job.get("id", 0), 0)
                    prio_text = {0: "High", 1: "Normal", 2: "Low"}.get(priority, "Normal")
                    self.queue_list.addItem(f"#{pid} [{prio_text}] {label} - {status}")
            except Exception:
                return
            self._update_header_pills()

        def _pause_jobs(self) -> None:
            self._job_paused = True
            self.queue_pause_btn.setEnabled(False)
            self.queue_resume_btn.setEnabled(True)
            self.status_label.setText("Jobs pausiert")
            self._update_header_pills()

        def _resume_jobs(self) -> None:
            self._job_paused = False
            self.queue_pause_btn.setEnabled(True)
            self.queue_resume_btn.setEnabled(False)
            self._maybe_start_next_job()
            self._update_header_pills()

        def _clear_job_queue(self) -> None:
            self._job_queue = [job for job in self._job_queue if job is self._job_active]
            self._refresh_job_queue()

        def _toggle_log_visibility(self) -> None:
            self._set_log_visible(not self._log_visible)

        def _on_igir_advanced_toggle(self, state: int) -> None:
            self._set_igir_advanced_visible(state == QtCore.Qt.CheckState.Checked)

        def _set_igir_advanced_visible(self, visible: bool) -> None:
            if hasattr(self, "_igir_cfg_group"):
                self._igir_cfg_group.setVisible(bool(visible))

        def _set_log_visible(self, visible: bool, persist: bool = True) -> None:
            self._log_visible = bool(visible)
            if hasattr(self, "log_dock"):
                self.log_dock.setVisible(self._log_visible)
            self.log_toggle_btn.setText("Log ausblenden" if self._log_visible else "Log anzeigen")
            if hasattr(self, "header_log_btn"):
                self.header_log_btn.setText("Log" if not self._log_visible else "Log ▾")
            if persist:
                self._save_log_visibility()

        def _rom_display_name(self, input_path: str) -> str:
            return rom_display_name(input_path)

        def _format_confidence(self, value: Optional[float]) -> str:
            return format_confidence(value)

        def _format_signals(self, item: object, default: str = "-") -> str:
            return format_signals(item, default=default)

        def _format_candidates(self, item: object) -> str:
            return format_candidates(item)

        def _choose_source(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select source folder")
            if directory:
                self._set_source_text(directory)
                self._append_log(f"Source set: {directory}")

        def _choose_dest(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select destination folder")
            if directory:
                self._set_dest_text(directory)
                self._append_log(f"Destination set: {directory}")

        def _choose_output(self) -> None:
            if self.output_edit is None:
                return
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output folder")
            if directory:
                self.output_edit.setText(directory)
                self._append_log(f"External output set: {directory}")

        def _choose_temp(self) -> None:
            if self.temp_edit is None:
                return
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select temp folder")
            if directory:
                self.temp_edit.setText(directory)
                self._append_log(f"External temp set: {directory}")

        def _on_drop_source(self, path: str) -> None:
            self._set_source_text(path)
            self._append_log(f"DnD source: {path}")

        def _on_drop_dest(self, path: str) -> None:
            self._set_dest_text(path)
            self._append_log(f"DnD destination: {path}")

        def _set_source_text(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._syncing_paths = True
            try:
                self.source_edit.setText(text)
                if hasattr(self, "dashboard_source_edit"):
                    self.dashboard_source_edit.setText(text)
                if hasattr(self, "conversion_source_edit"):
                    self.conversion_source_edit.setText(text)
                if hasattr(self, "igir_source_edit"):
                    self.igir_source_edit.setText(text)
            finally:
                self._syncing_paths = False

        def _set_dest_text(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._syncing_paths = True
            try:
                self.dest_edit.setText(text)
                if hasattr(self, "dashboard_dest_edit"):
                    self.dashboard_dest_edit.setText(text)
                if hasattr(self, "conversion_dest_edit"):
                    self.conversion_dest_edit.setText(text)
                if hasattr(self, "igir_dest_edit"):
                    self.igir_dest_edit.setText(text)
            finally:
                self._syncing_paths = False

        def _on_source_text_changed(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._set_source_text(text)
            self._refresh_dashboard()

        def _on_dest_text_changed(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._set_dest_text(text)
            self._refresh_dashboard()

        def _open_destination(self) -> None:
            directory = self.dest_edit.text().strip()
            if not directory:
                QtWidgets.QMessageBox.information(self, "Kein Ziel", "Bitte zuerst einen Zielordner wählen.")
                return
            try:
                url = QtCore.QUrl.fromLocalFile(directory)
                if not QtGui.QDesktopServices.openUrl(url):
                    QtWidgets.QMessageBox.warning(self, "Öffnen fehlgeschlagen", "Zielordner konnte nicht geöffnet werden.")
            except Exception:
                QtWidgets.QMessageBox.warning(self, "Öffnen fehlgeschlagen", "Zielordner konnte nicht geöffnet werden.")

        def _on_drop_output(self, path: str) -> None:
            if self.output_edit is None:
                return
            self.output_edit.setText(path)
            self._append_log(f"DnD external output: {path}")

        def _on_drop_temp(self, path: str) -> None:
            if self.temp_edit is None:
                return
            self.temp_edit.setText(path)
            self._append_log(f"DnD external temp: {path}")

        def _set_running(self, running: bool) -> None:
            if running:
                self._ui_fsm.transition(UIState.EXECUTING)
            else:
                self._ui_fsm.transition(UIState.IDLE)
            self.btn_scan.setEnabled(not running)
            self.btn_preview.setEnabled(not running)
            self.btn_execute.setEnabled(not running)
            self.btn_execute_convert.setEnabled(not running)
            self.btn_audit.setEnabled(not running)
            self.btn_export_audit_csv.setEnabled(not running and self._audit_report is not None)
            self.btn_export_audit_json.setEnabled(not running and self._audit_report is not None)
            self.btn_export_scan_csv.setEnabled(not running and self._scan_result is not None)
            self.btn_export_scan_json.setEnabled(not running and self._scan_result is not None)
            self.btn_export_plan_csv.setEnabled(not running and self._sort_plan is not None)
            self.btn_export_plan_json.setEnabled(not running and self._sort_plan is not None)
            self.btn_export_frontend_es.setEnabled(not running and self._sort_plan is not None)
            self.btn_export_frontend_launchbox.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_audit_csv.setEnabled(not running and self._audit_report is not None)
            self.menu_export_audit_json.setEnabled(not running and self._audit_report is not None)
            self.menu_export_scan_csv.setEnabled(not running and self._scan_result is not None)
            self.menu_export_scan_json.setEnabled(not running and self._scan_result is not None)
            self.menu_export_plan_csv.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_plan_json.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_frontend_es.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_frontend_launchbox.setEnabled(not running and self._sort_plan is not None)
            self.btn_cancel.setEnabled(running)
            self.btn_resume.setEnabled(not running and self._can_resume())
            self.btn_retry_failed.setEnabled(not running and self._can_retry_failed())
            self.header_btn_cancel.setEnabled(running)

            self.btn_source.setEnabled(not running)
            self.btn_dest.setEnabled(not running)
            self.btn_open_dest.setEnabled(not running)
            if self.btn_output is not None:
                self.btn_output.setEnabled(not running)
            if self.btn_temp is not None:
                self.btn_temp.setEnabled(not running)
            if self.output_edit is not None:
                self.output_edit.setEnabled(not running)
            if self.temp_edit is not None:
                self.temp_edit.setEnabled(not running)
            self.rebuild_checkbox.setEnabled(not running)
            self._sync_rebuild_controls(running=running)
            self.btn_clear_filters.setEnabled(not running)
            self.btn_add_dat.setEnabled(not running)
            self.btn_refresh_dat.setEnabled(not running)
            self.btn_cancel_dat.setEnabled(not running and self._dat_index_cancel_token is not None)
            self.btn_manage_dat.setEnabled(not running)
            self.btn_open_overrides.setEnabled(not running)
            self.dat_auto_load_checkbox.setEnabled(not running)
            self.btn_clear_dat_cache.setEnabled(not running)
            if not running:
                self._update_resume_buttons()
            self._is_running = bool(running)
            self._refresh_dashboard()
            self._update_quick_actions()
            self._update_header_pills()

        def _has_required_paths(self) -> bool:
            source = self.source_edit.text().strip() if self.source_edit is not None else ""
            dest = self.dest_edit.text().strip() if self.dest_edit is not None else ""
            return bool(source and dest)

        def _update_quick_actions(self) -> None:
            ready = self._has_required_paths()
            enabled = ready and not self._is_running
            try:
                if hasattr(self, "btn_dash_scan"):
                    self.btn_dash_scan.setEnabled(enabled)
                if hasattr(self, "btn_dash_preview"):
                    self.btn_dash_preview.setEnabled(enabled)
                if hasattr(self, "btn_dash_execute"):
                    self.btn_dash_execute.setEnabled(enabled)
                self.header_btn_scan.setEnabled(enabled)
                self.header_btn_preview.setEnabled(enabled)
                self.header_btn_execute.setEnabled(enabled)
            except Exception:
                pass
            return

        def _refresh_dashboard(self) -> None:
            if not hasattr(self, "dashboard_status_label"):
                return
            source = self.source_edit.text().strip() if self.source_edit is not None else ""
            dest = self.dest_edit.text().strip() if self.dest_edit is not None else ""
            status = self.status_label.text() if self.status_label is not None else "-"
            dat_status = self.dat_status.text() if self.dat_status is not None else "-"
            self.dashboard_source_label.setText(source or "-")
            self.dashboard_dest_label.setText(dest or "-")
            self.dashboard_status_label.setText(status or "-")
            self.dashboard_dat_label.setText(dat_status or "-")
            if hasattr(self, "main_source_label"):
                self.main_source_label.setText(source or "-")
            if hasattr(self, "main_dest_label"):
                self.main_dest_label.setText(dest or "-")
            self._sync_sidebar_status()
            self._update_quick_actions()

        def _sync_sidebar_status(self) -> None:
            if hasattr(self, "sidebar_status_label"):
                try:
                    self.sidebar_status_label.setText(self.status_label.text() if self.status_label else "-")
                except Exception:
                    pass
            if hasattr(self, "sidebar_summary_label"):
                try:
                    self.sidebar_summary_label.setText(self.summary_label.text() if self.summary_label else "-")
                except Exception:
                    pass
            self._update_header_pills()

        def _safe_set_label(self, label_attr: str, text: str, style: str | None = None) -> bool:
            label = getattr(self, label_attr, None)
            if label is None:
                return False
            try:
                label.setText(text)
                if style is not None:
                    label.setStyleSheet(style)
            except RuntimeError:
                try:
                    setattr(self, label_attr, None)
                except Exception:
                    pass
                return False
            return True

        def _update_header_pills(self) -> None:
            if self._is_running:
                self._safe_set_label(
                    "pill_status",
                    "Running",
                    "padding: 2px 8px; border-radius: 10px; background: #cfe8ff;",
                )
            else:
                self._safe_set_label(
                    "pill_status",
                    "Idle",
                    "padding: 2px 8px; border-radius: 10px; background: #e8e8e8;",
                )
            queue_len = len(self._job_queue)
            if self._job_paused:
                self._safe_set_label(
                    "pill_queue",
                    f"Queue: {queue_len}",
                    "padding: 2px 8px; border-radius: 10px; background: #f5c542;",
                )
            else:
                self._safe_set_label(
                    "pill_queue",
                    f"Queue: {queue_len}",
                    "padding: 2px 8px; border-radius: 10px; background: #e8e8e8;",
                )
            try:
                dat_text = self.dat_status.text() if self.dat_status is not None else "-"
            except Exception:
                dat_text = "-"
            self._safe_set_label("pill_dat", dat_text or "DAT: -")

        def _sync_rebuild_controls(self, *, running: bool = False) -> None:
            try:
                rebuild_active = bool(self.rebuild_checkbox.isChecked())
            except Exception:
                rebuild_active = False

            if rebuild_active:
                if self.mode_combo.currentText() != "copy":
                    self.mode_combo.setCurrentText("copy")
                if self.conflict_combo.currentText() != "skip":
                    self.conflict_combo.setCurrentText("skip")

            self.mode_combo.setEnabled(not running and not rebuild_active)
            self.conflict_combo.setEnabled(not running and not rebuild_active)

        def _on_rebuild_toggle(self, _state: int) -> None:
            self._sync_rebuild_controls(running=False)

        def _can_resume(self) -> bool:
            try:
                return Path(self._resume_path).exists()
            except Exception:
                return False

        def _can_retry_failed(self) -> bool:
            return bool(self._failed_action_indices) and self._sort_plan is not None

        def _update_resume_buttons(self) -> None:
            if self._worker is not None or self._thread is not None:
                return
            self.btn_resume.setEnabled(self._can_resume())
            self.btn_retry_failed.setEnabled(self._can_retry_failed())

        def _validate_paths(self, *, require_dest: bool = True) -> Optional[dict]:
            source = self.source_edit.text().strip()
            dest = self.dest_edit.text().strip()
            if self.output_edit is None:
                output_dir = ""
            else:
                try:
                    output_dir = self.output_edit.text().strip()
                except RuntimeError:
                    output_dir = ""
            if self.temp_edit is None:
                temp_dir = ""
            else:
                try:
                    temp_dir = self.temp_edit.text().strip()
                except RuntimeError:
                    temp_dir = ""
            if not source:
                try:
                    self._append_log("Validation failed: missing source path")
                except Exception:
                    pass
                QtWidgets.QMessageBox.warning(self, "Quelle fehlt", "Bitte einen Quellordner wählen.")
                return None
            if require_dest and not dest:
                try:
                    self._append_log("Validation failed: missing destination path")
                except Exception:
                    pass
                QtWidgets.QMessageBox.warning(self, "Ziel fehlt", "Bitte einen Zielordner wählen.")
                return None
            return {"source": source, "dest": dest, "output_dir": output_dir, "temp_dir": temp_dir}

        def _start_operation(
            self,
            op: str,
            *,
            start_index: int = 0,
            only_indices: Optional[List[int]] = None,
            resume_path: Optional[str] = None,
            conversion_mode: ConversionMode = "all",
        ) -> None:
            values = self._validate_paths(require_dest=op in ("plan", "execute"))
            if values is None:
                return

            self._current_op = op

            try:
                self._append_log(f"Starting {op}…")
            except Exception:
                pass

            if op in ("plan", "execute") and self._scan_result is None:
                QtWidgets.QMessageBox.information(self, "Keine Scan-Ergebnisse", "Bitte zuerst scannen.")
                return
            if op == "execute" and self._sort_plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Sortierplan", "Bitte zuerst Vorschau ausführen.")
                return

            self._activate_main_tab()

            self._cancel_token = CancelToken()
            self.progress.setValue(0)
            self.status_label.setText("Starte…")

            if op == "scan":
                self._scan_result = None
                self._sort_plan = None
                self._has_warnings = False
                self.results_model.clear()
                self._update_results_empty_state()
                self.log_view.clear()

            signals = WorkerSignals()
            signals.phase_changed.connect(self._on_phase_changed)
            signals.progress.connect(self._on_progress)
            signals.log.connect(self._append_log)
            signals.action_status.connect(self._on_action_status)
            signals.finished.connect(lambda payload: self._on_finished(op, payload))
            signals.failed.connect(self._on_failed)

            self._thread = QtCore.QThread()

            scan_for_plan = None
            if op == "plan":
                scan_for_plan = self._get_filtered_scan_result()

            if op == "execute" and resume_path is None:
                resume_path = self._resume_path

            self._worker = OperationWorker(
                op=op,
                source=values["source"],
                dest=values["dest"],
                output_dir=values["output_dir"],
                temp_dir=values["temp_dir"],
                mode=str(self.mode_combo.currentText()),
                on_conflict=str(self.conflict_combo.currentText()),
                conversion_mode=conversion_mode,
                scan_result=scan_for_plan if scan_for_plan is not None else self._scan_result,
                sort_plan=self._sort_plan,
                start_index=start_index,
                only_indices=only_indices,
                resume_path=resume_path,
                cancel_token=self._cancel_token,
                signals=signals,
            )
            worker = self._worker
            worker.moveToThread(self._thread)
            self._thread.started.connect(worker.run)
            self._thread.finished.connect(self._thread.deleteLater)
            signals.finished.connect(worker.deleteLater)
            signals.failed.connect(worker.deleteLater)
            self._backend_worker = BackendWorkerHandle(self._thread, self._cancel_token)

            self._set_running(True)
            self._thread.start()

        def _start_scan(self) -> None:
            self._queue_or_run("scan", "Scan", self._start_scan_now)

        def _start_scan_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            try:
                self._append_log("Scan requested")
            except Exception:
                pass
            self._start_operation("scan")

        def _start_preview(self) -> None:
            self._queue_or_run("plan", "Preview", self._start_preview_now)

        def _start_preview_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("plan")

        def _start_execute(self) -> None:
            self._queue_or_run("execute", "Execute", self._start_execute_now)

        def _quick_execute_or_preview(self) -> None:
            if self._sort_plan is not None and self._last_view == "plan":
                self._start_execute()
            else:
                self._start_preview()

        def _start_execute_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            if not self._confirm_execute_if_warnings():
                return
            self._start_operation("execute", conversion_mode="skip")

        def _start_convert_only(self) -> None:
            self._queue_or_run("execute", "Convert only", self._start_convert_only_now)

        def _start_convert_only_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            if not self._confirm_execute_if_warnings():
                return
            self._start_operation("execute", conversion_mode="only")

        def _start_audit(self) -> None:
            self._queue_or_run("audit", "Audit", self._start_audit_now)

        def _start_audit_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("audit")

        def _start_resume(self) -> None:
            if not self._can_resume():
                QtWidgets.QMessageBox.information(self, "Kein Fortsetzen möglich", "Kein Fortsetzungsstand gefunden.")
                return
            try:
                state = load_sort_resume_state(self._resume_path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Fortsetzen fehlgeschlagen", f"Fortsetzungsstand konnte nicht geladen werden: {exc}")
                return
            self._sort_plan = state.sort_plan
            self._populate_plan_table(state.sort_plan)
            self._failed_action_indices.clear()
            self._update_resume_buttons()
            self._start_operation("execute", start_index=state.resume_from_index)

        def _start_retry_failed(self) -> None:
            if not self._can_retry_failed():
                QtWidgets.QMessageBox.information(self, "Keine fehlgeschlagenen Aktionen", "Es gibt keine fehlgeschlagenen Aktionen zum Wiederholen.")
                return
            indices = sorted(self._failed_action_indices)
            self._failed_action_indices.clear()
            self._update_resume_buttons()
            self._start_operation("execute", only_indices=indices)

        def _cancel(self) -> None:
            self._append_log("Cancel requested by user")
            try:
                self.status_label.setText("Abbrechen…")
            except Exception:
                pass
            self._cancel_token.cancel()
            if self._backend_worker is not None:
                self._backend_worker.cancel()
            if self._export_cancel_token is not None:
                try:
                    self._export_cancel_token.cancel()
                except Exception:
                    pass
            self.btn_cancel.setEnabled(False)

        def _on_phase_changed(self, phase: str, total: int) -> None:
            self._update_stepper(phase)
            if phase == "scan":
                self._ui_fsm.transition(UIState.SCANNING)
                self.status_label.setText("Scan läuft…")
                self.progress.setRange(0, 100)
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, 100)
                    self.dashboard_progress.setValue(0)
            elif phase == "plan":
                self._ui_fsm.transition(UIState.PLANNING)
                self.status_label.setText("Plane…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, max(1, int(total)))
                    self.dashboard_progress.setValue(0)
            elif phase == "execute":
                self._ui_fsm.transition(UIState.EXECUTING)
                self.status_label.setText("Ausführen…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, max(1, int(total)))
                    self.dashboard_progress.setValue(0)
            elif phase == "audit":
                self._ui_fsm.transition(UIState.AUDITING)
                self.status_label.setText("Prüfe Konvertierungen…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, max(1, int(total)))
                    self.dashboard_progress.setValue(0)

        def _on_progress(self, current: int, total: int) -> None:
            if total and total > 0:
                self.progress.setRange(0, int(total))
                self.progress.setValue(int(current))
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, int(total))
                    self.dashboard_progress.setValue(int(current))
            else:
                self.progress.setRange(0, 0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, 0)

        def _cleanup_thread(self) -> None:
            if self._thread is not None:
                self._thread.quit()
                self._thread.wait(5000)
            self._thread = None
            self._worker = None

        def _populate_scan_table(self, scan: ScanResult) -> None:
            rows: List[Any] = []
            self._table_items = list(scan.items)
            min_conf = self._get_min_confidence()
            for row_index, item in enumerate(scan.items):
                status_text = "found"
                status_tooltip = ""
                status_color = None
                try:
                    source = str(item.detection_source or "-")
                    exact = "ja" if getattr(item, "is_exact", False) else "nein"
                    status_tooltip = f"Quelle: {source}\nExact: {exact}"
                except Exception:
                    status_tooltip = ""
                if not self._is_confident_for_display(item, min_conf):
                    status_text = "unknown/low-confidence"
                    status_color = "#b00020"
                rows.append(
                    ResultRow(
                        status=status_text,
                        action="scan",
                        input_path=str(item.input_path or ""),
                        name=self._rom_display_name(item.input_path),
                        detected_system=str(item.detected_system or ""),
                        security=self._format_confidence(item.detection_confidence),
                        signals=self._format_signals(item),
                        candidates=self._format_candidates(item),
                        planned_target="",
                        normalization=self._format_normalization_hint(item.input_path, item.detected_system),
                        reason=self._format_reason(item),
                        meta_index=row_index,
                        status_tooltip=status_tooltip,
                        status_color=status_color,
                    )
                )

            self.results_model.set_rows(rows)
            try:
                self.results_proxy.invalidate()
            except Exception:
                pass

            try:
                self.status_label.setText(
                    f"Scan results: {len(scan.items)} (filtered from {len(self._scan_result.items) if self._scan_result else len(scan.items)})"
                )
            except Exception:
                pass

            try:
                min_conf = self._get_min_confidence()
                unknown_count = sum(1 for item in scan.items if not self._is_confident_for_display(item, min_conf))
                self.summary_label.setText(f"{len(scan.items)} gesamt | {unknown_count} unbekannt/niedrige Sicherheit")
                self._has_warnings = unknown_count > 0
            except Exception:
                self.summary_label.setText("-")

            self._sync_sidebar_status()
            self._update_safety_pill()

            self._update_results_empty_state()

        def _populate_plan_table(self, plan: SortPlan) -> None:
            rows: List[Any] = []
            self._table_items = []
            warnings = 0
            for row_index, act in enumerate(plan.actions):
                status_text = str(act.error or act.status)
                status_color = None
                tooltip = ""
                if act.error:
                    tooltip = str(act.error)
                    status_color = "#b00020"
                    warnings += 1
                elif str(act.status).lower().startswith(("error", "skipped")):
                    warnings += 1
                rows.append(
                    ResultRow(
                        status=status_text,
                        action=str(act.action),
                        input_path=str(act.input_path or ""),
                        name=self._rom_display_name(act.input_path),
                        detected_system=str(act.detected_system or ""),
                        security="",
                        signals="",
                        candidates="",
                        planned_target=str(act.planned_target_path or ""),
                        normalization=self._format_normalization_hint(act.input_path, act.detected_system),
                        reason="",
                        meta_index=row_index,
                        status_tooltip=tooltip,
                        status_color=status_color,
                    )
                )

            self._has_warnings = warnings > 0
            self.results_model.set_rows(rows)
            try:
                self.results_proxy.invalidate()
            except Exception:
                pass

            try:
                planned = sum(1 for act in plan.actions if str(act.status).startswith("planned"))
                skipped = sum(1 for act in plan.actions if str(act.status).startswith("skipped"))
                errors = sum(1 for act in plan.actions if str(act.status).startswith("error"))
                converts = sum(1 for act in plan.actions if str(act.action) == "convert")
                renames = sum(1 for act in plan.actions if "rename" in str(act.status))
                self.summary_label.setText(
                    f"{planned} geplant | {converts} konvertieren | {renames} umbenennen | {skipped} übersprungen | {errors} Fehler"
                )
            except Exception:
                self.summary_label.setText("-")

            self._sync_sidebar_status()
            self._update_safety_pill()

            self._update_results_empty_state()

        def _populate_audit_table(self, report: ConversionAuditReport) -> None:
            rows: List[Any] = []
            self._table_items = []
            for row_index, item in enumerate(report.items):
                suggestion = item.current_extension
                if item.recommended_extension and item.recommended_extension != item.current_extension:
                    suggestion = f"{item.current_extension} -> {item.recommended_extension}".strip()

                action = "convert" if item.status == "should_convert" else "keep"
                status = item.status
                if item.reason:
                    status = f"{status}: {item.reason}"

                rows.append(
                    ResultRow(
                        status=status,
                        action=action,
                        input_path=str(item.input_path or ""),
                        name=self._rom_display_name(item.input_path),
                        detected_system=str(item.detected_system or ""),
                        security="",
                        signals="",
                        candidates="",
                        planned_target=suggestion,
                        normalization="-",
                        reason=str(item.reason or ""),
                        meta_index=row_index,
                    )
                )

            self.results_model.set_rows(rows)
            try:
                self.results_proxy.invalidate()
            except Exception:
                pass

            try:
                totals = report.totals or {}
                self.summary_label.setText(
                    " | ".join(f"{key} {totals.get(key, 0)}" for key in sorted(totals.keys()))
                )
            except Exception:
                self.summary_label.setText("-")

            self._sync_sidebar_status()
            self._has_warnings = False
            self._update_safety_pill()

            self._update_results_empty_state()

        def _on_action_status(self, row_index: int, status: str) -> None:
            try:
                row = int(row_index)
                text = str(status)
                tooltip = text if text.lower().startswith("error") or len(text) > 80 else None
                if text.lower().startswith("error"):
                    self._failed_action_indices.add(row)
                    self._update_resume_buttons()
                    self.results_model.update_status(row, text, tooltip=tooltip, color="#b00020")
                else:
                    self.results_model.update_status(row, text, tooltip=tooltip)
            except Exception:
                # UI must not crash on status update
                return

        def _audit_report_to_dict(self, report: ConversionAuditReport) -> dict:
            return audit_report_to_dict(report)

        def _scan_report_to_dict(self, scan: ScanResult) -> dict:
            return scan_report_to_dict(scan)

        def _plan_report_to_dict(self, plan: SortPlan) -> dict:
            return plan_report_to_dict(plan)

        def _export_scan_json(self) -> None:
            scan = self._scan_result
            if scan is None:
                QtWidgets.QMessageBox.information(self, "Kein Scan", "Bitte zuerst scannen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Scan JSON",
                "scan_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            self._run_export_task(
                "Scan JSON",
                lambda: write_json(self._scan_report_to_dict(scan), filename),
            )

        def _export_scan_csv(self) -> None:
            scan = self._scan_result
            if scan is None:
                QtWidgets.QMessageBox.information(self, "Kein Scan", "Bitte zuerst scannen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Scan CSV",
                "scan_report.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Scan CSV", lambda: write_scan_csv(scan, filename))

        def _export_plan_json(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Plan JSON",
                "plan_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            self._run_export_task(
                "Plan JSON",
                lambda: write_json(self._plan_report_to_dict(plan), filename),
            )

        def _export_plan_csv(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Plan CSV",
                "plan_report.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Plan CSV", lambda: write_plan_csv(plan, filename))

        def _export_frontend_es(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save EmulationStation gamelist",
                "gamelist.xml",
                "XML Files (*.xml)",
            )
            if not filename:
                return
            self._run_export_task("Frontend EmulationStation", lambda: write_emulationstation_gamelist(plan, filename))

        def _export_frontend_launchbox(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save LaunchBox CSV",
                "launchbox_export.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Frontend LaunchBox", lambda: write_launchbox_csv(plan, filename))

        def _export_audit_json(self) -> None:
            report = self._audit_report
            if report is None:
                QtWidgets.QMessageBox.information(self, "Kein Audit", "Bitte zuerst Konvertierungen prüfen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Audit JSON",
                "audit_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            self._run_export_task(
                "Audit JSON",
                lambda: write_json(self._audit_report_to_dict(report), filename),
            )

        def _export_audit_csv(self) -> None:
            report = self._audit_report
            if report is None:
                QtWidgets.QMessageBox.information(self, "Kein Audit", "Bitte zuerst Konvertierungen prüfen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Audit CSV",
                "audit_report.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Audit CSV", lambda: write_audit_csv(report, filename))

        def _run_export_task(self, label: str, task) -> None:
            if self._export_thread is not None and self._export_thread.isRunning():
                QtWidgets.QMessageBox.information(self, "Export läuft", "Ein Export ist bereits aktiv.")
                return

            self._export_cancel_token = CancelToken()

            def task_with_cancel(cancel_token: CancelToken) -> None:
                if cancel_token.is_cancelled():
                    raise RuntimeError("Export cancelled")
                task()
                if cancel_token.is_cancelled():
                    raise RuntimeError("Export cancelled")

            thread = QtCore.QThread()
            worker = ExportWorker(label, task_with_cancel, self._export_cancel_token)
            worker.moveToThread(thread)

            worker.finished.connect(lambda lbl: self._on_export_finished(lbl))
            worker.failed.connect(lambda msg: self._on_export_failed(msg))
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            worker.failed.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(lambda: self._cleanup_export_thread())

            self._export_thread = thread
            self._export_worker = worker
            thread.started.connect(worker.run)
            thread.start()

        def _cleanup_export_thread(self) -> None:
            try:
                if self._export_worker is not None:
                    self._export_worker.deleteLater()
            except Exception:
                pass
            try:
                if self._export_thread is not None:
                    self._export_thread.deleteLater()
            except Exception:
                pass
            self._export_thread = None
            self._export_worker = None
            self._export_cancel_token = None

        def _on_export_finished(self, label: str) -> None:
            QtWidgets.QMessageBox.information(self, "Export abgeschlossen", f"{label} gespeichert.")

        def _on_export_failed(self, message: str) -> None:
            QtWidgets.QMessageBox.warning(self, "Export fehlgeschlagen", message)

        def _on_finished(self, op: str, payload: object) -> None:
            self._cleanup_thread()
            self._set_running(False)
            self._ui_fsm.transition(UIState.IDLE)

            if op == "scan":
                if not isinstance(payload, ScanResult):
                    raise RuntimeError("Scan worker returned unexpected payload")
                self._scan_result = payload
                self._refresh_filter_options()
                filtered = self._get_filtered_scan_result()
                self.status_label.setText("Abgebrochen" if payload.cancelled else "Scan abgeschlossen")
                self._populate_scan_table(filtered)
                self._last_view = "scan"
                if payload.cancelled:
                    QtWidgets.QMessageBox.information(self, "Abgebrochen", "Scan abgebrochen.")
                else:
                    QtWidgets.QMessageBox.information(self, "Scan abgeschlossen", f"ROMs gefunden: {len(payload.items)}")
                self._complete_job("scan")
                return

            if op == "plan":
                if not isinstance(payload, SortPlan):
                    raise RuntimeError("Plan worker returned unexpected payload")
                self._sort_plan = payload
                self.status_label.setText("Plan bereit")
                self._populate_plan_table(payload)
                self._last_view = "plan"
                QtWidgets.QMessageBox.information(self, "Vorschau bereit", f"Geplante Aktionen: {len(payload.actions)}")
                self._complete_job("plan")
                return

            if op == "execute":
                if not isinstance(payload, SortReport):
                    raise RuntimeError("Execute worker returned unexpected payload")
                self.status_label.setText("Abgebrochen" if payload.cancelled else "Fertig")
                self._append_summary_row(payload)
                self._update_results_empty_state()
                QtWidgets.QMessageBox.information(
                    self,
                    "Fertig",
                    f"Fertig. Kopiert: {payload.copied}, Verschoben: {payload.moved}\nFehler: {len(payload.errors)}\n\nSiehe Log für Details.",
                )
                self._complete_job("execute")
                return

            if op == "audit":
                if not isinstance(payload, ConversionAuditReport):
                    raise RuntimeError("Audit worker returned unexpected payload")
                self.status_label.setText("Abgebrochen" if payload.cancelled else "Audit bereit")
                self._audit_report = payload
                self._populate_audit_table(payload)
                QtWidgets.QMessageBox.information(
                    self,
                    "Audit abgeschlossen",
                    f"Geprüft: {len(payload.items)}\n\nSiehe Tabelle für Vorschläge.",
                )
                self._complete_job("audit")
                self._set_running(False)
                return

        def _on_failed(self, message: str, tb: str) -> None:
            handle_worker_failure(
                message,
                tb,
                self._append_log,
                lambda msg, trace: QtWidgets.QMessageBox.critical(
                    self,
                    "Arbeitsfehler",
                    f"{msg}\n\n{trace}",
                ),
            )
            self._cleanup_thread()
            self._set_running(False)
            self._ui_fsm.transition(UIState.ERROR)
            self.status_label.setText("Error")
            self._set_log_visible(True, persist=False)
            if self._current_op:
                self._complete_job(self._current_op)
                self._current_op = None

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()

    exec_fn = getattr(app, "exec", None) or getattr(app, "exec_")
    return int(exec_fn())
    '''

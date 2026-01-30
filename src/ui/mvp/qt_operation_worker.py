from __future__ import annotations

import traceback
from typing import Any, List, Optional, cast

from .viewmodel_types import ViewModelEvents


def build_operation_worker(
    QtCore,
    Slot,
    binding: str,
    viewmodel,
    ConversionMode,
):
    class OperationWorker(QtCore.QObject):
        def __init__(
            self,
            op: str,
            source: str,
            dest: str,
            output_dir: str,
            temp_dir: str,
            mode: str,
            on_conflict: str,
            conversion_mode: ConversionMode,
            scan_result: Optional[Any],
            sort_plan: Optional[Any],
            start_index: int,
            only_indices: Optional[List[int]],
            resume_path: Optional[str],
            cancel_token: Any,
            signals: Any,
        ):
            super().__init__()
            self.op = op
            self.source = source
            self.dest = dest
            self.output_dir = output_dir
            self.temp_dir = temp_dir
            self.mode = mode
            self.on_conflict = on_conflict
            self.conversion_mode = conversion_mode
            self.scan_result = scan_result
            self.sort_plan = sort_plan
            self.start_index = int(start_index)
            self.only_indices = list(only_indices) if only_indices else None
            self.resume_path = resume_path
            self.cancel_token = cancel_token
            self.signals = signals

        @Slot()
        def run(self) -> None:
            try:
                self.signals.log.emit(f"Qt binding: {binding}")
                viewmodel.set_events(
                    ViewModelEvents(
                        log=lambda msg: self.signals.log.emit(str(msg)),
                        progress=lambda c, t: self.signals.progress.emit(int(c), int(t)),
                        phase_changed=lambda phase, total: self.signals.phase_changed.emit(str(phase), int(total)),
                        action_status=lambda i, status: self.signals.action_status.emit(int(i), str(status)),
                    )
                )

                if self.op == "scan":
                    self.signals.log.emit(f"Scan started: source={self.source}")
                    scan = viewmodel.run_scan(
                        self.source,
                        progress_cb=lambda c, t: self.signals.progress.emit(int(c), int(t)),
                        log_cb=lambda msg: self.signals.log.emit(str(msg)),
                        cancel_token=self.cancel_token,
                    )
                    self.signals.log.emit(f"Scan finished: items={len(scan.items)} cancelled={scan.cancelled}")
                    self.signals.finished.emit(scan)
                    return

                if self.op == "plan":
                    if self.scan_result is None:
                        raise RuntimeError("No scan result available")
                    self.signals.log.emit(
                        f"Plan started: items={len(self.scan_result.items)} mode={self.mode} conflict={self.on_conflict}"
                    )
                    plan = viewmodel.plan_sort(
                        self.scan_result,
                        self.dest,
                        mode=self.mode,
                        on_conflict=self.on_conflict,
                        cancel_token=self.cancel_token,
                    )
                    self.signals.log.emit(f"Plan finished: actions={len(plan.actions)}")
                    self.signals.finished.emit(plan)
                    return

                if self.op == "execute":
                    if self.sort_plan is None:
                        raise RuntimeError("No sort plan available")
                    total_actions = len(self.sort_plan.actions)
                    if self.only_indices:
                        filtered = [i for i in self.only_indices if 0 <= int(i) < total_actions]
                        total = len(set(filtered))
                    elif self.start_index > 0:
                        total = max(0, total_actions - int(self.start_index))
                    else:
                        total = total_actions
                    if self.conversion_mode != "all":
                        convert_count = sum(1 for action in self.sort_plan.actions if action.action == "convert")
                        if self.conversion_mode == "only":
                            total = convert_count
                        elif self.conversion_mode == "skip":
                            total = max(0, total_actions - convert_count)
                    self.signals.log.emit(
                        "Execute started: total={total} resume={resume} only_indices={only} conversion_mode={mode}".format(
                            total=total,
                            resume=self.start_index,
                            only=self.only_indices,
                            mode=self.conversion_mode,
                        )
                    )
                    report = viewmodel.execute_sort(
                        self.sort_plan,
                        progress_cb=lambda c, t: self.signals.progress.emit(int(c), int(t)),
                        log_cb=lambda msg: self.signals.log.emit(str(msg)),
                        action_status_cb=lambda i, status: self.signals.action_status.emit(int(i), str(status)),
                        cancel_token=self.cancel_token,
                        dry_run=False,
                        resume_path=self.resume_path,
                        start_index=self.start_index,
                        only_indices=self.only_indices,
                        conversion_mode=cast(ConversionMode, self.conversion_mode),
                    )
                    self.signals.log.emit(
                        "Execute finished: processed={processed} copied={copied} moved={moved} errors={errors} cancelled={cancelled}".format(
                            processed=report.processed,
                            copied=report.copied,
                            moved=report.moved,
                            errors=len(report.errors),
                            cancelled=report.cancelled,
                        )
                    )
                    self.signals.finished.emit(report)
                    return

                if self.op == "audit":
                    self.signals.log.emit(f"Audit started: source={self.source}")
                    report = viewmodel.audit_conversion_candidates(
                        self.source,
                        progress_cb=lambda c, t: self.signals.progress.emit(int(c), int(t)),
                        log_cb=lambda msg: self.signals.log.emit(str(msg)),
                        cancel_token=self.cancel_token,
                        include_disabled=True,
                    )
                    self.signals.log.emit(
                        f"Audit finished: items={len(report.items)} cancelled={report.cancelled}"
                    )
                    self.signals.finished.emit(report)
                    return

                raise RuntimeError(f"Unknown operation: {self.op}")

            except Exception as exc:
                self.signals.failed.emit(str(exc), traceback.format_exc())

    return OperationWorker

"""Qt worker factories for MVP UI (lazy Qt binding)."""

from __future__ import annotations

from typing import Any, Tuple, Type


def build_qt_workers(
    QtCore: Any,
    Signal: Any,
    Slot: Any,
    igir_plan,
    igir_execute,
    CancelToken,
) -> Tuple[Type[Any], Type[Any], Type[Any], Type[Any], Type[Any]]:
    """Create Qt worker classes bound to the provided QtCore/Signal/Slot.

    This keeps Qt imports lazy and avoids hard dependency at import time.
    """

    class WorkerSignals(QtCore.QObject):
        phase_changed = Signal(str, int)
        progress = Signal(int, int)
        log = Signal(str)
        action_status = Signal(int, str)
        finished = Signal(object)
        failed = Signal(str, str)

    class ExportWorker(QtCore.QObject):
        finished = Signal(str)
        failed = Signal(str)

        def __init__(self, label: str, task, cancel_token: Any):
            super().__init__()
            self._label = label
            self._task = task
            self._cancel_token = cancel_token

        @Slot()
        def run(self) -> None:
            try:
                if self._cancel_token.is_cancelled():
                    raise RuntimeError("Export cancelled")
                self._task(self._cancel_token)
                if self._cancel_token.is_cancelled():
                    raise RuntimeError("Export cancelled")
                self.finished.emit(self._label)
            except Exception as exc:
                self.failed.emit(str(exc))

    class DatIndexWorker(QtCore.QObject):
        finished = Signal(object)
        failed = Signal(str)

        def __init__(self, task):
            super().__init__()
            self._task = task

        @Slot()
        def run(self) -> None:
            try:
                result = self._task()
                self.finished.emit(result)
            except Exception as exc:
                self.failed.emit(str(exc))

    class IgirPlanWorker(QtCore.QObject):
        log = Signal(str)
        finished = Signal(object)
        failed = Signal(str)

        def __init__(
            self,
            input_path: str,
            output_dir: str,
            report_dir: str,
            temp_dir: str,
            cancel_token: Any,
        ):
            super().__init__()
            self._input_path = input_path
            self._output_dir = output_dir
            self._report_dir = report_dir
            self._temp_dir = temp_dir
            self._cancel_token = cancel_token

        @Slot()
        def run(self) -> None:
            try:
                result = igir_plan(
                    input_path=self._input_path,
                    output_dir=self._output_dir,
                    dest_root=self._output_dir,
                    report_dir=self._report_dir,
                    temp_dir=self._temp_dir,
                    log_cb=lambda msg: self.log.emit(str(msg)),
                    cancel_token=self._cancel_token,
                )
                self.finished.emit(result)
            except Exception as exc:
                self.failed.emit(str(exc))

    class IgirExecuteWorker(QtCore.QObject):
        log = Signal(str)
        finished = Signal(object)
        failed = Signal(str)

        def __init__(
            self,
            input_path: str,
            output_dir: str,
            temp_dir: str,
            cancel_token: Any,
            plan_confirmed: bool,
            explicit_user_action: bool,
            copy_first: bool,
        ):
            super().__init__()
            self._input_path = input_path
            self._output_dir = output_dir
            self._temp_dir = temp_dir
            self._cancel_token = cancel_token
            self._plan_confirmed = plan_confirmed
            self._explicit_user_action = explicit_user_action
            self._copy_first = copy_first

        @Slot()
        def run(self) -> None:
            try:
                result = igir_execute(
                    input_path=self._input_path,
                    output_dir=self._output_dir,
                    dest_root=self._output_dir,
                    temp_dir=self._temp_dir,
                    log_cb=lambda msg: self.log.emit(str(msg)),
                    cancel_token=self._cancel_token,
                    plan_confirmed=self._plan_confirmed,
                    explicit_user_action=self._explicit_user_action,
                    copy_first=self._copy_first,
                )
                self.finished.emit(result)
            except Exception as exc:
                self.failed.emit(str(exc))

    return WorkerSignals, ExportWorker, DatIndexWorker, IgirPlanWorker, IgirExecuteWorker

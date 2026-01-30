from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, cast

from ...app.api import (
    CancelToken,
    ConflictPolicy,
    ConversionMode,
    SortMode,
    audit_conversion_candidates,
    execute_sort,
    plan_sort,
    run_scan,
)
from ...ui.state_machine import UIState, UIStateMachine
from .viewmodel_types import DetailsDTO, ResultsRowDTO, ViewModelEvents


@dataclass
class AppViewModelState:
    last_scan: Optional[Any] = None
    last_plan: Optional[Any] = None
    last_report: Optional[Any] = None
    last_audit: Optional[Any] = None
    last_error: Optional[str] = None


def scan_item_to_row(item: Any) -> ResultsRowDTO:
    return ResultsRowDTO(
        input_path=str(getattr(item, "input_path", "")),
        detected_system=str(getattr(item, "detected_system", "")),
        planned_target_path=None,
        action="scan",
        status="scanned",
        error=None,
    )


def sort_action_to_row(action: Any) -> ResultsRowDTO:
    return ResultsRowDTO(
        input_path=str(getattr(action, "input_path", "")),
        detected_system=str(getattr(action, "detected_system", "")),
        planned_target_path=getattr(action, "planned_target_path", None),
        action=str(getattr(action, "action", "")),
        status=str(getattr(action, "status", "")),
        error=getattr(action, "error", None),
    )


def action_to_details(action: Any) -> DetailsDTO:
    return DetailsDTO(
        input_path=str(getattr(action, "input_path", "")),
        target_path=getattr(action, "planned_target_path", None),
        status=str(getattr(action, "status", "")),
        system=str(getattr(action, "detected_system", "")),
        reason=getattr(action, "error", None),
    )


class AppViewModel:
    def __init__(
        self,
        run_scan_fn: Callable[..., Any] = run_scan,
        plan_sort_fn: Callable[..., Any] = plan_sort,
        execute_sort_fn: Callable[..., Any] = execute_sort,
        audit_fn: Callable[..., Any] = audit_conversion_candidates,
        state_machine: Optional[UIStateMachine] = None,
    ) -> None:
        self._run_scan = run_scan_fn
        self._plan_sort = plan_sort_fn
        self._execute_sort = execute_sort_fn
        self._audit = audit_fn
        self._state_machine = state_machine
        self._cancel_token: Optional[CancelToken] = None
        self.state = AppViewModelState()
        self.events = ViewModelEvents()

    def set_events(self, events: ViewModelEvents) -> None:
        self.events = events

    def new_cancel_token(self) -> CancelToken:
        self._cancel_token = CancelToken()
        return self._cancel_token

    def cancel(self) -> None:
        if self._cancel_token is not None:
            self._cancel_token.cancel()

    def _transition(self, target: UIState) -> None:
        if self._state_machine is not None:
            self._state_machine.transition(target)

    def run_scan(
        self,
        source: str,
        progress_cb: Callable[[int, int], None],
        log_cb: Callable[[str], None],
        cancel_token: CancelToken,
    ) -> Any:
        self._transition(UIState.SCANNING)
        try:
            self.events.phase_changed and self.events.phase_changed("scan", 0)
            scan = self._run_scan(
                source,
                config=None,
                progress_cb=progress_cb,
                log_cb=log_cb,
                cancel_token=cancel_token,
            )
            self.state.last_scan = scan
            self._transition(UIState.IDLE)
            return scan
        except Exception as exc:
            self.state.last_error = str(exc)
            self.events.error and self.events.error(str(exc))
            self._transition(UIState.ERROR)
            raise

    def plan_sort(
        self,
        scan_result: Any,
        dest: str,
        mode: str,
        on_conflict: str,
        cancel_token: CancelToken,
    ) -> Any:
        self._transition(UIState.PLANNING)
        try:
            self.events.phase_changed and self.events.phase_changed("plan", len(scan_result.items))
            plan = self._plan_sort(
                scan_result,
                dest,
                config=None,
                mode=cast(SortMode, mode),
                on_conflict=cast(ConflictPolicy, on_conflict),
                cancel_token=cancel_token,
            )
            self.state.last_plan = plan
            self._transition(UIState.IDLE)
            return plan
        except Exception as exc:
            self.state.last_error = str(exc)
            self.events.error and self.events.error(str(exc))
            self._transition(UIState.ERROR)
            raise

    def execute_sort(
        self,
        sort_plan: Any,
        progress_cb: Callable[[int, int], None],
        log_cb: Callable[[str], None],
        action_status_cb: Callable[[int, str], None],
        cancel_token: CancelToken,
        dry_run: bool,
        resume_path: Optional[str],
        start_index: int,
        only_indices: Optional[List[int]],
        conversion_mode: ConversionMode,
    ) -> Any:
        self._transition(UIState.EXECUTING)
        try:
            report = self._execute_sort(
                sort_plan,
                progress_cb=progress_cb,
                log_cb=log_cb,
                action_status_cb=action_status_cb,
                cancel_token=cancel_token,
                dry_run=dry_run,
                resume_path=resume_path,
                start_index=start_index,
                only_indices=only_indices,
                conversion_mode=cast(ConversionMode, conversion_mode),
            )
            self.state.last_report = report
            self._transition(UIState.IDLE)
            return report
        except Exception as exc:
            self.state.last_error = str(exc)
            self.events.error and self.events.error(str(exc))
            self._transition(UIState.ERROR)
            raise

    def audit_conversion_candidates(
        self,
        source: str,
        progress_cb: Callable[[int, int], None],
        log_cb: Callable[[str], None],
        cancel_token: CancelToken,
        include_disabled: bool = True,
    ) -> Any:
        self._transition(UIState.AUDITING)
        try:
            self.events.phase_changed and self.events.phase_changed("audit", 0)
            report = self._audit(
                source,
                config=None,
                progress_cb=progress_cb,
                log_cb=log_cb,
                cancel_token=cancel_token,
                include_disabled=include_disabled,
            )
            self.state.last_audit = report
            self._transition(UIState.IDLE)
            return report
        except Exception as exc:
            self.state.last_error = str(exc)
            self.events.error and self.events.error(str(exc))
            self._transition(UIState.ERROR)
            raise

    def map_scan_items(self, items: Iterable[Any]) -> List[ResultsRowDTO]:
        return [scan_item_to_row(item) for item in items]

    def map_plan_actions(self, actions: Iterable[Any]) -> List[ResultsRowDTO]:
        return [sort_action_to_row(action) for action in actions]

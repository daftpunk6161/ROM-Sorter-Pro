from __future__ import annotations

from types import SimpleNamespace

from src.ui.mvp.viewmodel import AppViewModel
from src.ui.mvp.viewmodel_types import ViewModelEvents
from src.ui.state_machine import UIState, UIStateMachine


def test_viewmodel_transitions_and_state() -> None:
    events_called = []

    def run_scan_stub(source, config, progress_cb, log_cb, cancel_token):
        log_cb("scan")
        return SimpleNamespace(items=[1, 2], cancelled=False)

    def plan_sort_stub(scan_result, dest, config, mode, on_conflict, cancel_token):
        return SimpleNamespace(actions=[1, 2, 3])

    def execute_sort_stub(*args, **kwargs):
        return SimpleNamespace(processed=1, copied=1, moved=0, errors=[], cancelled=False)

    def audit_stub(source, config, progress_cb, log_cb, cancel_token, include_disabled=True):
        return SimpleNamespace(items=[1], cancelled=False)

    sm = UIStateMachine()
    vm = AppViewModel(
        run_scan_fn=run_scan_stub,
        plan_sort_fn=plan_sort_stub,
        execute_sort_fn=execute_sort_stub,
        audit_fn=audit_stub,
        state_machine=sm,
    )
    vm.set_events(ViewModelEvents(log=lambda msg: events_called.append(msg)))

    scan = vm.run_scan("src", progress_cb=lambda *_: None, log_cb=lambda *_: None, cancel_token=vm.new_cancel_token())
    assert len(scan.items) == 2
    assert vm.state.last_scan is scan
    assert sm.state == UIState.IDLE

    plan = vm.plan_sort(scan, "dest", mode="copy", on_conflict="rename", cancel_token=vm.new_cancel_token())
    assert len(plan.actions) == 3
    assert vm.state.last_plan is plan
    assert sm.state == UIState.IDLE

    report = vm.execute_sort(
        plan,
        progress_cb=lambda *_: None,
        log_cb=lambda *_: None,
        action_status_cb=lambda *_: None,
        cancel_token=vm.new_cancel_token(),
        dry_run=False,
        resume_path=None,
        start_index=0,
        only_indices=None,
        conversion_mode="all",
    )
    assert report.processed == 1
    assert vm.state.last_report is report
    assert sm.state == UIState.IDLE

    audit = vm.audit_conversion_candidates(
        "src",
        progress_cb=lambda *_: None,
        log_cb=lambda *_: None,
        cancel_token=vm.new_cancel_token(),
    )
    assert audit.items == [1]
    assert vm.state.last_audit is audit
    assert sm.state == UIState.IDLE

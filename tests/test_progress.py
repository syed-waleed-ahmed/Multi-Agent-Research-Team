"""Tests for cooperative cancellation and time budgets."""

from __future__ import annotations

import threading
import time

import pytest

from research_team.exceptions import WorkflowCancelledError, WorkflowTimeoutError
from research_team.progress import STAGES, RunControl, Stage


def test_stages_order_and_agent_names():
    assert [s.value for s in STAGES] == ["research", "coding", "synthesis"]
    assert Stage.SYNTHESIS.agent_name == "Manager Agent"


def test_check_passes_when_idle():
    RunControl().check()


def test_cancel_raises_on_next_check():
    control = RunControl()
    control.cancel()
    assert control.cancelled
    with pytest.raises(WorkflowCancelledError):
        control.check()


def test_deadline_raises_timeout():
    control = RunControl(timeout_seconds=0.01)
    time.sleep(0.02)
    with pytest.raises(WorkflowTimeoutError) as exc:
        control.check()
    assert "time limit" in exc.value.public_message


def test_wait_wakes_immediately_on_cancel():
    control = RunControl()
    threading.Timer(0.05, control.cancel).start()
    started = time.monotonic()
    with pytest.raises(WorkflowCancelledError):
        control.wait(5)
    assert time.monotonic() - started < 2


def test_wait_longer_than_budget_times_out_fast():
    control = RunControl(timeout_seconds=0.05)
    started = time.monotonic()
    with pytest.raises(WorkflowTimeoutError):
        control.wait(30)
    assert time.monotonic() - started < 2

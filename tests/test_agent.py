"""
Tests for the PawPal+ agentic scheduling loop.

Three categories:
  1. Unit tests   — test _parse_action() with no API calls
  2. Mock tests   — patch the K2 API to inject predetermined actions, verify state
  3. Integration  — real API call (opt-in via: pytest -m integration)
"""

import json
import pytest
from datetime import date, time, timedelta
from unittest.mock import MagicMock, patch

from pawpal_system import Owner, Pet, Task, TimeSlot, Scheduler, Schedule, ScheduledTask
from agent import _parse_action, run_agentic_schedule


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_scheduler():
    """Minimal scheduler: one pet (Baxter) with two tasks that share a preferred window."""
    owner = Owner(
        name="Jordan",
        contactInfo="jordan@example.com",
        availableTimeSlots=[TimeSlot(time(7, 0), time(10, 0))],
    )
    pet = Pet(name="Baxter", type="dog", age=3)
    walk = Task(
        name="Walk",
        duration=timedelta(minutes=30),
        priority=9,
        pet=pet,
        preferredTime=TimeSlot(time(7, 0), time(8, 0)),
    )
    feed = Task(
        name="Feed",
        duration=timedelta(minutes=20),
        priority=6,
        pet=pet,
        preferredTime=TimeSlot(time(7, 0), time(8, 0)),
    )
    pet.addTask(walk)
    pet.addTask(feed)
    return Scheduler(owner, [pet])


def _make_conflicting_schedule(scheduler):
    """Build a Schedule where Walk and Feed overlap (07:00–07:30 vs 07:15–07:35)."""
    tasks = scheduler.pets[0].getTasks()
    sched = Schedule(date=date.today())
    sched.addScheduledTask(ScheduledTask(task=tasks[0], startTime=time(7, 0),  endTime=time(7, 30)))
    sched.addScheduledTask(ScheduledTask(task=tasks[1], startTime=time(7, 15), endTime=time(7, 35)))
    return sched


def _mock_api_response(action_dict):
    """Wrap action_dict in a mock that looks like an openai ChatCompletion response."""
    response = MagicMock()
    response.choices[0].message.content = json.dumps(action_dict)
    return response


# ── 1. Unit tests: _parse_action ─────────────────────────────────────────────

def test_parse_action_valid_json():
    raw = json.dumps({
        "action": "accept_schedule",
        "task_name": None,
        "pet_name": None,
        "reason": "No better option",
    })
    result = _parse_action(raw)
    assert result is not None
    assert result["action"] == "accept_schedule"


def test_parse_action_strips_thinking_tags():
    """K2 may wrap its reasoning in <think> tags — those should be stripped."""
    raw = (
        "<think>I should lower the priority of Feed.</think>\n"
        '{"action": "lower_task_priority", "task_name": "Feed", '
        '"pet_name": "Baxter", "reason": "Walk has higher priority"}'
    )
    result = _parse_action(raw)
    assert result is not None
    assert result["action"] == "lower_task_priority"


def test_parse_action_strips_markdown_fence():
    """Model may wrap JSON in a ```json code fence."""
    raw = (
        "```json\n"
        '{"action": "skip_task_today", "task_name": "Feed", '
        '"pet_name": "Baxter", "reason": "low priority"}\n'
        "```"
    )
    result = _parse_action(raw)
    assert result is not None
    assert result["action"] == "skip_task_today"


def test_parse_action_extracts_embedded_json():
    """JSON embedded inside prose should still be found via the regex fallback."""
    raw = (
        'Here is my decision: {"action": "relax_preferred_time", '
        '"task_name": "Walk", "pet_name": "Baxter", "reason": "test"}'
    )
    result = _parse_action(raw)
    assert result is not None
    assert result["action"] == "relax_preferred_time"


def test_parse_action_returns_none_on_garbage():
    """Completely unparseable text should return None, not raise."""
    result = _parse_action("Sorry, I cannot help with scheduling today.")
    assert result is None


# ── 2. Mock tests: agent loop behaviour ──────────────────────────────────────

def test_no_conflicts_skips_api():
    """When the schedule has no conflicts, the API must never be called."""
    scheduler = _make_scheduler()
    clean_schedule = Schedule(date=date.today())   # empty → no conflicts

    with patch.object(scheduler, "generateDailySchedule", return_value=clean_schedule):
        with patch("agent.client") as mock_client:
            _, agent_log = run_agentic_schedule(scheduler)

    mock_client.chat.completions.create.assert_not_called()
    assert agent_log[0]["conflicts_before"] == 0
    assert "No conflicts" in agent_log[0]["summary"]


def test_lower_priority_action_applied():
    """Agent action lower_task_priority must reduce the target task's priority by 3."""
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)
    clean = Schedule(date=date.today())

    api_response = _mock_api_response({
        "action": "lower_task_priority",
        "task_name": "Feed",
        "pet_name": "Baxter",
        "reason": "Feed has lower importance than Walk",
    })

    with patch.object(scheduler, "generateDailySchedule", side_effect=[conflicting, clean]):
        with patch("agent.client") as mock_client:
            mock_client.chat.completions.create.return_value = api_response
            _, agent_log = run_agentic_schedule(scheduler)

    feed = next(t for t in scheduler.pets[0].getTasks() if t.name == "Feed")
    assert feed.priority == 3   # was 6 → lowered by 3
    assert "Lowered priority" in agent_log[0]["summary"]


def test_relax_preferred_time_applied():
    """Agent action relax_preferred_time must set the task's preferredTime to None."""
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)
    clean = Schedule(date=date.today())

    api_response = _mock_api_response({
        "action": "relax_preferred_time",
        "task_name": "Feed",
        "pet_name": "Baxter",
        "reason": "Removing the time window lets it shift to an open slot",
    })

    with patch.object(scheduler, "generateDailySchedule", side_effect=[conflicting, clean]):
        with patch("agent.client") as mock_client:
            mock_client.chat.completions.create.return_value = api_response
            _, agent_log = run_agentic_schedule(scheduler)

    feed = next(t for t in scheduler.pets[0].getTasks() if t.name == "Feed")
    assert feed.preferredTime is None
    assert "Relaxed time preference" in agent_log[0]["summary"]


def test_skip_task_applied():
    """Agent action skip_task_today must mark the target task as completed."""
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)
    clean = Schedule(date=date.today())

    api_response = _mock_api_response({
        "action": "skip_task_today",
        "task_name": "Feed",
        "pet_name": "Baxter",
        "reason": "Non-critical task causing unavoidable conflict",
    })

    with patch.object(scheduler, "generateDailySchedule", side_effect=[conflicting, clean]):
        with patch("agent.client") as mock_client:
            mock_client.chat.completions.create.return_value = api_response
            _, agent_log = run_agentic_schedule(scheduler)

    feed = next(t for t in scheduler.pets[0].getTasks() if t.name == "Feed")
    assert feed.completed is True
    assert "Skipped" in agent_log[0]["summary"]


def test_accept_schedule_stops_loop_after_one_call():
    """accept_schedule must end the loop immediately — API called exactly once."""
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)

    api_response = _mock_api_response({
        "action": "accept_schedule",
        "task_name": None,
        "pet_name": None,
        "reason": "Conflicts are minor",
    })

    with patch.object(scheduler, "generateDailySchedule", return_value=conflicting):
        with patch("agent.client") as mock_client:
            mock_client.chat.completions.create.return_value = api_response
            _, agent_log = run_agentic_schedule(scheduler)

    mock_client.chat.completions.create.assert_called_once()
    assert "accepted schedule" in agent_log[0]["summary"]


def test_max_iterations_respected():
    """Loop must stop after max_iterations even when conflicts never clear."""
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)

    # API always asks to lower Feed's priority — but conflicts never go away
    api_response = _mock_api_response({
        "action": "lower_task_priority",
        "task_name": "Feed",
        "pet_name": "Baxter",
        "reason": "Keep trying",
    })

    max_iter = 3
    with patch.object(scheduler, "generateDailySchedule", return_value=conflicting):
        with patch("agent.client") as mock_client:
            mock_client.chat.completions.create.return_value = api_response
            _, agent_log = run_agentic_schedule(scheduler, max_iterations=max_iter)

    assert mock_client.chat.completions.create.call_count == max_iter
    assert "max iterations" in agent_log[-1]["summary"]


def test_unknown_task_name_accepts_schedule():
    """If the model names a task that doesn't exist, the agent accepts gracefully."""
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)

    api_response = _mock_api_response({
        "action": "lower_task_priority",
        "task_name": "GhostTask",
        "pet_name": "Baxter",
        "reason": "This task does not exist",
    })

    with patch.object(scheduler, "generateDailySchedule", return_value=conflicting):
        with patch("agent.client") as mock_client:
            mock_client.chat.completions.create.return_value = api_response
            _, agent_log = run_agentic_schedule(scheduler)

    assert "not found" in agent_log[0]["summary"]


def test_unparseable_response_accepts_schedule():
    """If the model returns text that isn't valid JSON, the agent accepts gracefully."""
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)

    bad_response = MagicMock()
    bad_response.choices[0].message.content = "I am unable to determine the best action."

    with patch.object(scheduler, "generateDailySchedule", return_value=conflicting):
        with patch("agent.client") as mock_client:
            mock_client.chat.completions.create.return_value = bad_response
            _, agent_log = run_agentic_schedule(scheduler)

    assert "could not be parsed" in agent_log[0]["summary"]


# ── 3. Integration test (real API) ────────────────────────────────────────────

@pytest.mark.integration
def test_agent_reduces_conflicts_real_api():
    """
    Live call to K2 Think V2. Skipped unless you run: pytest -m integration

    Verifies that after the agent loop the number of conflicts is lower than
    before, OR the agent log explains why it accepted an unresolved schedule.
    """
    scheduler = _make_scheduler()
    conflicting = _make_conflicting_schedule(scheduler)
    conflicts_before = len(conflicting.detect_conflicts())

    with patch.object(scheduler, "generateDailySchedule", return_value=conflicting):
        final_schedule, agent_log = run_agentic_schedule(scheduler)

    conflicts_after = len(final_schedule.detect_conflicts())

    # The agent either resolved the conflicts, accepted them, or exhausted iterations.
    # All three are valid outcomes that confirm K2 returned parseable JSON every time.
    resolved = conflicts_after < conflicts_before
    accepted = any("accept" in entry["summary"].lower() for entry in agent_log)
    exhausted = any("max iterations" in entry["summary"].lower() for entry in agent_log)
    no_parse_errors = not any("could not be parsed" in e["summary"] for e in agent_log)
    assert (resolved or accepted or exhausted) and no_parse_errors, (
        f"Expected conflicts to decrease, be accepted, or exhaust iterations with valid JSON. "
        f"Before: {conflicts_before}, After: {conflicts_after}\n"
        f"Agent log: {agent_log}"
    )

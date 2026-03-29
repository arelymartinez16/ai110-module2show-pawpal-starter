# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter scheduling

The following features were added:

- **Recurring tasks** — Tasks support `daily` or `weekly` recurrence. When marked complete, `markCompleted()` automatically creates the next instance with the appropriate due date.
- **Conflict detection** — `Schedule.detect_conflicts()` scans the scheduled task list and reports any overlapping time slots by name, pet, and time range.
- **Improved schedule explanation** — `explainSchedule()` produces a human-readable summary including: priority order, owner availability blocks, free gaps within those blocks, a chronological task list, and any detected conflicts.
- **Constraint filtering** — `Scheduler.apply_constraints()` filters tasks against both owner-level and task-level constraints (pet name, minimum priority, task name pattern) before scheduling begins.
- **Scheduler helpers** — Added `get_pending_tasks()`, `get_completed_tasks()`, `get_due_today_tasks()`, and `complete_task()` to support UI and testing needs.
- **Free-slot tracking** — `fitTasksIntoTimeSlots()` subtracts used time from available slots after each placement, preventing double-booking.

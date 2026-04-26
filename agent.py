"""
Agentic scheduling loop for PawPal+.

Uses K2 Think V2 to inspect the current schedule, identify conflicts, and take
one corrective action per iteration until conflicts are resolved or the max
number of iterations is reached.

Requires the environment variable K2_API_KEY to be set.
"""

import json
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from pawpal_system import Scheduler

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("K2_API_KEY", ""),
    base_url="https://api.k2think.ai/v1",
)

MODEL = "MBZUAI-IFM/K2-Think-v2"

SYSTEM_PROMPT = """You are a pet care scheduling agent. Your job is to resolve
conflicts in a daily pet care schedule by taking one targeted action per turn.

YOUR ENTIRE RESPONSE MUST BE A SINGLE JSON OBJECT. No explanation before or
after. No markdown fences. No prose. Just the JSON.

Schema:
{
  "action": "<lower_task_priority | relax_preferred_time | skip_task_today | accept_schedule>",
  "task_name": "<exact task name, or null for accept_schedule>",
  "pet_name": "<exact pet name, or null for accept_schedule>",
  "reason": "<one sentence>"
}

Example output:
{"action": "relax_preferred_time", "task_name": "Feed", "pet_name": "Baxter", "reason": "Removing the morning preference lets Feed shift to an open afternoon slot."}

Action descriptions:
- lower_task_priority: Reduce a task's priority by 3 so it yields slots to higher-priority tasks.
- relax_preferred_time: Remove a task's preferred time window so it can fill any open slot.
- skip_task_today: Drop a non-critical task from today's schedule entirely (last resort).
- accept_schedule: Stop optimizing — use when conflicts are unavoidable or minor.

Rules:
- Preserve higher-priority tasks.
- Prefer relax_preferred_time over lower_task_priority over skip_task_today.
- Use accept_schedule only when no action would improve things."""


def _build_user_message(schedule, conflicts, scheduler) -> str:
    scheduled_info = [
        {
            "task": st.task.name,
            "pet": st.task.pet.name,
            "priority": st.task.priority,
            "time": f"{st.startTime.strftime('%I:%M %p')} - {st.endTime.strftime('%I:%M %p')}",
        }
        for st in schedule.getTasks()
    ]

    all_tasks_info = [
        {
            "name": task.name,
            "pet": pet.name,
            "priority": task.priority,
            "duration_min": int(task.duration.total_seconds() / 60),
            "preferred_time": task.preferredTime.formatted() if task.preferredTime else "Any",
        }
        for pet in scheduler.pets
        for task in pet.getTasks()
        if not task.completed
    ]

    return (
        f"The current schedule has {len(conflicts)} conflict(s).\n\n"
        f"Scheduled tasks:\n{json.dumps(scheduled_info, indent=2)}\n\n"
        f"Conflicts:\n{json.dumps(conflicts, indent=2)}\n\n"
        f"All pending tasks:\n{json.dumps(all_tasks_info, indent=2)}\n\n"
        "Choose ONE action to reduce conflicts."
    )


def _extract_first_json_object(text: str) -> str | None:
    """Return the first complete JSON object found in text using brace counting."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_action(text: str) -> dict | None:
    """Extract and parse the JSON action from the model's response."""
    # Strip thinking tags and markdown fences the model may include
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        candidate = _extract_first_json_object(text)
        if candidate:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    return None


def _find_task(scheduler, task_name, pet_name):
    for pet in scheduler.pets:
        if pet.name == pet_name:
            for task in pet.getTasks():
                if task.name == task_name:
                    return task
    return None


def run_agentic_schedule(scheduler: Scheduler, max_iterations: int = 3):
    """
    Run the agentic scheduling loop.

    Returns:
        (Schedule, list[dict])  — the final schedule and a log of agent actions.
    """
    agent_log = []

    for iteration in range(max_iterations):
        schedule = scheduler.generateDailySchedule()
        conflicts = schedule.detect_conflicts()

        if not conflicts:
            agent_log.append({
                "iteration": iteration + 1,
                "summary": "No conflicts — schedule accepted as-is.",
                "conflicts_before": 0,
            })
            return schedule, agent_log

        # Ask K2 what to do
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(schedule, conflicts, scheduler)},
            ],
            stream=False,
            temperature=0,
        )
        raw_text = response.choices[0].message.content or ""
        action = _parse_action(raw_text)

        if action is None:
            agent_log.append({
                "iteration": iteration + 1,
                "summary": "Agent response could not be parsed — accepting schedule.",
                "conflicts_before": len(conflicts),
            })
            return schedule, agent_log

        action_type = action.get("action")
        task_name = action.get("task_name")
        pet_name = action.get("pet_name")
        reason = action.get("reason", "")

        if action_type == "accept_schedule":
            agent_log.append({
                "iteration": iteration + 1,
                "summary": f"Agent accepted schedule: {reason}",
                "conflicts_before": len(conflicts),
            })
            return schedule, agent_log

        elif action_type == "lower_task_priority":
            task = _find_task(scheduler, task_name, pet_name)
            if task is None:
                agent_log.append({
                    "iteration": iteration + 1,
                    "summary": f"Task '{task_name}' not found — accepting schedule.",
                    "conflicts_before": len(conflicts),
                })
                return schedule, agent_log
            old_p = task.priority
            task.priority = max(1, task.priority - 3)
            agent_log.append({
                "iteration": iteration + 1,
                "summary": (
                    f"Lowered priority of '{task_name}' ({pet_name}) "
                    f"from {old_p} → {task.priority}. {reason}"
                ),
                "conflicts_before": len(conflicts),
            })

        elif action_type == "relax_preferred_time":
            task = _find_task(scheduler, task_name, pet_name)
            if task is None:
                agent_log.append({
                    "iteration": iteration + 1,
                    "summary": f"Task '{task_name}' not found — accepting schedule.",
                    "conflicts_before": len(conflicts),
                })
                return schedule, agent_log
            old_pref = task.preferredTime.formatted() if task.preferredTime else "Any"
            task.preferredTime = None
            agent_log.append({
                "iteration": iteration + 1,
                "summary": (
                    f"Relaxed time preference for '{task_name}' ({pet_name}) "
                    f"from '{old_pref}' → any slot. {reason}"
                ),
                "conflicts_before": len(conflicts),
            })

        elif action_type == "skip_task_today":
            task = _find_task(scheduler, task_name, pet_name)
            if task is None:
                agent_log.append({
                    "iteration": iteration + 1,
                    "summary": f"Task '{task_name}' not found — accepting schedule.",
                    "conflicts_before": len(conflicts),
                })
                return schedule, agent_log
            task.completed = True
            agent_log.append({
                "iteration": iteration + 1,
                "summary": f"Skipped '{task_name}' ({pet_name}) from today's schedule. {reason}",
                "conflicts_before": len(conflicts),
            })

        else:
            agent_log.append({
                "iteration": iteration + 1,
                "summary": f"Unknown action '{action_type}' — accepting schedule.",
                "conflicts_before": len(conflicts),
            })
            return schedule, agent_log

    # Exhausted iterations
    final_schedule = scheduler.generateDailySchedule()
    remaining = len(final_schedule.detect_conflicts())
    agent_log.append({
        "iteration": max_iterations + 1,
        "summary": (
            f"Reached max iterations ({max_iterations}) — returning best schedule "
            f"({remaining} conflict(s) remaining)."
        ),
        "conflicts_before": remaining,
    })
    return final_schedule, agent_log

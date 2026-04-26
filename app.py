import streamlit as st
from datetime import date, time, timedelta
from unittest.mock import patch
from pawpal_system import Owner, Pet, Task, TimeSlot, Scheduler, Schedule, ScheduledTask
from agent import run_agentic_schedule

if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        name='Arely',
        contactInfo='arely@example.com',
        availableTimeSlots=[
            TimeSlot(startTime=time(7, 0), endTime=time(10, 0)),   # 7:00 - 10:00
            TimeSlot(startTime=time(12, 0), endTime=time(17, 0)),  # 12:00 - 17:00
            TimeSlot(startTime=time(17, 0), endTime=time(20, 0)),  # 17:00 - 20:00
        ],
        preferences={'minPriority': 1},
    )

owner = st.session_state.owner

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")

if "pets" not in st.session_state:
    st.session_state.pets = [
        Pet(name="Mochi", type="dog", age=2),
    ]

pet_col1, pet_col2, pet_col3 = st.columns(3)
with pet_col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with pet_col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with pet_col3:
    age = st.number_input("Age", min_value=0, max_value=30, value=2)

if st.button("Add pet"):
    if pet_name.strip() == "":
        st.warning("Pet name cannot be empty")
    else:
        new_pet = Pet(name=pet_name.strip(), type=species, age=int(age))
        st.session_state.pets.append(new_pet)

if st.session_state.pets:
    st.write("Current pets:")
    st.table([
        {"name": p.name, "type": p.type, "age": p.age} for p in st.session_state.pets
    ])

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

task_pet_names = [pet.name for pet in st.session_state.pets]

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col4:
    task_pet = st.selectbox("Assign to pet", task_pet_names)

preferred_period = st.selectbox(
    "Preferred period",
    ["None", "Morning", "Afternoon", "Evening"],
    index=0,
)

if st.button("Add task"):
    st.session_state.tasks.append(
        {
            "title": task_title,
            "duration_minutes": int(duration),
            "priority": priority,
            "pet_name": task_pet,
            "preferred_period": preferred_period,
        }
    )

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    # ── Build Task objects from session state ─────────────────────────────────
    pets_map = {p.name: p for p in st.session_state.pets}

    priority_map = {"low": 3, "medium": 6, "high": 9}
    period_slots = {
        "Morning":   TimeSlot(startTime=time(7, 0),  endTime=time(10, 0)),
        "Afternoon": TimeSlot(startTime=time(12, 0), endTime=time(17, 0)),
        "Evening":   TimeSlot(startTime=time(17, 0), endTime=time(20, 0)),
    }

    for t in st.session_state.tasks:
        pet_name_for_task = t.get("pet_name")
        if pet_name_for_task not in pets_map:
            continue
        preferred_time = period_slots.get(t.get("preferred_period"))
        task = Task(
            name=t["title"],
            duration=timedelta(minutes=int(t["duration_minutes"])),
            priority=priority_map.get(t.get("priority", "low"), 3),
            pet=pets_map[pet_name_for_task],
            preferredTime=preferred_time,
        )
        pets_map[pet_name_for_task].addTask(task)

    scheduler = Scheduler(owner=owner, pets=list(pets_map.values()))

    with st.spinner("AI agent is optimizing your schedule…"):
        schedule, agent_log = run_agentic_schedule(scheduler)

    scheduled_tasks = schedule.getTasks()

    if not scheduled_tasks:
        st.warning("No tasks could be scheduled with current availability and preferences.")
        st.stop()

    # ── Agent activity log ────────────────────────────────────────────────────
    with st.expander("🤖 Agent activity", expanded=True):
        for entry in agent_log:
            before = entry["conflicts_before"]
            label = f"**Iteration {entry['iteration']}** — {entry['summary']}"
            if before == 0:
                st.success(label)
            else:
                st.info(f"{label} *(conflicts before: {before})*")

    # ── Remaining conflict warnings ───────────────────────────────────────────
    conflicts = schedule.detect_conflicts()
    if conflicts:
        st.error(
            f"**{len(conflicts)} conflict(s) remain after agent optimization.** "
            "Try adjusting task durations, preferred periods, or owner availability."
        )
        for conflict in conflicts:
            parts = conflict.removeprefix("Conflict: ").split(" overlaps with ")
            if len(parts) == 2:
                st.warning(
                    f"**Overlap:** {parts[0].strip()}  \n"
                    f"**conflicts with:** {parts[1].strip()}"
                )
            else:
                st.warning(conflict)
    else:
        st.success(
            f"Schedule generated — {len(scheduled_tasks)} task(s) placed with no conflicts."
        )

    # ── Priority order (from Scheduler.sortTasks) ─────────────────────────────
    all_tasks = [st_task.task for st_task in scheduled_tasks]
    sorted_by_priority = scheduler.sortTasks(all_tasks)
    priority_order = ", ".join(
        f"{t.name} ({t.pet.name})" for t in sorted_by_priority
    )
    st.caption(f"Priority order used: {priority_order}")

    # ── Schedule table ────────────────────────────────────────────────────────
    st.markdown("### Today's Schedule")
    st.table([
        {
            "Time": (
                f"{st_task.startTime.strftime('%I:%M %p')} – "
                f"{st_task.endTime.strftime('%I:%M %p')}"
            ),
            "Pet": st_task.task.pet.name,
            "Task": st_task.task.name,
            "Priority": st_task.task.priority,
            "Duration": f"{int(st_task.task.duration.total_seconds() // 60)} min",
        }
        for st_task in scheduled_tasks
    ])

    # ── Plan explanation ──────────────────────────────────────────────────────
    with st.expander("Why was this schedule chosen?", expanded=False):
        explanation = schedule.explainSchedule(owner.availableTimeSlots)
        st.info(explanation)

st.divider()
st.subheader("Demo: Agent Conflict Resolution")
st.caption(
    "The real scheduler never produces overlapping tasks, so the agent loop never "
    "triggers on normal inputs. This demo forces a pre-built conflict (Walk 7:00–7:30 "
    "overlaps Feed 7:15–7:35) so you can watch K2 Think V2 resolve it live."
)

if st.button("Run conflict demo", type="primary"):
    demo_owner = Owner(
        name="Demo",
        contactInfo="demo@example.com",
        availableTimeSlots=[TimeSlot(time(7, 0), time(10, 0))],
    )
    demo_pet = Pet(name="Baxter", type="dog", age=3)
    walk_task = Task(
        name="Walk",
        duration=timedelta(minutes=30),
        priority=9,
        pet=demo_pet,
        preferredTime=TimeSlot(time(7, 0), time(8, 0)),
    )
    feed_task = Task(
        name="Feed",
        duration=timedelta(minutes=20),
        priority=6,
        pet=demo_pet,
        preferredTime=TimeSlot(time(7, 0), time(8, 0)),
    )
    demo_pet.addTask(walk_task)
    demo_pet.addTask(feed_task)
    demo_scheduler = Scheduler(owner=demo_owner, pets=[demo_pet])

    # Walk 7:00–7:30 overlaps Feed 7:15–7:35
    conflict_sched = Schedule(date=date.today())
    conflict_sched.addScheduledTask(
        ScheduledTask(task=walk_task, startTime=time(7, 0), endTime=time(7, 30))
    )
    conflict_sched.addScheduledTask(
        ScheduledTask(task=feed_task, startTime=time(7, 15), endTime=time(7, 35))
    )

    # First call returns the pre-built conflict; later calls use the real scheduler
    # so the agent's modifications (relax preferred time, lower priority) take effect.
    real_generate = demo_scheduler.generateDailySchedule
    first_call = [True]

    def _first_conflicting_then_real():
        if first_call[0]:
            first_call[0] = False
            return conflict_sched
        return real_generate()

    with patch.object(demo_scheduler, "generateDailySchedule", side_effect=_first_conflicting_then_real):
        with st.spinner("AI agent resolving conflict…"):
            demo_schedule, demo_log = run_agentic_schedule(demo_scheduler)

    with st.expander("🤖 Agent activity (demo)", expanded=True):
        for entry in demo_log:
            before = entry["conflicts_before"]
            label = f"**Iteration {entry['iteration']}** — {entry['summary']}"
            if before == 0:
                st.success(label)
            else:
                st.info(f"{label} *(conflicts before: {before})*")

    demo_tasks = demo_schedule.getTasks()
    if demo_tasks:
        st.markdown("### Demo Schedule (after agent)")
        st.table([
            {
                "Time": (
                    f"{dt.startTime.strftime('%I:%M %p')} – "
                    f"{dt.endTime.strftime('%I:%M %p')}"
                ),
                "Pet": dt.task.pet.name,
                "Task": dt.task.name,
                "Priority": dt.task.priority,
                "Duration": f"{int(dt.task.duration.total_seconds() // 60)} min",
            }
            for dt in demo_tasks
        ])

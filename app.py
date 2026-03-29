import streamlit as st
from datetime import time, timedelta
from pawpal_system import Owner, Pet, Task, TimeSlot, Scheduler

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
    # Build pets from session state
    pets_map = {p.name: p for p in st.session_state.pets}

    priority_map = {"low": 1, "medium": 2, "high": 3}
    period_slots = {
        "Morning": TimeSlot(startTime=time(7, 0), endTime=time(10, 0)),
        "Afternoon": TimeSlot(startTime=time(12, 0), endTime=time(17, 0)),
        "Evening": TimeSlot(startTime=time(17, 0), endTime=time(20, 0)),
    }

    for t in st.session_state.tasks:
        pet_name_for_task = t.get("pet_name")
        if pet_name_for_task not in pets_map:
            continue

        duration_td = timedelta(minutes=int(t["duration_minutes"]))
        preferred_time = None
        if t.get("preferred_period") in period_slots:
            preferred_time = period_slots[t["preferred_period"]]

        task = Task(
            name=t["title"],
            duration=duration_td,
            priority=priority_map.get(t.get("priority", "low"), 1),
            pet=pets_map[pet_name_for_task],
            preferredTime=preferred_time,
        )
        pets_map[pet_name_for_task].addTask(task)

    scheduler = Scheduler(owner=owner, pets=list(pets_map.values()))
    schedule = scheduler.generateDailySchedule()

    if schedule.getTasks():
        st.success("Schedule generated!")
        for stask in schedule.getTasks():
            st.write(
                f"{stask.startTime.strftime('%I:%M %p')} - {stask.endTime.strftime('%I:%M %p')} : "
                f"{stask.task.pet.name} - {stask.task.name} (priority {stask.task.priority})"
            )

        st.markdown("### Plan Explanation")
        for line in schedule.explainSchedule().splitlines():
            st.markdown(f"- {line}")
    else:
        st.warning("No tasks could be scheduled with current availability/prefs.")

from datetime import date, time, timedelta

from pawpal_system import Owner, Pet, Schedule, ScheduledTask, Scheduler, Task, TimeSlot


def test_task_completion_marks_completed():
    pet = Pet(name='Baxter', type='dog', age=4)
    task = Task(name='Walk', duration=timedelta(minutes=20), priority=5, pet=pet)
    assert not task.completed

    task.markCompleted()

    assert task.completed


def test_pet_add_task_increases_count():
    pet = Pet(name='Mittens', type='cat', age=2)
    assert len(pet.getTasks()) == 0

    task = Task(name='Feed', duration=timedelta(minutes=10), priority=8, pet=pet)
    pet.addTask(task)

    assert len(pet.getTasks()) == 1


def test_recurring_task_mark_completed_creates_next_instance():
    pet = Pet(name='Mittens', type='cat', age=2)
    task = Task(
        name='Daily Feed',
        duration=timedelta(minutes=15),
        priority=8,
        pet=pet,
        recurrence='daily',
        dueDate=date.today(),
    )
    pet.addTask(task)

    next_task = task.markCompleted(date.today())

    assert task.completed
    assert next_task is not None
    assert next_task.name == task.name
    assert next_task.pet == pet
    assert next_task.dueDate == date.today() + timedelta(days=1)


def test_scheduler_complete_task_appends_recurring():
    owner = Owner(name='Arely', contactInfo='arely@example.com')
    pet = Pet(name='Baxter', type='dog', age=4)
    task = Task(
        name='Evening Walk',
        duration=timedelta(minutes=30),
        priority=9,
        pet=pet,
        recurrence='daily',
        dueDate=date.today(),
    )
    pet.addTask(task)

    scheduler = Scheduler(owner, [pet])
    next_task = scheduler.complete_task('Evening Walk', date.today())

    assert task.completed
    assert next_task is not None
    assert next_task.dueDate == date.today() + timedelta(days=1)
    assert len(pet.tasks) == 2


# ── Sorting correctness ───────────────────────────────────────────────────────

def test_sort_tasks_returns_chronological_order():
    """Higher-priority tasks come first; equal-priority tasks sort by pet name
    then preferred start time, so the final schedule is in chronological order."""
    owner = Owner(name='Arely', contactInfo='arely@example.com')
    pet_a = Pet(name='Alpha', type='dog', age=3)
    pet_b = Pet(name='Beta', type='cat', age=2)

    low = Task(
        name='Low Walk',
        duration=timedelta(minutes=20),
        priority=3,
        pet=pet_a,
        preferredTime=TimeSlot(time(8, 0), time(9, 0)),
    )
    high = Task(
        name='High Feed',
        duration=timedelta(minutes=15),
        priority=9,
        pet=pet_b,
        preferredTime=TimeSlot(time(10, 0), time(11, 0)),
    )
    mid = Task(
        name='Mid Groom',
        duration=timedelta(minutes=30),
        priority=6,
        pet=pet_a,
        preferredTime=TimeSlot(time(9, 0), time(10, 0)),
    )

    scheduler = Scheduler(owner, [pet_a, pet_b])
    sorted_tasks = scheduler.sortTasks([low, high, mid])

    assert [t.name for t in sorted_tasks] == ['High Feed', 'Mid Groom', 'Low Walk']


# ── Recurrence logic ─────────────────────────────────────────────────────────

def test_daily_recurrence_due_date_advances_by_one_day():
    """Completing a daily task must produce a new task due the next calendar day,
    regardless of what day of the week it is."""
    today = date(2026, 3, 29)  # Sunday — ensures no weekday bias
    pet = Pet(name='Baxter', type='dog', age=4)
    task = Task(
        name='Morning Walk',
        duration=timedelta(minutes=30),
        priority=7,
        pet=pet,
        recurrence='daily',
        dueDate=today,
    )

    next_task = task.markCompleted(today)

    assert task.completed
    assert next_task is not None
    assert next_task.recurrence == 'daily'
    assert next_task.dueDate == date(2026, 3, 30)
    assert not next_task.completed


# ── Conflict detection ────────────────────────────────────────────────────────

def test_detect_conflicts_flags_overlapping_tasks():
    """Two tasks sharing an overlapping time window must be reported as a conflict."""
    pet = Pet(name='Baxter', type='dog', age=4)

    task_a = Task(name='Walk', duration=timedelta(minutes=30), priority=5, pet=pet)
    task_b = Task(name='Feed', duration=timedelta(minutes=20), priority=5, pet=pet)

    # Manually build a schedule where both tasks overlap (09:00–09:30 vs 09:15–09:35)
    scheduled_a = ScheduledTask(task=task_a, startTime=time(9, 0), endTime=time(9, 30))
    scheduled_b = ScheduledTask(task=task_b, startTime=time(9, 15), endTime=time(9, 35))

    sched = Schedule(date=date.today())
    sched.addScheduledTask(scheduled_a)
    sched.addScheduledTask(scheduled_b)

    conflicts = sched.detect_conflicts()

    assert len(conflicts) == 1
    assert 'Walk' in conflicts[0]
    assert 'Feed' in conflicts[0]


def test_detect_conflicts_no_conflict_for_back_to_back_tasks():
    """Tasks that are adjacent (one ends exactly when the next begins) must NOT
    be flagged as conflicts."""
    pet = Pet(name='Baxter', type='dog', age=4)

    task_a = Task(name='Walk', duration=timedelta(minutes=30), priority=5, pet=pet)
    task_b = Task(name='Feed', duration=timedelta(minutes=20), priority=5, pet=pet)

    scheduled_a = ScheduledTask(task=task_a, startTime=time(9, 0), endTime=time(9, 30))
    scheduled_b = ScheduledTask(task=task_b, startTime=time(9, 30), endTime=time(9, 50))

    sched = Schedule(date=date.today())
    sched.addScheduledTask(scheduled_a)
    sched.addScheduledTask(scheduled_b)

    conflicts = sched.detect_conflicts()

    assert conflicts == []

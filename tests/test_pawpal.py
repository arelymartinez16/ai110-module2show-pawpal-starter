from datetime import date, time, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task


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

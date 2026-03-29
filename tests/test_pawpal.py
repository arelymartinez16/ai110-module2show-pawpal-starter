from datetime import time, timedelta

from pawpal_system import Pet, Task


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

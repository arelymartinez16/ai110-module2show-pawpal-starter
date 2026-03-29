from datetime import time, timedelta

from pawpal_system import Owner, Pet, Task, TimeSlot, Scheduler


def main():
    owner = Owner(
        name='Arely',
        contactInfo='arely@example.com',
        availableTimeSlots=[
            TimeSlot(startTime=time(7, 0), endTime=time(10, 0)), # 7:00 - 10:00
            TimeSlot(startTime=time(17, 0), endTime=time(20, 0)), # 17:00 - 20:00 (5:00 PM - 8:00 PM)
        ],
        preferences={'minPriority': 1},
    )

    dog = Pet(name='Baxter', type='dog', age=4)
    cat = Pet(name='Mittens', type='cat', age=2)

    task1 = Task(
        name='Morning Walk',
        duration=timedelta(minutes=30),
        priority=9,
        pet=dog,
        preferredTime=TimeSlot(startTime=time(7, 30), endTime=time(8, 0)), # 7:30 - 8:00
    )
    task2 = Task(
        name='Feed Breakfast',
        duration=timedelta(minutes=15),
        priority=10,
        pet=cat,
        preferredTime=TimeSlot(startTime=time(8, 0), endTime=time(8, 15)), # 8:00 - 8:15
    )
    task3 = Task(
        name='Evening Play',
        duration=timedelta(minutes=45),
        priority=7,
        pet=dog,
        preferredTime=TimeSlot(startTime=time(17, 30), endTime=time(18, 15)), # 17:30 - 18:15 (5:30 PM - 6:15 PM)
    )
    task4 = Task(
        name='Midday Brush',
        duration=timedelta(minutes=20),
        priority=5,
        pet=cat,
        preferredTime=TimeSlot(startTime=time(12, 0), endTime=time(12, 20)),
    )
    task5 = Task(
        name='Evening Treat',
        duration=timedelta(minutes=10),
        priority=8,
        pet=dog,
        preferredTime=TimeSlot(startTime=time(18, 15), endTime=time(18, 25)),
    )

    # add out of logical timeline order to validate sorting
    dog.addTask(task3)
    cat.addTask(task2)
    dog.addTask(task1)
    cat.addTask(task4)
    dog.addTask(task5)

    scheduler = Scheduler(owner, [dog, cat])
    today_schedule = scheduler.generateDailySchedule()

    print("Today's Schedule")
    print("------------------")
    print(today_schedule.explainSchedule(owner.availableTimeSlots))

    print("\n-- Debug views --")
    print("All tasks by priority+pet:")
    for t in scheduler.sortTasks([t for p in [dog, cat] for t in p.getTasks()]):
        print(f"  {t.priority} - {t.pet.name} - {t.name} ({t.preferredTime.formatted() if t.preferredTime else 'no pref'})")

    print("\nPending tasks:")
    for t in scheduler.get_pending_tasks():
        print(f"  {t.pet.name}: {t.name} (priority {t.priority})")

    print("\nTasks due today:")
    for t in scheduler.get_due_today_tasks():
        print(f"  {t.pet.name}: {t.name}")

    print("\nScheduled tasks (chronological):")
    for st in today_schedule.getTasks():
        print(f"  {st.startTime.strftime('%I:%M %p')} - {st.endTime.strftime('%I:%M %p')} : {st.task.pet.name} - {st.task.name}")

    print("\nConflicts:")
    for c in today_schedule.detect_conflicts():
        print(f"  {c}")


if __name__ == '__main__':
    main()
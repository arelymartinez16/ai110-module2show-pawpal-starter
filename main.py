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

    dog.addTask(task1)
    dog.addTask(task3)
    cat.addTask(task2)

    scheduler = Scheduler(owner, [dog, cat])
    today_schedule = scheduler.generateDailySchedule()

    print("Today's Schedule")
    print("------------------")
    print(today_schedule.explainSchedule())


if __name__ == '__main__':
    main()
from dataclasses import dataclass, field
from datetime import date, time, timedelta, datetime
from typing import List, Dict, Optional, Any

@dataclass
class TimeSlot:
    startTime: time
    endTime: time

    def overlapsWith(self, other: 'TimeSlot') -> bool:
        """Return True if this TimeSlot overlaps another."""
        return self.startTime < other.endTime and other.startTime < self.endTime

    def duration(self) -> timedelta:
        """Return the duration of this TimeSlot."""
        start_dt = datetime.combine(date.min, self.startTime)
        end_dt = datetime.combine(date.min, self.endTime)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        return end_dt - start_dt

    def formatted(self) -> str:
        """Return this TimeSlot as a formatted AM/PM string."""
        return f"{self.startTime.strftime('%I:%M %p')} - {self.endTime.strftime('%I:%M %p')}"

@dataclass
class Constraint:
    type: str
    details: Dict[str, Any]

    def appliesTo(self, task: 'Task') -> bool:
        """Return True if this constraint applies to the given task."""
        if self.type == 'pet' and 'petName' in self.details:
            return task.pet.name == self.details['petName']
        if self.type == 'priority' and 'minPriority' in self.details:
            return task.priority >= self.details['minPriority']
        if self.type == 'taskName' and 'pattern' in self.details:
            return self.details['pattern'].lower() in task.name.lower()
        return True

    def isSatisfied(self, timeSlot: TimeSlot) -> bool:
        """Return True if this constraint is satisfied by a given TimeSlot."""
        if self.type == 'availableWindow' and 'slot' in self.details:
            constraint_slot = self.details['slot']
            return constraint_slot.startTime <= timeSlot.startTime and timeSlot.endTime <= constraint_slot.endTime
        if self.type == 'notNight' and self.details.get('enabled', False):
            return not (timeSlot.startTime >= time(22, 0) or timeSlot.endTime <= time(6, 0))
        return True

@dataclass
class Task:
    name: str
    duration: timedelta
    priority: int
    pet: 'Pet'
    preferredTime: Optional[TimeSlot] = None
    completed: bool = False
    constraints: List[Constraint] = field(default_factory=list)

    def markCompleted(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def updateTask(self, details: Dict[str, Any]) -> None:
        """Update task fields from a dictionary."""
        for key, value in details.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def isDue(self, today: date) -> bool:
        """Return True if the task is still due."""
        return not self.completed

@dataclass
class Pet:
    name: str
    type: str
    age: int
    specialNeeds: List[str] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

    def addTask(self, task: Task) -> None:
        """Add a new task to this pet."""
        self.tasks.append(task)

    def removeTask(self, taskId: str) -> None:
        """Remove a task by its name."""
        self.tasks = [t for t in self.tasks if t.name != taskId]

    def getTasks(self) -> List[Task]:
        """Return the list of tasks for this pet."""
        return self.tasks

    def updatePetInfo(self, info: Dict[str, Any]) -> None:
        """Update pet details from a dict."""
        for key, value in info.items():
            if hasattr(self, key):
                setattr(self, key, value)

@dataclass
class Owner:
    name: str
    contactInfo: str
    availableTimeSlots: List[TimeSlot] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Constraint] = field(default_factory=list)

    def updateAvailability(self, newSlots: List[TimeSlot]) -> None:
        """Set owner's available TimeSlots."""
        self.availableTimeSlots = newSlots

    def updatePreferences(self, preferences: Dict[str, Any]) -> None:
        """Merge new preferences into existing preferences."""
        self.preferences.update(preferences)

    def getConstraints(self) -> List[Constraint]:
        """Return owner constraints, including preference-derived constraints."""
        combined = list(self.constraints)
        if 'minPriority' in self.preferences:
            combined.append(Constraint('priority', {'minPriority': self.preferences['minPriority']}))
        return combined

@dataclass
class ScheduledTask:
    task: Task
    startTime: time
    endTime: time

    def reschedule(self, newStartTime: time) -> None:
        """Reschedule this task to start at a new time."""
        duration = self.getDuration()
        self.startTime = newStartTime
        end_dt = datetime.combine(date.min, newStartTime) + duration
        self.endTime = end_dt.time()

    def getDuration(self) -> timedelta:
        """Return the duration between start and end times."""
        start_dt = datetime.combine(date.min, self.startTime)
        end_dt = datetime.combine(date.min, self.endTime)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        return end_dt - start_dt

@dataclass
class Schedule:
    date: date
    scheduledTasks: List[ScheduledTask] = field(default_factory=list)

    def addScheduledTask(self, task: ScheduledTask) -> None:
        """Add a scheduled task to this daily schedule."""
        self.scheduledTasks.append(task)

    def removeScheduledTask(self, taskId: str) -> None:
        """Remove a scheduled task by task name."""
        self.scheduledTasks = [s for s in self.scheduledTasks if s.task.name != taskId]

    def getTasks(self) -> List[ScheduledTask]:
        """Return the list of scheduled tasks."""
        return self.scheduledTasks

    def explainSchedule(self) -> str:
        """Return a concise, personalized paragraph explaining schedule generation."""
        if not self.scheduledTasks:
            return "No tasks were scheduled because no matching available slots were found."

        tasks_by_priority = sorted(self.scheduledTasks, key=lambda x: x.task.priority, reverse=True)
        top_task = tasks_by_priority[0].task
        pet_names = sorted({st.task.pet.name for st in self.scheduledTasks})

        first_slot = min(self.scheduledTasks, key=lambda st: st.startTime)
        last_slot = max(self.scheduledTasks, key=lambda st: st.endTime)

        pref_used = [st for st in self.scheduledTasks if st.task.preferredTime]
        low_priority = [st for st in self.scheduledTasks if st.task.priority < 2]

        sentence1 = (
            f"Tasks were sorted by priority, so high-priority tasks like '{top_task.name}' for "
            f"{top_task.pet.name} were given scheduling precedence."
        )
        sentence2 = (
            f"The planner placed each task in the earliest available owner window "
            f"from {first_slot.startTime.strftime('%I:%M %p')} to {last_slot.endTime.strftime('%I:%M %p')}."
        )
        sentence3 = (
            "Preferred time ranges were respected when provided" +
            (" (one or more preferred slots used)." if pref_used else " (no preferred times were set).")
        )
        sentence4 = (
            "Lower-priority tasks for "
            f"{', '.join(sorted({st.task.pet.name for st in low_priority})) or 'no pets'} were placed afterward and may be delayed "
            "if the day is fully booked."
        )

        return " ".join([sentence1, sentence2, sentence3, sentence4])

@dataclass
class Scheduler:
    owner: Owner
    pets: List[Pet] = field(default_factory=list)

    def generateDailySchedule(self) -> Schedule:
        """Generate a schedule for the day based on owner availability and tasks."""
        all_tasks = [t for pet in self.pets for t in pet.tasks if not t.completed]
        tasks = self.sortTasksByPriority(all_tasks)
        return self.fitTasksIntoTimeSlots(tasks, self.owner.availableTimeSlots)

    def sortTasksByPriority(self, tasks: List[Task]) -> List[Task]:
        """Return tasks sorted by descending priority."""
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def _subtract_slot(self, free_slots: List[TimeSlot], used: TimeSlot) -> List[TimeSlot]:
        """Return free slots with the used slot removed."""
        result = []
        for slot in free_slots:
            if not slot.overlapsWith(used):
                result.append(slot)
                continue
            if slot.startTime < used.startTime:
                result.append(TimeSlot(slot.startTime, used.startTime))
            if used.endTime < slot.endTime:
                result.append(TimeSlot(used.endTime, slot.endTime))
        return result

    def _find_fit(self, task: Task, free_slots: List[TimeSlot]) -> Optional[ScheduledTask]:
        """Return a ScheduledTask that fits the given task in free slots, or None."""
        duration_minutes = int(task.duration.total_seconds() / 60)

        def can_fit(interval: TimeSlot, start_time: time) -> bool:
            start_dt = datetime.combine(date.min, start_time)
            end_dt = start_dt + task.duration
            end_time = end_dt.time()
            if end_dt.date() > date.min:
                end_time = time(23, 59)
            return TimeSlot(start_time, end_time).duration() >= task.duration

        for slot in sorted(free_slots, key=lambda s: s.startTime):
            if task.preferredTime:
                if not slot.overlapsWith(task.preferredTime):
                    continue

                pref_start = max(slot.startTime, task.preferredTime.startTime)
                end_dt = datetime.combine(date.min, pref_start) + task.duration
                candidate_slot = TimeSlot(pref_start, end_dt.time())

                if can_fit(slot, pref_start) and all(c.appliesTo(task) and c.isSatisfied(candidate_slot) for c in self.owner.getConstraints() + task.constraints):
                    return ScheduledTask(task, pref_start, end_dt.time())

                continue

            preferred_start = slot.startTime
            if can_fit(slot, preferred_start):
                end_dt = datetime.combine(date.min, preferred_start) + task.duration
                candidate_slot = TimeSlot(preferred_start, end_dt.time())
                if all(c.appliesTo(task) and c.isSatisfied(candidate_slot) for c in self.owner.getConstraints() + task.constraints):
                    return ScheduledTask(task, preferred_start, end_dt.time())

        return None

    def fitTasksIntoTimeSlots(self, tasks: List[Task], timeSlots: List[TimeSlot]) -> Schedule:
        """Fill the schedule by placing tasks into available time slots."""
        schedule = Schedule(date.today())
        free_slots = sorted(timeSlots, key=lambda x: x.startTime)

        remaining_tasks = tasks[:]
        progress = True

        while progress and remaining_tasks:
            progress = False
            for task in list(remaining_tasks):
                scheduled = self._find_fit(task, free_slots)
                if scheduled:
                    schedule.addScheduledTask(scheduled)
                    used = TimeSlot(scheduled.startTime, scheduled.endTime)
                    free_slots = self._subtract_slot(free_slots, used)
                    remaining_tasks.remove(task)
                    progress = True

        schedule.scheduledTasks.sort(key=lambda st: st.startTime)
        return schedule

    def explainDecision(self, task: Task) -> str:
        """Explain why a specific task was scheduled or not."""
        if task.completed:
            return f"Task '{task.name}' for {task.pet.name} is already completed."
        if task.preferredTime:
            pref = f"{task.preferredTime.startTime.strftime('%I:%M %p')} - {task.preferredTime.endTime.strftime('%I:%M %p')}"
        else:
            pref = "No preference"
        return f"Task '{task.name}' for {task.pet.name} has priority {task.priority} and preferred time {pref}."

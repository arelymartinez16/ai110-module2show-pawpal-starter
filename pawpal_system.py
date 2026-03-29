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
    dueDate: Optional[date] = None
    recurrence: Optional[str] = None  # 'daily', 'weekly', or None

    def markCompleted(self, today: Optional[date] = None) -> Optional['Task']:
        """Mark this task as completed and return the next recurrence instance if any."""
        if today is None:
            today = date.today()

        self.completed = True

        if self.recurrence not in ('daily', 'weekly'):
            return None

        next_due = today + timedelta(days=1 if self.recurrence == 'daily' else 7)

        new_task = Task(
            name=self.name,
            duration=self.duration,
            priority=self.priority,
            pet=self.pet,
            preferredTime=self.preferredTime,
            completed=False,
            constraints=[Constraint(c.type, dict(c.details)) for c in self.constraints],
            dueDate=next_due,
            recurrence=self.recurrence,
        )

        return new_task

    def updateTask(self, details: Dict[str, Any]) -> None:
        """Update task fields from a dictionary."""
        for key, value in details.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def isDue(self, today: date) -> bool:
        """Return True if the task is due today or still pending."""
        if self.completed:
            return False

        if self.recurrence == 'daily':
            return True
        if self.recurrence == 'weekly':
            return today.weekday() == (self.dueDate.weekday() if self.dueDate else today.weekday())

        if self.dueDate is None:
            return True

        return self.dueDate <= today

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

    def detect_conflicts(self) -> List[str]:
        """Detect overlapping scheduled tasks in this schedule."""
        conflicts = []
        sorted_tasks = sorted(self.scheduledTasks, key=lambda st: (st.startTime, st.endTime))
        for i in range(len(sorted_tasks) - 1):
            current = sorted_tasks[i]
            nxt = sorted_tasks[i + 1]
            # overlap when next task starts before current task ends
            if nxt.startTime < current.endTime:
                conflicts.append(
                    f"Conflict: '{current.task.name}' ({current.task.pet.name}) "
                    f"{current.startTime.strftime('%I:%M %p')}-{current.endTime.strftime('%I:%M %p')} "
                    f"overlaps with '{nxt.task.name}' ({nxt.task.pet.name}) "
                    f"{nxt.startTime.strftime('%I:%M %p')}-{nxt.endTime.strftime('%I:%M %p')}"
                )
        return conflicts

    def explainSchedule_old(self) -> str:
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
        conflicts = self.detect_conflicts()
        conflict_text = (
            f" There are {len(conflicts)} conflict(s): {conflicts[0]}" if conflicts else ""
        )

        sentence4 = (
            "Lower-priority tasks for "
            f"{', '.join(sorted({st.task.pet.name for st in low_priority})) or 'no pets'} were placed afterward and may be delayed "
            "if the day is fully booked."
        )

        return " ".join([sentence1, sentence2, sentence3, sentence4]) + conflict_text

    def explainSchedule(self, available_slots: Optional[List[TimeSlot]] = None) -> str:
        """Return a concise human-readable explanation of the generated schedule."""
        if not self.scheduledTasks:
            if available_slots:
                blocks = ", ".join(slot.formatted() for slot in sorted(available_slots, key=lambda s: s.startTime))
                return f"No tasks were scheduled. Owner availability blocks were: {blocks}."
            return "No tasks were scheduled because no matching available slots were found."

        by_time = sorted(self.scheduledTasks, key=lambda st: st.startTime)
        by_priority = sorted(self.scheduledTasks, key=lambda st: (-st.task.priority, st.startTime))

        all_pets = sorted({st.task.pet.name for st in self.scheduledTasks})
        low_tasks = [st for st in by_priority if st.task.priority < 8]

        lines = [
            f"Scheduled {len(self.scheduledTasks)} tasks for {', '.join(all_pets)}.",
            f"Priority order: {', '.join([f'{st.task.name} ({st.task.pet.name})' for st in by_priority])}.",
            "High-priority tasks are scheduled before lower-priority tasks within available blocks.",
        ]

        if available_slots:
            sorted_slots = sorted(available_slots, key=lambda s: s.startTime)
            slot_text = ", ".join(slot.formatted() for slot in sorted_slots)
            lines.append(f"Owner availability blocks: {slot_text}.")

            gaps = []
            for block in sorted_slots:
                block_tasks = [st for st in by_time if st.startTime >= block.startTime and st.endTime <= block.endTime]
                cursor = block.startTime
                for st in block_tasks:
                    if cursor < st.startTime:
                        gaps.append(TimeSlot(cursor, st.startTime))
                    cursor = max(cursor, st.endTime)
                if cursor < block.endTime:
                    gaps.append(TimeSlot(cursor, block.endTime))

            if gaps:
                gap_text = ", ".join(g.formatted() for g in gaps)
                lines.append(f"Gaps inside availability blocks: {gap_text}.")
            else:
                lines.append("No gaps detected inside availability blocks.")
        else:
            first_slot = by_time[0]
            last_slot = by_time[-1]
            lines.append(
                f"Tasks span from {first_slot.startTime.strftime('%I:%M %p')} "
                f"to {last_slot.endTime.strftime('%I:%M %p')} and may have implicit gaps between tasks."
            )

        lines.append("Scheduled tasks in chronological order:")
        for st in by_time:
            lines.append(
                f"- {st.startTime.strftime('%I:%M %p')} to {st.endTime.strftime('%I:%M %p')}: "
                f"{st.task.name} ({st.task.pet.name}, priority {st.task.priority})"
            )

        if low_tasks:
            lines.append(f"Lower-priority tasks included: {', '.join([st.task.name for st in low_tasks])}.")

        conflicts = self.detect_conflicts()
        if conflicts:
            lines.append(f"Conflicts detected ({len(conflicts)}): {', '.join(conflicts)}")

        return " ".join(lines)

@dataclass
class Scheduler:
    owner: Owner
    pets: List[Pet] = field(default_factory=list)

    def generateDailySchedule(self, today: Optional[date] = None) -> Schedule:
        """Generate a schedule for the day based on owner availability and tasks."""
        if today is None:
            today = date.today()

        all_tasks = [t for pet in self.pets for t in pet.tasks if not t.completed and t.isDue(today)]
        constraint_tasks = self.apply_constraints(all_tasks)
        tasks = self.sortTasks(constraint_tasks)
        return self.fitTasksIntoTimeSlots(tasks, self.owner.availableTimeSlots)

    def sortTasks(self, tasks: List[Task]) -> List[Task]:
        """Return tasks sorted by priority, pet name, and preferred start time."""
        def key(t: Task):
            preferred_start = t.preferredTime.startTime if t.preferredTime else time(0, 0)
            return (-t.priority, t.pet.name.lower(), preferred_start)

        return sorted(tasks, key=key)

    def apply_constraints(self, tasks: List[Task]) -> List[Task]:
        """Filter tasks by owner and task constraints."""
        owner_constraints = self.owner.getConstraints()
        return [t for t in tasks if all(c.appliesTo(t) for c in owner_constraints + t.constraints)]

    def get_tasks_by_pet(self, pet_name: str) -> List[Task]:
        """Return all tasks across all pets matching this pet name."""
        return [t for pet in self.pets if pet.name == pet_name for t in pet.tasks]

    def get_pending_tasks(self) -> List[Task]:
        """Return all pending tasks across pets."""
        return [t for pet in self.pets for t in pet.tasks if not t.completed]

    def get_completed_tasks(self) -> List[Task]:
        """Return all completed tasks across pets."""
        return [t for pet in self.pets for t in pet.tasks if t.completed]

    def get_due_today_tasks(self, today: Optional[date] = None) -> List[Task]:
        """Return all tasks due today."""
        if today is None:
            today = date.today()
        return [t for pet in self.pets for t in pet.tasks if t.isDue(today)]

    def complete_task(self, task_name: str, today: Optional[date] = None) -> Optional[Task]:
        """Mark a task complete and create the next recurring instance if applicable."""
        for pet in self.pets:
            for task in pet.tasks:
                if task.name == task_name and not task.completed:
                    next_task = task.markCompleted(today)
                    if next_task is not None:
                        pet.addTask(next_task)
                    return next_task
        return None

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
        constraints = self.owner.getConstraints() + task.constraints
        for slot in sorted(free_slots, key=lambda s: s.startTime):
            if task.preferredTime and not slot.overlapsWith(task.preferredTime):
                continue

            start = max(slot.startTime, task.preferredTime.startTime) if task.preferredTime else slot.startTime
            end_dt = datetime.combine(date.min, start) + task.duration
            end = end_dt.time()

            candidate = TimeSlot(start, end)
            if candidate.duration() < task.duration:
                continue
            if all(c.appliesTo(task) and c.isSatisfied(candidate) for c in constraints):
                return ScheduledTask(task, start, end)
        return None
        # duration_minutes = int(task.duration.total_seconds() / 60)

        # def can_fit(interval: TimeSlot, start_time: time) -> bool:
        #     start_dt = datetime.combine(date.min, start_time)
        #     end_dt = start_dt + task.duration
        #     end_time = end_dt.time()
        #     if end_dt.date() > date.min:
        #         end_time = time(23, 59)
        #     return TimeSlot(start_time, end_time).duration() >= task.duration

        # for slot in sorted(free_slots, key=lambda s: s.startTime):
        #     if task.preferredTime:
        #         if not slot.overlapsWith(task.preferredTime):
        #             continue

        #         pref_start = max(slot.startTime, task.preferredTime.startTime)
        #         end_dt = datetime.combine(date.min, pref_start) + task.duration
        #         candidate_slot = TimeSlot(pref_start, end_dt.time())

        #         if can_fit(slot, pref_start) and all(c.appliesTo(task) and c.isSatisfied(candidate_slot) for c in self.owner.getConstraints() + task.constraints):
        #             return ScheduledTask(task, pref_start, end_dt.time())

        #         continue

        #     preferred_start = slot.startTime
        #     if can_fit(slot, preferred_start):
        #         end_dt = datetime.combine(date.min, preferred_start) + task.duration
        #         candidate_slot = TimeSlot(preferred_start, end_dt.time())
        #         if all(c.appliesTo(task) and c.isSatisfied(candidate_slot) for c in self.owner.getConstraints() + task.constraints):
        #             return ScheduledTask(task, preferred_start, end_dt.time())

        # return None

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

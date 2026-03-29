from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import List, Map, Optional, Any

@dataclass
class TimeSlot:
    startTime: time
    endTime: time

    def overlapsWith(self, other: 'TimeSlot') -> bool:
        pass

    def duration(self) -> timedelta:
        pass


@dataclass
class Constraint:
    type: str
    details: Map[str, Any]

    def appliesTo(self, task: 'Task') -> bool:
        pass

    def isSatisfied(self, timeSlot: TimeSlot) -> bool:
        pass


@dataclass
class Task:
    name: str
    duration: timedelta
    priority: int
    pet: 'Pet'
    preferredTime: Optional[TimeSlot] = None
    completed: bool = False

    def markCompleted(self) -> None:
        pass

    def updateTask(self, details: Map[str, Any]) -> None:
        pass

    def isDue(self, today: date) -> bool:
        pass


@dataclass
class Pet:
    name: str
    type: str
    age: int
    specialNeeds: List[str] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

    def addTask(self, task: Task) -> None:
        pass

    def removeTask(self, taskId: str) -> None:
        pass

    def getTasks(self) -> List[Task]:
        pass

    def updatePetInfo(self, info: Map[str, Any]) -> None:
        pass


@dataclass
class Owner:
    name: str
    availableTimeSlots: List[TimeSlot] = field(default_factory=list)
    preferences: Map[str, Any] = field(default_factory=dict)

    def updateAvailability(self, newSlots: List[TimeSlot]) -> None:
        pass

    def updatePreferences(self, preferences: Map[str, Any]) -> None:
        pass

    def getConstraints(self) -> List[Constraint]:
        pass


@dataclass
class ScheduledTask:
    task: Task
    startTime: time
    endTime: time

    def reschedule(self, newStartTime: time) -> None:
        pass

    def getDuration(self) -> timedelta:
        pass


@dataclass
class Schedule:
    date: date
    scheduledTasks: List[ScheduledTask] = field(default_factory=list)

    def addScheduledTask(self, task: ScheduledTask) -> None:
        pass

    def removeScheduledTask(self, taskId: str) -> None:
        pass

    def getTasks(self) -> List[ScheduledTask]:
        pass

    def explainSchedule(self) -> str:
        pass


@dataclass
class Scheduler:
    owner: Owner
    pets: List[Pet] = field(default_factory=list)

    def generateDailySchedule(self) -> Schedule:
        pass

    def sortTasksByPriority(self, tasks: List[Task]) -> List[Task]:
        pass

    def fitTasksIntoTimeSlots(self, tasks: List[Task], timeSlots: List[TimeSlot]) -> Schedule:
        pass

    def explainDecision(self, task: Task) -> str:
        pass
"""An in-memory clinic back end so the example runs without a database.

Everything is keyed by patient subject. The clock is fixed so tests and the article
quote stable dates. ``fail_next`` lets tests simulate an upstream outage, which is
how the error outcome is exercised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

TODAY = date(2026, 10, 5)
NOW = datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc)


class UpstreamUnavailable(Exception):
    pass


@dataclass
class Appointment:
    id: str
    patient: str
    clinician: str
    clinician_type: str
    starts_at: datetime
    location: str
    status: str = "booked"


@dataclass
class Slot:
    id: str
    clinician: str
    clinician_type: str
    starts_at: datetime
    location: str
    taken: bool = False


@dataclass
class Prescription:
    id: str
    patient: str
    name: str
    daily_dose: int
    quantity_dispensed: int
    dispensed_on: date
    refills_remaining: int


@dataclass
class ClinicStore:
    appointments: dict[str, Appointment] = field(default_factory=dict)
    slots: dict[str, Slot] = field(default_factory=dict)
    prescriptions: dict[str, Prescription] = field(default_factory=dict)
    bookings_by_key: dict[str, str] = field(default_factory=dict)
    refills_by_key: dict[str, str] = field(default_factory=dict)
    _failures: set[str] = field(default_factory=set)
    _down: set[str] = field(default_factory=set)
    _seq: int = 0

    # --- failure injection -------------------------------------------------
    def fail_next(self, system: str) -> None:
        """The next call to `system` fails, then it recovers."""
        self._failures.add(system)

    def set_down(self, system: str, down: bool = True) -> None:
        """`system` fails on every call until restored."""
        (self._down.add if down else self._down.discard)(system)

    def _check(self, system: str) -> None:
        if system in self._down:
            raise UpstreamUnavailable(system)
        if system in self._failures:
            self._failures.discard(system)
            raise UpstreamUnavailable(system)

    def next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq:04d}"

    # --- queries -------------------------------------------------------------
    def appointments_for(self, patient: str) -> list[Appointment]:
        self._check("appointments")
        return sorted((a for a in self.appointments.values() if a.patient == patient and a.status == "booked"), key=lambda a: a.starts_at)

    def open_slots(self) -> list[Slot]:
        self._check("appointments")
        return sorted((s for s in self.slots.values() if not s.taken), key=lambda s: s.starts_at)

    def prescriptions_for(self, patient: str) -> list[Prescription]:
        self._check("medications")
        return sorted((p for p in self.prescriptions.values() if p.patient == patient), key=lambda p: p.name)


def seed() -> ClinicStore:
    store = ClinicStore()
    day = lambda d, h, m=0: datetime(TODAY.year, TODAY.month, TODAY.day, h, m, tzinfo=timezone.utc) + timedelta(days=d)
    store.appointments["apt-1001"] = Appointment("apt-1001", "pat-1", "Dr Rao", "gp", day(3, 10, 30), "Riverside clinic")
    store.appointments["apt-1002"] = Appointment("apt-1002", "pat-1", "Nurse Patel", "nurse", day(21, 9, 0), "Riverside clinic")
    store.appointments["apt-2001"] = Appointment("apt-2001", "pat-2", "Dr Lee", "gp", day(1, 14, 0), "Hillview clinic")
    for i, (d, h, ct, who, loc) in enumerate([
        (1, 9, "gp", "Dr Rao", "Riverside clinic"), (1, 11, "gp", "Dr Lee", "Hillview clinic"),
        (2, 15, "physio", "A. Mendes", "Riverside clinic"), (4, 8, "nurse", "Nurse Patel", "Riverside clinic"),
        (6, 16, "gp", "Dr Rao", "Riverside clinic"), (12, 10, "physio", "A. Mendes", "Hillview clinic"),
    ], start=1):
        store.slots[f"slot-{i}"] = Slot(f"slot-{i}", who, ct, day(d, h), loc)
    store.prescriptions["rx-1"] = Prescription("rx-1", "pat-1", "Metformin 500mg", daily_dose=2, quantity_dispensed=56, dispensed_on=TODAY - timedelta(days=22), refills_remaining=2)
    store.prescriptions["rx-2"] = Prescription("rx-2", "pat-1", "Atorvastatin 20mg", daily_dose=1, quantity_dispensed=28, dispensed_on=TODAY - timedelta(days=5), refills_remaining=0)
    return store

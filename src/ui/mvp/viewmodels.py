"""Minimal view models for Qt UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardViewModel:
    source: str
    dest: str
    status: str
    dat_status: str

    @classmethod
    def from_state(cls, source: str, dest: str, status: str, dat_status: str) -> "DashboardViewModel":
        return cls(source=source or "-", dest=dest or "-", status=status or "-", dat_status=dat_status or "-")

    @property
    def source_display(self) -> str:
        return self.source or "-"

    @property
    def dest_display(self) -> str:
        return self.dest or "-"

    @property
    def status_display(self) -> str:
        return self.status or "-"

    @property
    def dat_display(self) -> str:
        return self.dat_status or "-"

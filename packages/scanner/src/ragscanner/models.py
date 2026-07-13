"""Minimal framework-neutral models for scaffold diagnostics."""

from pydantic import BaseModel


class ComponentStatus(BaseModel):
    ok: bool
    detail: str


class DoctorReport(BaseModel):
    version: str
    configuration: ComponentStatus
    network: ComponentStatus

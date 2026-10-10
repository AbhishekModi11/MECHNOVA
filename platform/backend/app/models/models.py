from datetime import datetime, date as dt_date, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, Float, Text, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "admin" | "worker"
    company_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)  # Employee ID
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    attendances: Mapped[list["Attendance"]] = relationship("Attendance", back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")
    machine_requests: Mapped[list["MachineRequest"]] = relationship("MachineRequest", back_populates="worker", foreign_keys="MachineRequest.worker_id")


class Machine(BaseModel):
    __tablename__ = "machines"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)  # e.g., "M-01"
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Haas VF-2"
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "3-Axis Vertical Mill"
    status: Mapped[str] = mapped_column(String(30), default="idle", nullable=False)  # "idle" | "working" | "maintenance" | "offline"
    
    current_worker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    current_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    
    travel_limits: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # {"x": 762, "y": 406, "z": 508}
    controller_type: Mapped[str] = mapped_column(String(50), default="Fanuc / Haas compatible")
    config_ref: Mapped[str] = mapped_column(String(100), default="config/machine_3axis_example.yaml")

    # Relationships
    tool_stock: Mapped[list["ToolStock"]] = relationship("ToolStock", back_populates="machine")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="machine")


class ToolStock(BaseModel):
    __tablename__ = "tool_stock"

    tool_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # Links to engine tool library
    name: Mapped[str] = mapped_column(String(150), default="")
    type: Mapped[str] = mapped_column(String(50), default="end_mill")
    diameter_mm: Mapped[float] = mapped_column(Float, default=10.0)
    machine_id: Mapped[Optional[int]] = mapped_column(ForeignKey("machines.id"), nullable=True)
    
    life_total: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)  # Total cutting minutes or ops
    life_used: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="fresh", nullable=False)  # "fresh" | "in_use" | "worn"
    last_changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    machine: Mapped[Optional["Machine"]] = relationship("Machine", back_populates="tool_stock")
    change_logs: Mapped[list["ToolChangeLog"]] = relationship("ToolChangeLog", back_populates="tool_stock")


class Attendance(BaseModel):
    __tablename__ = "attendance"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "present" | "absent" | "leave"

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="attendances")


class Project(BaseModel):
    __tablename__ = "projects"

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    material_id: Mapped[str] = mapped_column(String(50), default="aluminum_6061", nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default="step", nullable=False)  # "step" | "image_extrusion"
    source_file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    dimensions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # {"length": 100, "width": 60, "height": 20}
    
    run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    engine_status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)  # "queued"|"running"|"done"|"failed"
    status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False
    )  # "draft"|"analysed"|"requested"|"approved"|"rejected"|"deployed"|"completed"|"cancelled"
    
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_operation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects", foreign_keys=[owner_id])
    machine_request: Mapped[Optional["MachineRequest"]] = relationship("MachineRequest", back_populates="project", uselist=False)
    schedule: Mapped[Optional["Schedule"]] = relationship("Schedule", back_populates="project", uselist=False)


class MachineRequest(BaseModel):
    __tablename__ = "machine_requests"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    worker_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    requested_machine_id: Mapped[Optional[int]] = mapped_column(ForeignKey("machines.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # "pending"|"approved"|"rejected"|"scheduled"
    
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="machine_request")
    worker: Mapped["User"] = relationship("User", back_populates="machine_requests", foreign_keys=[worker_id])


class Schedule(BaseModel):
    __tablename__ = "schedules"

    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    machine: Mapped["Machine"] = relationship("Machine", back_populates="schedules")
    project: Mapped["Project"] = relationship("Project", back_populates="schedule")


class ToolChangeLog(BaseModel):
    __tablename__ = "tool_change_logs"

    tool_stock_id: Mapped[int] = mapped_column(ForeignKey("tool_stock.id"), nullable=False)
    machine_id: Mapped[Optional[int]] = mapped_column(ForeignKey("machines.id"), nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(150), nullable=False)  # "Tool worn past threshold (heuristic)"
    old_tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    new_tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tool_stock: Mapped["ToolStock"] = relationship("ToolStock", back_populates="change_logs")


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # "info" | "request_approved" | "job_completed"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")

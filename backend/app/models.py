from pydantic import BaseModel
from typing import Optional, Literal


class DevLoginIn(BaseModel):
    email: str


class TicketCreate(BaseModel):
    title: str
    description: str
    department: str
    priority: Literal["Low", "Medium", "High", "Urgent"] = "Medium"
    assignee_name: Optional[str] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    priority: Optional[Literal["Low", "Medium", "High", "Urgent"]] = None
    assignee_id: Optional[str] = None
    due_at: Optional[str] = None


class StatusIn(BaseModel):
    status: Literal["Open", "In Progress", "Pending", "Resolved", "Closed"]


class AssignIn(BaseModel):
    assignee_id: Optional[str] = None


class CommentIn(BaseModel):
    body: str
    is_internal: bool = False


class DepartmentIn(BaseModel):
    name: str
    description: Optional[str] = None


class EmployeePatch(BaseModel):
    role: Optional[Literal["admin", "employee"]] = None
    department: Optional[str] = None

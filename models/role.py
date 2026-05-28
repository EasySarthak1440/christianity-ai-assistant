from enum import Enum


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"
    auditor = "auditor"
    compliance = "compliance"

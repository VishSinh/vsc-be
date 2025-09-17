from contextvars import ContextVar

current_staff: ContextVar = ContextVar("current_staff", default=None)


def set_current_staff(staff):
    current_staff.set(staff)


def reset_current_staff():
    current_staff.set(None)


def get_current_staff():
    return current_staff.get()

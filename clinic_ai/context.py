import contextvars

# Context variable to store the current user across the thread/task
current_user = contextvars.ContextVar('current_user', default=None)

from graders import grade_task

def grade(*args, **kwargs):
    return grade_task("security_audit", kwargs.get("answer", args[0] if args else ""))

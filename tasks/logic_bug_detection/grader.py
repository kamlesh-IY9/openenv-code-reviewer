from graders import grade_task

def grade(*args, **kwargs):
    return grade_task("logic_bug_detection", kwargs.get("answer", args[0] if args else ""))

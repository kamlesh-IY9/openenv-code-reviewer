from graders import grade_task_answer

def grade(*args, **kwargs):
    return grade_task_answer("syntax_check", kwargs.get("answer", args[0] if args else ""))

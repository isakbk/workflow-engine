
import time


class UnknownExecutor(ValueError):
    pass


EXECUTORS = {}


def register(name):
    def decorator(func):
        if name in EXECUTORS:
            raise ValueError(f"Executor '{name}' is already registered.")

        EXECUTORS[name] = func
        return func

    return decorator


def get_executor(name):
    if name not in EXECUTORS:
        raise UnknownExecutor(f"Unknown executor: {name}")

    return EXECUTORS[name]


# 1. Echo Executor
@register("echo")
def echo(task_run, sleep=time.sleep):
    return {"echo": task_run.name}


# 2. Sleep Executor
@register("sleep")
def sleep_executor(task_run, sleep=time.sleep):
    sleep(1)
    return {"slept": 1}


# 3. Fail Executor
@register("fail")
def fail(task_run, sleep=time.sleep):
    raise RuntimeError("Task failed on purpose.")


# 4. Flaky Executor
@register("flaky")
def flaky(task_run, sleep=time.sleep):
    if task_run.attempt < 3:
        raise RuntimeError("Flaky failure.")

    return {"flaky": "ok"}

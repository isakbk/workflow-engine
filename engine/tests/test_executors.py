import pytest

from engine.executors import EXECUTORS, UnknownExecutor, get_executor, register
from engine.models import TaskRun


@pytest.fixture
def clean_registry():
    snapshot = dict(EXECUTORS)
    yield
    EXECUTORS.clear()
    EXECUTORS.update(snapshot)


def no_sleep(seconds):
    return None


def make_task_run(name="extract", attempt=1):
    return TaskRun(name=name, fn="echo", attempt=attempt)


# ---------- registry ----------

def test_builtin_executors_are_registered():
    for name in ("echo", "sleep", "fail", "flaky"):
        assert name in EXECUTORS
        assert callable(get_executor(name))


def test_get_executor_unknown_raises():
    assert issubclass(UnknownExecutor, ValueError)
    with pytest.raises(UnknownExecutor) as error:
        get_executor("nope")
    assert str(error.value) == "Unknown executor: nope"


def test_register_adds_executor_and_returns_function(clean_registry):
    @register("t13_custom")
    def custom(task_run, sleep=None):
        return {"ok": True}

    assert get_executor("t13_custom") is custom
    assert custom(None) == {"ok": True}


def test_register_duplicate_name_is_rejected(clean_registry):
    @register("t13_dup")
    def first(task_run, sleep=None):
        return 1

    with pytest.raises(ValueError) as error:
        @register("t13_dup")
        def second(task_run, sleep=None):
            return 2

    assert str(error.value) == "Executor 't13_dup' is already registered."
    assert get_executor("t13_dup") is first


def test_registering_a_builtin_name_again_is_rejected(clean_registry):
    original = get_executor("echo")
    with pytest.raises(ValueError):
        register("echo")(lambda task_run, sleep=None: None)
    assert get_executor("echo") is original


# ---------- built-in executors ----------

def test_echo_returns_task_name():
    executor = get_executor("echo")
    assert executor(make_task_run("extract"), sleep=no_sleep) == {"echo": "extract"}
    assert executor(make_task_run("load")) == {"echo": "load"}


def test_sleep_calls_injected_sleep_once():
    calls = []
    result = get_executor("sleep")(make_task_run("nap"), sleep=calls.append)
    assert calls == [1]
    assert result == {"slept": 1}


def test_fail_always_raises():
    with pytest.raises(RuntimeError) as error:
        get_executor("fail")(make_task_run(), sleep=no_sleep)
    assert str(error.value) == "Task failed on purpose."


@pytest.mark.parametrize("attempt", [1, 2])
def test_flaky_fails_on_early_attempts(attempt):
    with pytest.raises(RuntimeError) as error:
        get_executor("flaky")(make_task_run(attempt=attempt), sleep=no_sleep)
    assert str(error.value) == "Flaky failure."


@pytest.mark.parametrize("attempt", [3, 4])
def test_flaky_succeeds_from_third_attempt(attempt):
    result = get_executor("flaky")(make_task_run(attempt=attempt), sleep=no_sleep)
    assert result == {"flaky": "ok"}
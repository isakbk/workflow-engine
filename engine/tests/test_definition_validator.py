import copy

from engine.definition import validate_definition


def task(name, **extra):
    data = {"name": name, "fn": "echo"}
    data.update(extra)
    return data


def definition(*tasks):
    return {"tasks": list(tasks)}


def mentions(errors, word):
    return any(word in error for error in errors)


def test_minimal_definition_is_valid():
    assert validate_definition(definition(task("a"))) == []


def test_full_definition_is_valid():
    full = definition(
        task("extract", max_attempts=5, timeout_seconds=30),
        task("clean", depends_on=["extract"]),
        task("stats", depends_on=["extract"]),
        task("report", depends_on=["clean", "stats"], max_attempts=1, timeout_seconds=100),
    )
    assert validate_definition(full) == []


def test_empty_task_list_is_valid():
    assert validate_definition({"tasks": []}) == []


def test_definition_must_be_an_object():
    for bad in [None, [], "text", 5, ["tasks"]]:
        assert validate_definition(bad) != []


def test_tasks_key_is_required():
    for bad in [{}, {"jobs": []}]:
        assert mentions(validate_definition(bad), "tasks")


def test_tasks_must_be_a_list():
    for bad in ["abc", {}, None, 5]:
        assert mentions(validate_definition({"tasks": bad}), "tasks")


def test_each_task_must_be_an_object():
    for bad in ["a", 5, None, ["a"]]:
        assert validate_definition({"tasks": [bad]}) != []


def test_name_must_be_a_non_empty_string_up_to_100_chars():
    bad_tasks = [
        {"fn": "echo"},
        {"name": "", "fn": "echo"},
        {"name": 5, "fn": "echo"},
        {"name": "x" * 101, "fn": "echo"},
    ]
    for bad in bad_tasks:
        assert mentions(validate_definition({"tasks": [bad]}), "name")
    assert validate_definition(definition(task("x" * 100))) == []


def test_fn_must_be_a_non_empty_string_up_to_100_chars():
    bad_tasks = [
        {"name": "a"},
        {"name": "a", "fn": ""},
        {"name": "a", "fn": 5},
        {"name": "a", "fn": "f" * 101},
    ]
    for bad in bad_tasks:
        assert mentions(validate_definition({"tasks": [bad]}), "fn")
    assert validate_definition({"tasks": [{"name": "a", "fn": "f" * 100}]}) == []


def test_depends_on_must_be_a_list_of_strings():
    for bad in ["a", {"x": 1}, [1], [None], None]:
        errors = validate_definition(definition(task("a"), task("b", depends_on=bad)))
        assert mentions(errors, "depends_on")


def test_max_attempts_and_timeout_must_be_positive_integers():
    for field in ["max_attempts", "timeout_seconds"]:
        for bad in [0, -1, "3", 1.5, True, None]:
            errors = validate_definition(definition(task("a", **{field: bad})))
            assert mentions(errors, field)


def test_unknown_task_keys_are_rejected():
    errors = validate_definition(definition(task("a", color="red")))
    assert mentions(errors, "color")


def test_duplicate_task_names_are_reported():
    errors = validate_definition(definition(task("dup"), task("dup")))
    assert len(errors) == 1
    assert mentions(errors, "dup")


def test_unknown_dependency_is_reported():
    errors = validate_definition(definition(task("a", depends_on=["ghost"])))
    assert len(errors) == 1
    assert mentions(errors, "ghost")


def test_dependency_may_point_to_a_task_listed_later():
    assert validate_definition(definition(task("a", depends_on=["b"]), task("b"))) == []


def test_every_problem_is_reported_once():
    broken = definition(task("a", depends_on=["ghost"]), {"name": "b"})
    errors = validate_definition(broken)
    assert len(errors) == 2
    assert mentions(errors, "ghost")
    assert mentions(errors, "fn")


def test_cycles_are_not_checked_here():
    loop = definition(task("a", depends_on=["b"]), task("b", depends_on=["a"]))
    selfish = definition(task("a", depends_on=["a"]))
    assert validate_definition(loop) == []
    assert validate_definition(selfish) == []


def test_input_is_not_modified():
    data = definition(task("a"), task("b", depends_on=["a"]))
    snapshot = copy.deepcopy(data)
    validate_definition(data)
    assert data == snapshot


def test_errors_are_strings():
    errors = validate_definition(definition({"name": 5}, "bad"))
    assert errors
    assert all(isinstance(error, str) for error in errors)
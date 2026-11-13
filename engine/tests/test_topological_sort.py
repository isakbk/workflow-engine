import copy

import pytest

from engine.graph import CycleError, topological_sort


def is_valid_cycle(graph, path):
    if not isinstance(path, list) or len(path) < 2 or path[0] != path[-1]:
        return False
    return all(nxt in graph.get(current, []) for current, nxt in zip(path, path[1:]))


def test_empty_and_single_task_graphs():
    assert topological_sort({}) == []
    assert topological_sort({"a": []}) == ["a"]


def test_chain_is_ordered_by_dependency():
    graph = {"c": ["b"], "b": ["a"], "a": []}
    assert topological_sort(graph) == ["a", "b", "c"]


def test_diamond_order():
    graph = {
        "report": ["clean", "stats"],
        "stats": ["extract"],
        "clean": ["extract"],
        "extract": [],
    }
    assert topological_sort(graph) == ["extract", "clean", "stats", "report"]


def test_independent_tasks_are_sorted_by_name():
    assert topological_sort({"c": [], "a": [], "b": []}) == ["a", "b", "c"]


def test_smallest_ready_task_goes_first():
    assert topological_sort({"b": [], "a": ["b"], "c": []}) == ["b", "a", "c"]
    assert topological_sort({"z": [], "y": ["z"], "a": []}) == ["a", "z", "y"]


def test_dependencies_always_come_before_dependents():
    graph = {
        "a": [],
        "b": ["a"],
        "c": ["a"],
        "d": ["b", "c"],
        "e": ["d", "a"],
        "f": [],
        "g": ["f", "e"],
    }
    order = topological_sort(graph)
    assert sorted(order) == sorted(graph)
    assert len(order) == len(set(order))
    for name, dependencies in graph.items():
        for dependency in dependencies:
            assert order.index(dependency) < order.index(name)


def test_result_does_not_depend_on_insertion_order():
    first = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}
    second = dict(reversed(list(first.items())))
    assert topological_sort(first) == topological_sort(second) == ["a", "b", "c", "d"]


def test_unknown_dependency_names_are_ignored():
    order = topological_sort({"a": ["ghost"], "b": ["a"]})
    assert order == ["a", "b"]
    assert "ghost" not in order


def test_cycle_raises_cycle_error_with_path():
    graph = {"a": ["b"], "b": ["a"]}
    with pytest.raises(CycleError) as info:
        topological_sort(graph)
    assert is_valid_cycle(graph, info.value.path)
    assert set(info.value.path) == {"a", "b"}


def test_self_dependency_raises_cycle_error():
    with pytest.raises(CycleError) as info:
        topological_sort({"a": ["a"]})
    assert info.value.path == ["a", "a"]


def test_cycle_next_to_healthy_tasks_still_raises():
    graph = {"ok": [], "x": ["y"], "y": ["x"]}
    with pytest.raises(CycleError) as info:
        topological_sort(graph)
    assert set(info.value.path) == {"x", "y"}


def test_cycle_error_is_a_value_error():
    assert issubclass(CycleError, ValueError)


def test_very_long_chain_does_not_crash():
    size = 5000
    graph = {str(i): ([str(i - 1)] if i else []) for i in range(size)}
    assert topological_sort(graph) == [str(i) for i in range(size)]


def test_many_independent_tasks():
    graph = {str(i): [] for i in range(3000)}
    assert topological_sort(graph) == sorted(graph)


def test_input_is_not_modified():
    graph = {"a": [], "b": ["a"], "c": ["a", "b"]}
    snapshot = copy.deepcopy(graph)
    topological_sort(graph)
    assert graph == snapshot


def test_result_is_a_list_of_names():
    order = topological_sort({"a": [], "b": ["a"]})
    assert isinstance(order, list)
    assert all(isinstance(name, str) for name in order)
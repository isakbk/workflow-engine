import copy

from engine.graph import find_cycle


def is_valid_cycle(graph, path):
    if not isinstance(path, list) or len(path) < 2 or path[0] != path[-1]:
        return False
    return all(nxt in graph.get(current, []) for current, nxt in zip(path, path[1:]))


def test_graph_without_dependencies_has_no_cycle():
    assert find_cycle({}) is None
    assert find_cycle({"a": []}) is None
    assert find_cycle({"a": [], "b": [], "c": []}) is None


def test_chain_has_no_cycle():
    assert find_cycle({"a": [], "b": ["a"], "c": ["b"]}) is None


def test_diamond_has_no_cycle():
    graph = {
        "extract": [],
        "clean": ["extract"],
        "stats": ["extract"],
        "report": ["clean", "stats"],
    }
    assert find_cycle(graph) is None


def test_self_dependency_is_a_cycle():
    assert find_cycle({"a": ["a"]}) == ["a", "a"]


def test_two_task_cycle_is_found():
    graph = {"a": ["b"], "b": ["a"]}
    path = find_cycle(graph)
    assert is_valid_cycle(graph, path)
    assert set(path) == {"a", "b"}
    assert len(path) == 3


def test_three_task_cycle_is_found():
    graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
    path = find_cycle(graph)
    assert is_valid_cycle(graph, path)
    assert set(path) == {"a", "b", "c"}
    assert len(path) == 4


def test_cycle_path_contains_only_cycle_members():
    graph = {"start": [], "a": ["start", "b"], "b": ["c"], "c": ["a"], "end": ["c"]}
    path = find_cycle(graph)
    assert is_valid_cycle(graph, path)
    assert set(path) == {"a", "b", "c"}


def test_cycle_is_found_next_to_a_healthy_component():
    graph = {"ok1": [], "ok2": ["ok1"], "x": ["y"], "y": ["x"]}
    path = find_cycle(graph)
    assert is_valid_cycle(graph, path)
    assert set(path) == {"x", "y"}


def test_unknown_dependency_names_are_ignored():
    assert find_cycle({"a": ["ghost"]}) is None
    graph = {"a": ["ghost", "b"], "b": ["a"]}
    path = find_cycle(graph)
    assert is_valid_cycle(graph, path)
    assert set(path) == {"a", "b"}


def test_very_long_chain_does_not_crash():
    size = 5000
    graph = {str(i): ([str(i - 1)] if i else []) for i in range(size)}
    assert find_cycle(graph) is None


def test_very_long_cycle_is_found():
    size = 5000
    graph = {str(i): [str((i + 1) % size)] for i in range(size)}
    path = find_cycle(graph)
    assert is_valid_cycle(graph, path)
    assert len(path) == size + 1


def test_input_is_not_modified():
    graph = {"a": ["b"], "b": ["a"], "c": []}
    snapshot = copy.deepcopy(graph)
    find_cycle(graph)
    assert graph == snapshot


def test_cycle_is_a_list_of_names():
    path = find_cycle({"a": ["b"], "b": ["a"]})
    assert isinstance(path, list)
    assert all(isinstance(name, str) for name in path)
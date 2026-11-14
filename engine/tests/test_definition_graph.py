import copy

from engine.definition import build_graph


def test_build_graph_maps_each_task_to_its_dependencies():
    definition = {
        "tasks": [
            {"name": "extract", "fn": "echo"},
            {"name": "clean", "fn": "echo", "depends_on": ["extract"]},
            {"name": "report", "fn": "echo", "depends_on": ["clean", "extract"]},
        ]
    }
    assert build_graph(definition) == {
        "extract": [],
        "clean": ["extract"],
        "report": ["clean", "extract"],
    }


def test_build_graph_of_empty_task_list_is_empty():
    assert build_graph({"tasks": []}) == {}


def test_build_graph_returns_independent_copies():
    definition = {
        "tasks": [
            {"name": "a", "fn": "echo"},
            {"name": "b", "fn": "echo", "depends_on": ["a"]},
        ]
    }
    snapshot = copy.deepcopy(definition)
    graph = build_graph(definition)
    graph["b"].append("zzz")
    graph["new"] = []
    assert definition == snapshot
import heapq

def find_cycle(graph):

    # Step 1: Original graph को copy बनाउने
    replica = {}

    for key, value in graph.items():
        replica[key] = value.copy()

    # Step 2: Unknown dependencies हटाउने
    for key in replica:

        lists = []

        for dependency in replica[key]:

            if dependency in replica:
                lists.append(dependency)

        replica[key] = lists

    # Step 3: Kahn's Algorithm
    while True:

        lists = []

        # Dependency नभएका tasks खोज्ने
        for key, value in replica.items():

            count = len(value)

            if count == 0:
                lists.append(key)

        # Ready task नभए Kahn's Algorithm रोक्ने
        if len(lists) == 0:
            break

        # Ready tasks हटाउने
        for task in lists:
            del replica[task]

        # बाँकी tasks बाट हटाइएको task को dependency हटाउने
        for key in replica:

            for task in lists:

                if task in replica[key]:
                    replica[key].remove(task)

    # Step 4: Leftover graph मा DFS गर्ने

    dicts = {}

    for key in replica:
        dicts[key] = 0

    for start in replica:

        if dicts[start] != 0:
            continue

        path = [start]

        positions = {
            start: 0
        }

        stack = [(start, 0)]

        dicts[start] = 1

        while stack:

            node, count = stack[-1]

            # सबै dependencies जाँच भइसकेको छ कि छैन?
            if count >= len(replica[node]):

                stack.pop()

                dicts[node] = 2

                positions.pop(node)

                path.pop()

                continue

            # एउटा dependency निकाल्ने
            neighbor = replica[node][count]

            # अर्को पटक अर्को dependency जाँच गर्न index बढाउने
            stack[-1] = (node, count + 1)

            # Case 1: नयाँ task भेटियो
            if dicts[neighbor] == 0:

                dicts[neighbor] = 1

                positions[neighbor] = len(path)

                path.append(neighbor)

                stack.append((neighbor, 0))

            # Case 2: पहिले नै Visiting task भेटियो
            elif dicts[neighbor] == 1:

                cycle_start = positions[neighbor]

                return path[cycle_start:] + [neighbor]

    # Cycle भेटिएन
    return None






class CycleError(ValueError):
    def __init__(self, path):
        self.path = path
        super().__init__(f"Cycle detected: {' -> '.join(path)}")


def topological_sort(graph):

    # Step 1: Create in-degree and reverse graph
    in_degree = {name: 0 for name in graph}
    dependents = {name: [] for name in graph}

    # Step 2: Build graph relationships
    for task, dependencies in graph.items():

        for dependency in dependencies:

            # Ignore unknown dependencies
            if dependency not in graph:
                continue

            in_degree[task] += 1
            dependents[dependency].append(task)

    # Step 3: Find all ready tasks
    ready = [
        task
        for task, count in in_degree.items()
        if count == 0
    ]

    # Min Heap: alphabetical order
    heapq.heapify(ready)

    result = []

    # Step 4: Kahn's Algorithm
    while ready:

        # Get smallest alphabetical task
        task = heapq.heappop(ready)

        result.append(task)

        # Step 5: Remove completed task dependencies
        for dependent in dependents[task]:

            in_degree[dependent] -= 1

            if in_degree[dependent] == 0:
                heapq.heappush(ready, dependent)

    # Step 6: Detect cycle using T8 function
    if len(result) != len(graph):

        path = find_cycle(graph)

        raise CycleError(path)

    return result
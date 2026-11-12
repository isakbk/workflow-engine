
def find_cycle(graph):

    # Step 1: Copy graph (original graph modify नगर्ने)
    replica = {
        key: list(value)
        for key, value in graph.items()
    }

    # Step 2: Unknown dependencies ignore गर्ने
    for key in replica:
        replica[key] = [
            dependency
            for dependency in replica[key]
            if dependency in replica
        ]

    # Step 3: Kahn's Algorithm
    while True:

        ready = []

        for key, dependencies in replica.items():
            if not dependencies:
                ready.append(key)

        if not ready:
            break

        for task in ready:
            del replica[task]

        for dependencies in replica.values():
            for task in ready:
                if task in dependencies:
                    dependencies.remove(task)

    # Step 4: Leftover graph मा cycle खोज्ने
    # Iterative DFS (recursion प्रयोग नगर्ने)

    state = {key: 0 for key in replica}

    for start in replica:

        if state[start] != 0:
            continue

        path = [start]
        positions = {start: 0}
        stack = [(start, iter(replica[start]))]
        state[start] = 1

        while stack:

            node, neighbors = stack[-1]

            try:
                neighbor = next(neighbors)

            except StopIteration:
                stack.pop()
                state[node] = 2
                positions.pop(node)
                path.pop()
                continue

            if state[neighbor] == 0:

                state[neighbor] = 1
                positions[neighbor] = len(path)
                path.append(neighbor)

                stack.append(
                    (neighbor, iter(replica[neighbor]))
                )

            elif state[neighbor] == 1:

                cycle_start = positions[neighbor]

                return path[cycle_start:] + [neighbor]

    return None

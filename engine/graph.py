
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

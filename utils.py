def find_closest_cup(lst, target, tolerance=50):
    min_diff = float('inf')
    closest_cup = -1
    for i, freq in enumerate(lst):
        if freq == 0:
            continue
        diff = abs(freq - target)
        if diff < min_diff and diff <= tolerance:
            min_diff = diff
            closest_cup = i
    return closest_cup
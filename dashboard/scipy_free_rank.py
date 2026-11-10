"""Minimal average-rank helper (no scipy dependency), matching the dashboard's
tie rule: ascending ranks, tied values share their mean rank (1-based)."""
import numpy as np


def average_ranks(arr):
    arr = np.asarray(arr, dtype=float)
    n = len(arr)
    order = arr.argsort(kind="mergesort")
    ranks = np.empty(n, dtype=float)
    sorted_vals = arr[order]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks

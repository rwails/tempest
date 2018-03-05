#!/usr/bin/env python3

"""
array_fn: index -> value
key_fn: value -> compare
"""
def boundary_search(array_fn, key_fn, idx_metric_fn, idx_mid_fn,
                    idx_start, idx_end, delta):

    new_search = lambda x, y: boundary_search(array_fn, key_fn, idx_metric_fn,
                                              idx_mid_fn, x, y, delta)

    if key_fn(array_fn(idx_start)) == key_fn(array_fn(idx_end)):
        return [(None, None)]
    if (idx_metric_fn(idx_start, idx_end) <= delta):
        return [(idx_start, idx_end)]
    else:
        mid = idx_mid_fn(idx_start, idx_end)
        if key_fn(array_fn(idx_start)) == key_fn(array_fn(mid)):
            return new_search(mid, idx_end)
        elif key_fn(array_fn(mid)) == key_fn(array_fn(idx_end)):
            return new_search(idx_start, mid)
        else:
            return (new_search(idx_start, mid) + new_search(mid, idx_end))

#!/usr/bin/env python3

import bisect
import random

def make_key_list_and_cumulative_probs(key_to_prob):
    key_list = sorted(key_to_prob.keys())

    if key_list == []:
        return []

    cumulative_probs = [key_to_prob[key_list[0]]]

    for key in key_list[1:]:
        prob = cumulative_probs[-1] + key_to_prob[key]
        cumulative_probs.append(prob)

    return key_list, cumulative_probs

def select_key_from_cumulative_probs(key_list, cumulative_probs):
    result_idx = bisect.bisect_right(cumulative_probs, random.random())
    if (result_idx == len(cumulative_probs)): # Handle unlikely rounding errors
        result_idx -= 1
    return key_list[result_idx]

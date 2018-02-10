#!/usr/bin/env python3
"""
Functions to analyze the entropy of a client-specific guard selection
distribution.
"""

import numpy

def make_prob_matrix(client_asns, guard_fps, client_guard_selection_probs):
    """
    Returns a numpy matrix where every client AS corresponds to a row, every
    guard fingerprint corresponds to a column, and each cell contains the
    probability of client AS x choosing guard y.

    Clients and guards are placed into the matrix in the order determined by
    client_asns and guard_fps.
    """

    prob_matrix = numpy.zeros(shape=(len(client_asns), len(guard_fps)))

    for idx in range(0, len(client_asns)):
        for jdx in range(0, len(guard_fps)):
            client_asn = client_asns[idx]
            guard_fp = guard_fps[jdx]
            prob_matrix[idx][jdx] =\
                client_guard_selection_probs[client_asn][guard_fp]

    return prob_matrix

def score_clients_by_certainty(prob_matrix, client_asns, k, start_row, end_row):
    """
    Ranks rows in the probability matrix (clients) by calculating
    Kullback–Leibler divergence to all other rows.  Scores rows by smallest
    divergence and by kth smallest divergence.  Since this calculation is
    pairwise, it can take a long time to compute.  Use start_row and end_row to
    parallelize.
    """
    num_client_asns, num_guards = prob_matrix.shape
    log_prob_matrix = numpy.zeros(shape=(num_client_asns, num_guards))

    for idx in range(0, num_client_asns):
        log_prob_matrix[idx] = numpy.log2(prob_matrix[idx])

    certainty_scores = []

    filter_zero_prob = numpy.vectorize(lambda x: 0. if (x == -numpy.inf or
                                                        numpy.isnan(x)) else x)

    for idx in range(start_row, end_row):
        certainty = numpy.ones(num_client_asns) * numpy.inf

        for jdx in range(0, num_client_asns):
            if (idx != jdx):
                log_row_diff = filter_zero_prob(log_prob_matrix[idx] -
                                                log_prob_matrix[jdx])
                certainty[jdx] = numpy.dot(prob_matrix[idx], log_row_diff)

        sorted_certainty = numpy.sort(certainty)

        client_asn = client_asns[idx]

        certainty_scores.append((client_asn, sorted_certainty[0],
                                 sorted_certainty[k - 1]))

    return certainty_scores

def score_clients_by_dissim(prob_matrix):
    """
    Ranks rows in the probability matrix (clients) by calculating total
    variation distance to all other rows.  Returns a list of (row index, score)
    tuples, where score := sum over all total variation distances.  Higher
    scores are 'worse'.
    """
    num_client_asns, num_guards = prob_matrix.shape
    dissim_scores = []

    for idx in range(0, num_client_asns):
        acc = 0.0
        row = prob_matrix[idx]
        for jdx in range(0, num_guards):
            acc += numpy.sum(numpy.abs(numpy.subtract(prob_matrix[:,jdx],
                                                      row[jdx])))

        dissim_scores.append((idx, acc))

    return dissim_scores

def score_clients_by_entropy(prob_matrix):
    """
    Ranks rows in the probability matrix (clients) by computing the dot product
    of the row with the entropy of each (normalized) column.  These scores
    are the expected entropy of the adversary's posterior distribution after a
    single guard selection.  Lower scores are 'worse'.
    Returns:
        A list of (row index, score) tuples.
    """
    num_client_asns, num_guards = prob_matrix.shape
    entropy_scores = []

    column_entropies = numpy.zeros(num_guards)
    entropy_f = numpy.vectorize(lambda x: x * numpy.log2(x) if x > 0. else 0.)

    for jdx in range(0, num_guards):
        column_sum = numpy.sum(prob_matrix[:, jdx])
        if (column_sum == 0.):
            column_entropies[jdx] = 0.
        else:
            column_entropies[jdx] =\
                    (-1 * numpy.sum(entropy_f(numpy.divide(prob_matrix[:, jdx],
                                                           column_sum))))

    for idx in range(0, num_client_asns):
        entropy_scores.append((idx, numpy.dot(prob_matrix[idx],
                                              column_entropies)))

    return entropy_scores

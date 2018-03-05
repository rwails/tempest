#!/usr/bin/env python3

import logging
import random
import time

class ExponentialBackoff(object):
    """Use me as a decorator."""
    _max_retries = 30

    def __init__(self, f):
        self._f = f

    def __call__(self, *args):
        c = 0
        while True:
            try:
                ret = self._f(*args)
                return ret
            except Exception as e:
                c += 1
                if c < ExponentialBackoff._max_retries:
                    sleep_time = random.randint(0, 2**c - 1)
                    str = "Error {}.  Retrying in {} seconds..."
                    logging.warn(str.format(e, sleep_time))
                    time.sleep(sleep_time)
                else:
                    raise e

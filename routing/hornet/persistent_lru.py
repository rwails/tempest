#!/usr/bin/env python3

import dbm.gnu
from functools import lru_cache
import logging

import ujson

import serial

class PersistentLRU(object):
    _lru_list_key = b"_lru_list_key"

    def __init__(self, cache_filename, lru_max_size):
        self._cache_filename = cache_filename
        self._cache_db = None
        self._lru_list = []
        self._lru_max_size = lru_max_size

    def _check_integrity(self):
        k = self._cache_db.firstkey()
        while k is not None:
            str_key = k.decode('utf-8')
            if not (k == PersistentLRU._lru_list_key or str_key in
                    self._lru_list):
                logging.error(k, self._lru_list)
                assert(False)
            k = self._cache_db.nextkey(k)

    def _evict(self):
        while(len(self._lru_list) > self._lru_max_size):
            evict_key = self._lru_list.pop()
            logging.info("Evicting {}".format(evict_key))
            del self._cache_db[evict_key.encode('utf-8')]

    def _read_lru_list(self):
        if PersistentLRU._lru_list_key in self._cache_db:
            self._lru_list = ujson.loads(
                self._cache_db[PersistentLRU._lru_list_key].decode('utf-8')
            )

    def _write_lru_list(self):
        self._cache_db[PersistentLRU._lru_list_key] =\
            ujson.dumps(self._lru_list).encode('utf-8')

    def close(self):
        try:
            self._write_lru_list()
            self._cache_db.reorganize()
            self._cache_db.close()
            logging.info("Successfully closed cache")
        except Exception as e:
            warning_str = "Exception \"{}\" on close".format(e)
            logging.warn(warning_str)

    # Key should be str
    def get(self, key):
        return self._cache_db[key.encode('utf-8')]

    def has_key(self, key):
        return key in self._lru_list

    # Key should be str, value should be bytes
    def set(self, key, value):
        if key in self._lru_list:
            self._lru_list.remove(key)
        self._lru_list.insert(0, key)
        self._cache_db[key.encode('utf-8')] = value
        self._evict()

    def load(self):
        self._cache_db = dbm.gnu.open(self._cache_filename, "cs")
        self._read_lru_list()
        self._check_integrity()
        self._evict()

class _Dummy(object):
    def __init__(self, f):
        self._f = f

    def __call__(self, *args):
        return self._f(*args)

def add_persistent_caching(fn, cache_key, key_fn, cache, mem_caching):

    if mem_caching:
        closure_decorator = lru_cache(maxsize=64)
    else:
        closure_decorator = _Dummy

    @closure_decorator
    def func_wrapper(*args):
        key = cache_key + "-" + key_fn(*args)

        if not cache.has_key(key):
            value = fn(*args)
            logging.debug("Writing {} into cache".format(key))
            cache.set(key, serial.obj_to_bytes(value))

        logging.debug("Fetching {} from cache".format(key))
        return serial.obj_from_bytes(cache.get(key))

    return func_wrapper

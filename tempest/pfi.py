#!/usr/bin/env python3

import ctypes
import io
import logging
import os
import struct

class PFI(object):
    def __init__(self, libspookyhash_path, path_filename, index_filename):
        self._libhash_path = libspookyhash_path
        self._path_filename = path_filename
        self._index_filename = index_filename

        self._libhash = None
        self._path_file = None
        self._index_file = None

        self._header_size = 0
        self._num_bins = 0
        self._bytes_per_bin = 0

    def _bin_contents(self):
        buf = bytearray(8)
        buf[0:self._bytes_per_bin] = self._index_file.read(self._bytes_per_bin)
        self._index_file.seek(-1 * self._bytes_per_bin, io.SEEK_CUR)
        return struct.unpack("<q", buf)[0]

    def _bin_index(self, hash, i):
        return (hash + (i * i)) % self._num_bins

    def _bin_is_blank(self):
        data = self._index_file.read(self._bytes_per_bin)
        self._index_file.seek(-1 * self._bytes_per_bin, io.SEEK_CUR)
        return data[-1] == 255

    def _read_header_meta(self):
        self._header_size = struct.unpack("<q", self._index_file.read(8))[0]
        self._num_bins = struct.unpack("<q", self._index_file.read(8))[0]
        self._bytes_per_bin = struct.unpack("<q", self._index_file.read(8))[0]

    def _seek_to_bin(self, bin):
        offset = self._header_size + (bin * self._bytes_per_bin)
        self._index_file.seek(offset, io.SEEK_SET)

    def close(self):
        try:
            self._index_file.close()
            self._path_file.close()
        except:
            pass

    def get_path(self, src, dst):
        if (src == dst): return [src]
        key = src.encode("ascii") + b" " + dst.encode("ascii")
        hash_value = self._libhash.hash_string(key)
        i = 0
        bin = self._bin_index(hash_value, i)
        self._seek_to_bin(bin)

        while not self._bin_is_blank():
            # See if we have the correct result...
            path_file_offset = self._bin_contents()
            self._path_file.seek(path_file_offset, io.SEEK_SET)
            line =\
                self._path_file.readline().strip().decode("ascii").split(" ")
            if (line[0] == src and line[-1] == dst):
                return line
            else:
                i += 1
                bin = self._bin_index(hash_value, i)
                self._seek_to_bin(bin)

        return None

    def verify(self):
        assert(self._libhash.hash_string(b"qwerty12345") ==
               9134894412101018003)

        real_index_file_sz = os.path.getsize(self._index_filename)
        calc_index_file_sz = (self._header_size + self._bytes_per_bin *
                              self._num_bins)

        assert(real_index_file_sz == calc_index_file_sz)
        logging.info("Passed all PFI integrity checks.")
        return True

    def load(self):
        self._libhash = ctypes.cdll.LoadLibrary(self._libhash_path)
        self._libhash.hash_string.argtypes = [ctypes.c_char_p]
        self._libhash.hash_string.restype = ctypes.c_ulonglong
        self._index_file = open(self._index_filename, "rb", buffering=-1)
        self._read_header_meta()
        self._path_file = open(self._path_filename, "rb", buffering=-1)

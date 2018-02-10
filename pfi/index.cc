#define _POSIX_C_SOURCE 200809L

// Standard C
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// Standard C++
#include <iostream>
#include <random>

// POSIX
#include <unistd.h>

// External
#include <gmp.h>

std::uint64_t file_num_lines(const char *filename) {
   std::uint64_t number_of_lines = 0;
   char *line = nullptr;
   std::size_t n = 0;
   ssize_t read = 0;
   auto file = std::fopen(filename, "r");

   while ((read = getline(&line, &n, file)) != -1) {
      ++number_of_lines;
   }

   if (line != nullptr) { std::free(line); line = nullptr; }
   if (file != nullptr) { std::fclose(file); file = nullptr; }

   return number_of_lines;
}

std::uint64_t file_num_bytes(const char *filename) {
   auto f = std::fopen(filename, "rb");
   std::fseek(f, 0, SEEK_END);
   auto sz = std::ftell(f);
   std::fclose(f);
   return sz;
}

std::uint64_t num_bins(std::uint64_t num_lines) {
   std::uint64_t target = 2 * num_lines, answer = 0;
   mpz_t x, y;
   mpz_inits(x, y, NULL);

   mpz_set_ui(x, target);
   mpz_nextprime(y, x);
   answer = mpz_get_ui(y);

   mpz_clears(x, y, NULL);
   return answer;
}

std::uint64_t bytes_per_bin(std::uint64_t num_bytes) {
   return static_cast<std::uint64_t>(std::ceil((std::log2(num_bytes) + 1) / 8));
}

struct alignas(8) Meta {
   std::uint64_t header_size = sizeof(Meta);
   std::uint64_t num_bins, bytes_per_bin;
};

std::FILE *create_ff_file(const char *filename, std::size_t num_bytes) {
   std::uint64_t page_size = sysconf(_SC_PAGESIZE);
   unsigned char *buf = new unsigned char[page_size];
   std::memset(buf, 0xFF, page_size);

   auto f = std::fopen(filename, "wb+");

   while (num_bytes > page_size) {
      std::fwrite(buf, 1, page_size, f);
      num_bytes -= page_size;
   }

   std::fwrite(buf, 1, num_bytes, f);
   std::fseek(f, 0, SEEK_SET);

   delete[] buf; buf = nullptr;
   return f;
}

std::uint64_t index_file_size(const Meta &meta) {
   return meta.header_size + (meta.num_bins * meta.bytes_per_bin);
}

/*
 * Ensure file is seeked to slot before calling this function.
 * Will not change the current file offset.
 */
bool bin_is_blank(const Meta &meta, std::FILE *file) {
   char buf[8];
   std::fread(buf, 1, meta.bytes_per_bin, file);
   std::fseek(file, -1 * meta.bytes_per_bin, SEEK_CUR);
   return buf[meta.bytes_per_bin - 1] == -1;
}

void seek_to_bin(const Meta &meta, std::uint64_t bin, std::FILE *file) {
   std::uint64_t offset = meta.header_size + (bin * meta.bytes_per_bin);
   std::fseek(file, offset, SEEK_SET);
}

std::uint64_t bin_idx(std::uint64_t hash, const Meta &meta, unsigned i) {
   return (hash + (i * i)) % meta.num_bins;
}

void index_insert(std::uint64_t hash, std::uint64_t offset, const Meta &meta,
                  std::FILE *file)
{
   std::uint64_t bin = bin_idx(hash, meta, 0);
   seek_to_bin(meta, bin, file);

   unsigned i = 1;
   while (!bin_is_blank(meta, file)) {
      bin = bin_idx(hash, meta, i++);
      seek_to_bin(meta, bin, file);
   }

   std::fwrite(&offset, 1, meta.bytes_per_bin, file);
}

extern "C" std::uint64_t hash_string(const char *str);

int main(int argc, char **argv) {
   if (argc < 3) {
      std::cerr << "Useage: " << argv[0] << " <path_filename> <index_filename>"
         << std::endl;
      return -1;
   }

   const char *path_filename = argv[1];
   const char *index_filename = argv[2];

   auto path_file_num_lines = file_num_lines(path_filename);
   auto path_file_num_bytes = file_num_bytes(path_filename);

   Meta header;
   header.num_bins = num_bins(path_file_num_lines);
   header.bytes_per_bin = bytes_per_bin(path_file_num_bytes);

   std::cerr << "Path file lines:\t" << path_file_num_lines << std::endl;
   std::cerr << "Path file bytes:\t" << path_file_num_bytes << std::endl;
   std::cerr << "Num bins:\t" << header.num_bins << std::endl;
   std::cerr << "Bytes per bin:\t" << header.bytes_per_bin << std::endl;
   std::cerr << "Path file:\t" << path_filename << std::endl;
   std::cerr << "Index file:\t" << index_filename << std::endl;

   auto f = create_ff_file(index_filename, index_file_size(header));
   std::fwrite(&header, sizeof(Meta), 1, f);

   auto path_file = std::fopen(path_filename, "r");
   char *line = nullptr;
   std::size_t n = 0;
   ssize_t read = 0;

   std::uint64_t i = 0;
   std::uint64_t offset = std::ftell(path_file);

   char key[4096];
   std::memset(key, 0, 4096);

   while ((read = getline(&line, &n, path_file)) != -1) {
      if (i++ % 100000 == 0) {
         std::cerr << "Indexed " << i << " lines." << std::endl;
      }

      if (std::strchr(line, ' ') == nullptr) {
         std::cerr << "WARNING:\tSkipping line " << line << std::endl;
         offset = std::ftell(path_file);
         continue;
      }

      auto src_len = static_cast<std::size_t>(std::strchr(line, ' ') - line);
      std::strncpy(key, line, src_len);

      auto dst_start = std::strrchr(line, ' ');
      dst_start[std::strlen(dst_start) - 1] = '\0';
      std::strcpy(key + src_len, dst_start);

      auto hash = hash_string(key);
      index_insert(hash, offset, header, f);

      offset = std::ftell(path_file);
   }

   std::cerr << "Job complete." << std::endl;
   std::cerr << "Indexed " << i << " lines in total." << std::endl;

   if (line != nullptr) { std::free(line); line = nullptr; }
   if (path_file != nullptr) { std::fclose(path_file); path_file = nullptr; }
   if (f != nullptr) { std::fclose(f); f = nullptr; }

   return 0;
}

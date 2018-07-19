#define _POSIX_C_SOURCE 200112L

#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif // __APPLE__

#include <cassert>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <iostream>
#include <memory>

#include <tbb/tbb.h>

#include "routing_tree.h"

using namespace bgpsim;

#define BUF_SZ 256

void print_path(const Path &path) {

// #define REVERSE_PATHS

#ifdef REVERSE_PATHS
   auto end_itr = path.cend() - 1;
   for (auto itr = path.cbegin(); itr < end_itr; ++itr) {
      std::printf("%s ", itr->c_str());
   }
#else
   auto end_itr = path.crend() - 1;
   for (auto itr = path.crbegin(); itr < end_itr; ++itr) {
      std::printf("%s ", itr->c_str());
   }
#endif // REVERSE_PATHS

   std::printf("%s\n", end_itr->c_str());
}

void path_to_str(const Path& path,
                 std::size_t max_len [[ gnu::unused ]],
                 char *out)
{
   std::size_t len = 0;

   auto add_hop_str = [&] (const char *hop_str, const char *format,
                           std::size_t num_extra) -> void
   {
      len += std::strlen(hop_str) + num_extra;
      assert(len < max_len);
      std::sprintf(out, format, hop_str);
      out += std::strlen(hop_str) + num_extra;
   };

   auto end_itr = path.crend() - 1;

   for (auto itr = path.crbegin(); itr < end_itr; ++itr) {
      add_hop_str(itr->c_str(), "%s ", 1);
   }

   add_hop_str(end_itr->c_str(), "%s", 0);
}

using PathStrBuffer = char [BUF_SZ];

std::shared_ptr<PathStrBuffer>
prepare_path_strs(const IndexedPaths &indexed_paths, std::size_t *num_paths)
{
   *num_paths = indexed_paths.size();

   std::shared_ptr<PathStrBuffer> path_strs
      (
         new PathStrBuffer[*num_paths],
         std::default_delete<PathStrBuffer[]>()
      );

   std::size_t idx = 0;
   for (auto &value : indexed_paths) {
      path_to_str(value.second, BUF_SZ, path_strs.get()[idx]);
      ++idx;
   }

   return path_strs;
}

int main(int argc, char **argv) {

   if (argc != 3) {
      std::fprintf(stderr, "Usage: %s <asrel_filename> <num_threads>\n",
                   argv[0]);
      return -1;
   }

   const char *asrel_filename = argv[1];
   std::size_t num_threads = std::stoi(argv[2]);

   AdjList adj_list;
   add_relationships_to_adj_list(asrel_filename, &adj_list);

   std::vector<ASNumber> asns;

   for (auto &asn_adjlist_pair : adj_list) {
      asns.push_back(asn_adjlist_pair.first);
   }

   std::sort(asns.begin(), asns.end());

   IndexedPathsTo indexed_paths_to;

   compute_all_vanilla_paths(asns, adj_list, &indexed_paths_to, num_threads);

   tbb::mutex mtx;

   auto mt_print_path = [&] (const IndexedPathsTo::value_type &value) -> void
   {
      std::size_t num_paths = 0;
      auto path_strs = prepare_path_strs(value.second, &num_paths);

      mtx.lock();
      for (std::size_t idx = 0; idx < num_paths; ++idx) {
         auto *str = path_strs.get()[idx];
         if (std::strchr(str, ' ') != nullptr) {
            std::printf("%s\n", str);
         }
      }
      mtx.unlock();
   };

   tbb::parallel_for_each(indexed_paths_to.cbegin(), indexed_paths_to.cend(),
                          mt_print_path);

   std::fflush(stdout); std::fflush(stderr);
   std::_Exit(0);
}

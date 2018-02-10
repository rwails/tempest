#ifndef GRAPH_ALGORITHMS_HPP_
#define GRAPH_ALGORITHMS_HPP_
#include <map>
#include <queue>
#include <set>
#include <utility>

#include <tbb/concurrent_unordered_set.h>
#include <tbb/parallel_do.h>

#include <iostream>

namespace nrl {

/**
 * transpose_graph should be an empty, default-constructed graph.
 */
template <typename T>
void generate_transpose_graph(const T& graph, T* transpose_graph)
{
   using Weight = typename T::Weight;

   for (auto &u : *graph.vertices()) {
      transpose_graph->add_vertex(u);
   }

   auto add_reverse_edges = [&] (const Weight &k) -> void {
      for (auto &u : *graph.vertices()) {
         auto k_edges = graph.adj_vertices(u, k);
         if (k_edges != nullptr) {
            for (auto &v : *k_edges) {
               // Add the reverse edge with the same cost to the transpose.
               transpose_graph->add_edge(v, u, k);
            } // for v
         } // if
      } // for u
   };

   add_reverse_edges(0);
   add_reverse_edges(1);
}

template <typename T>
typename T::Weight graph_diameter(const T& graph [[ gnu::unused ]]) {
   // TODO (rwails): Implement Floyd-Warshall.  May be too expensive for our
   // large graph to run online.  Stub for now.
   //
   // UPDATE (rwails): Computed Gao-Rexford allpairs inference on CAIDA's
   // 2016-10 asrel2 dataset, longest shortest-path length was 22 for path
   // 10091 -> 264924.  Still a stub function for now.
   return 22;
}

template <typename T>
void zero_nbhd(const T& graph,
               const std::set<typename T::Vertex> &source_vertices,
               std::set<typename T::Vertex> *nbhd)
{
   std::queue<typename T::Vertex> queue;

   for (auto &u : source_vertices) {
      queue.push(u);
   }

   while (!queue.empty()) {
      auto u = queue.front();
      queue.pop();
      nbhd->insert(u);

      auto zero_edges = graph.adj_vertices(u, 0);

      if (zero_edges != nullptr) {
         for (auto &v : *zero_edges) {
            if (nbhd->count(v) == 0) { queue.push(v); }
         } // for
      } // if
   } // while
}

template <typename T>
void zero_nbhd_parallel(const T& graph,
                        const std::set<typename T::Vertex> &source_vertices,
                        std::set<typename T::Vertex> *nbhd)
{
   using Vertex = typename T::Vertex;
   tbb::concurrent_unordered_set<Vertex> s;

   auto nbhd_fn = [&] (const Vertex &u,
                       tbb::parallel_do_feeder<Vertex> &feeder) -> void
   {
      s.insert(u);

      auto zero_edges = graph.adj_vertices(u, 0);
      if (zero_edges != nullptr) {
         for (auto &v : *zero_edges) {
            if (s.count(v) == 0) { feeder.add(v); }
         }
      }
   };

   tbb::parallel_do(source_vertices.cbegin(), source_vertices.cend(), nbhd_fn);

   for (auto &u : s) {
      nbhd->insert(u);
   }
}

template <typename T>
void k_step(const T& graph,
            const std::set<typename T::Vertex> &source_vertices,
            const typename T::Weight &k,
            std::set<typename T::Vertex> *step)
{
   for (auto &u : source_vertices) {
      auto k_edges = graph.adj_vertices(u, k);
      if (k_edges != nullptr) {
         for (auto &v : *k_edges) {
            step->insert(v);
         }
      }
   }
}

} // namespace nrl

#endif // GRAPH_ALGORITHMS_HPP_

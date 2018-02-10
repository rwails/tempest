#ifndef SAMPLE_GRAPHS_HPP_
#define SAMPLE_GRAPHS_HPP_
#include <cstdint>
#include <algorithm>
#include <random>
#include <vector>

namespace nrl {

template <typename T>
void init_big_graph(T *graph) {
   using Vertex = typename T::Vertex;

   std::mt19937 gen(0);
   const std::uint32_t n = 250000;
   std::vector<Vertex> vertices;

   for (std::uint32_t idx = 0; idx < n; ++idx) {
      vertices.push_back(idx);
      graph->add_vertex(idx);
   }

   std::shuffle(vertices.begin(), vertices.end(), gen);
   std::uniform_int_distribution<std::uint32_t> edge_dist(0, 100);
   std::uniform_int_distribution<std::uint16_t> cost_dist(0, 1);
   std::uniform_int_distribution<std::uint32_t> idx_dist(0, n - 1);

   for (std::uint32_t idx = 0; idx < n; ++idx) {
      auto num_edges = edge_dist(gen);
      auto cost = cost_dist(gen);
      // std::rotate(vertices.begin(), vertices.begin() + 101, vertices.end());

      for (std::uint32_t jdx = 0; jdx < num_edges; ++jdx) {
         graph->add_edge(idx, vertices[idx_dist(gen)], cost);
      }
   }
}

template<typename T>
void init_line_graph(T *graph)
{
   using Vertex = typename T::Vertex;
   std::vector<Vertex> vertices{1, 2, 3, 4, 5, 6, 7};

   for (auto &u : vertices) {
      graph->add_vertex(u);
   }

   graph->add_edge(1, 2, 1);
   graph->add_edge(2, 3, 1);
   graph->add_edge(3, 4, 0);
   graph->add_edge(3, 6, 1);
   graph->add_edge(4, 5, 1);
   graph->add_edge(5, 1, 1);
   graph->add_edge(6, 7, 0);
}

template<typename T>
void init_sketch_graph(T *graph)
{
   using Vertex = typename T::Vertex;
   std::vector<Vertex> vertices{1, 2, 3, 4, 5, 6, 7, 8};

   for (auto &u : vertices) {
      graph->add_vertex(u);
   }

   graph->add_edge(1, 2, 0);
   graph->add_edge(1, 8, 1);
   graph->add_edge(2, 3, 0);
   graph->add_edge(2, 5, 1);
   graph->add_edge(3, 4, 0);
   graph->add_edge(3, 5, 1);
   graph->add_edge(4, 5, 1);
   graph->add_edge(5, 1, 1);
   graph->add_edge(5, 6, 0);
   graph->add_edge(6, 7, 1);
   graph->add_edge(7, 4, 1);
   graph->add_edge(8, 1, 0);
}

} // namespace nrl

#endif // SAMPLE_GRAPHS_H_

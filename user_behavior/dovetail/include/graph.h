#ifndef GRAPH_H_
#define GRAPH_H_
#include <cstdint>
#include <map>
#include <memory>
#include <vector>
#include "macro.h"

namespace nrl {

/*
 * Weighted directed graph represented by an adjacency list, each edge has
 * weight exactly 0 or 1.
 */
class BinaryWDGAdj {
public:
   using Vertex = std::uint32_t;
   using VertexContainer = std::vector<Vertex>;
   using Weight = std::int32_t;
   using AdjListContainer = std::vector<Vertex>;
   using AdjList = std::map< Vertex, std::shared_ptr<AdjListContainer> >;
   using Path = std::vector<Vertex>;

   static const Weight k_weight_inf = -1;

   BinaryWDGAdj() = default;

   const VertexContainer *vertices() const;

   /* Add edge u ---> v with weight 0 or 1 */
   void add_edge(const Vertex &u, const Vertex &v, const Weight &w);
   void add_vertex(const Vertex &u);
   const AdjListContainer *adj_vertices(const Vertex &u, const Weight &w) const;

   /* Calling reset will empty the graph and invalidate all current vertex or
    * edge refs. */
   void reset();
   void sort_edge_lists();

   DISALLOW_COPY_AND_ASSIGN(BinaryWDGAdj)
private:
   VertexContainer vertices_;
   AdjList one_edges_, zero_edges_;
};

} // namespace nrl

#endif // GRAPH_H_

#include "graph.h"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <utility>

#include <tbb/parallel_do.h>

namespace nrl {

const BinaryWDGAdj::VertexContainer *BinaryWDGAdj::vertices() const {
   return &vertices_;
}

void BinaryWDGAdj::add_edge(const Vertex &u, const Vertex &v, const Weight &w) {
   assert(w == 0 || w == 1);
   AdjList *adj_list = (w == 0 ? &zero_edges_ : &one_edges_);

   auto itr = adj_list->find(u);
   if (itr == adj_list->end()) {
      auto ret = adj_list->insert(std::make_pair(u,
                                  std::make_shared<AdjListContainer>()));
      itr = ret.first;
   }

   itr->second->push_back(v);
}

void BinaryWDGAdj::add_vertex(const Vertex &u) {
   vertices_.push_back(u);
}

const BinaryWDGAdj::AdjListContainer
*BinaryWDGAdj::adj_vertices(const Vertex &u, const Weight &w) const
{
   assert(w == 0 || w == 1);
   const AdjList *adj_list = (w == 0 ? &zero_edges_ : &one_edges_);

   auto itr = adj_list->find(u);
   if (itr == adj_list->end()) { return nullptr; }
   else {
      return itr->second.get();
   }
}

void BinaryWDGAdj::reset() {
   vertices_.clear();
   zero_edges_.clear();
   one_edges_.clear();
}

void BinaryWDGAdj::sort_edge_lists() {
   auto sort_fn = [&] (AdjList::value_type &value) -> void
   {
      std::sort(value.second->begin(), value.second->end());
   };

   tbb::parallel_do(zero_edges_.begin(), zero_edges_.end(), sort_fn);
   tbb::parallel_do(one_edges_.begin(), one_edges_.end(), sort_fn);
}

} // namespace nrl

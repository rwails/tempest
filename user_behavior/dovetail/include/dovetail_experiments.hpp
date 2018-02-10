#ifndef DOVETAIL_EXPERIMENTS_HPP_
#define DOVETAIL_EXPERIMENTS_HPP_

#include <cstddef>
#include <algorithm>
#include <iterator>
#include <set>
#include <vector>

#include "asrel.h"
#include "common_def.h"
#include "dovetail.hpp"
#include "generic_container_algorithms.hpp"
#include "graph.h"

namespace nrl {

template <typename T, typename URNG>
ASNumber random_dovetail_path_no_tail(const ASRelIR &as_rel_ir,
                                      std::size_t num_matchmakers,
                                      URNG &&g)
{
   using Graph = T;
   Graph graph, transpose_graph;
   DovetailProperties<Graph> properties;

   init_graph_and_properties_from_asrel(as_rel_ir, num_matchmakers, &graph,
                                        &properties, g);

   graph.sort_edge_lists();
   generate_transpose_graph(graph, &transpose_graph);
   transpose_graph.sort_edge_lists();

   auto diameter = graph_diameter(graph);

   typename Graph::Path chosen_path;

   ASNumber source_asn;
   std::vector<ASNumber> endhost_ases;

   std::copy(properties.endhost_ases.cbegin(), properties.endhost_ases.cend(),
             std::back_inserter(endhost_ases));

   source_asn = single_random_sample(endhost_ases.cbegin(),
                                     endhost_ases.cend(), g);

   nrl::create_path_to_random_matchmaker(graph, transpose_graph, diameter,
         source_asn, properties, 20000, diameter * 3, &chosen_path, g);

   if (chosen_path.empty()) {
      return ASNumber{};
   } else {
      ASPath as_path;
      graph_path_to_as_path(chosen_path, properties, &as_path);
      std::size_t as_path_size = as_path.size();
      assert(as_path_size >= 6);

      auto dovetail_idx = as_path_size - 3;

      return as_path[dovetail_idx];
   }

}

template <typename T, typename URNG>
bool multiple_connections_sample_no_tail(const ASRelIR &as_rel_ir,
                                         std::size_t num_matchmakers,
                                         std::size_t max_num_conn,
                                         std::string &adversary_asn,
                                         int sample_num,
                                         URNG &&g)
{
   using Graph = T;
   using Vertex = typename Graph::Vertex;
   using Weight = typename Graph::Weight;

   Graph graph, transpose_graph;
   DovetailProperties<Graph> properties;

   init_graph_and_properties_from_asrel(as_rel_ir, num_matchmakers, &graph,
                                        &properties, g);

   graph.sort_edge_lists();
   generate_transpose_graph(graph, &transpose_graph);
   transpose_graph.sort_edge_lists();

   auto diameter = graph_diameter(graph);

   typename Graph::Path chosen_path;

   ASNumber source_asn;
   ASPath as_path;
   CostMap<Graph> cost_map;

   random_sample(properties.endhost_ases.cbegin(),
                 properties.endhost_ases.cend(), &source_asn, 1, g);

   std::set<ASNumber> possible_ases = properties.endhost_ases;

   for (std::size_t i = 0; i <= max_num_conn; ++i) {
      chosen_path.clear();
      as_path.clear();
      cost_map.clear();

      std::cout << adversary_asn << ',' << sample_num << ',' << i << ','
         << possible_ases.size() << std::endl;

      create_path_to_random_matchmaker(graph, transpose_graph, diameter,
                                       source_asn, properties, 20000,
                                       diameter * 3, &chosen_path, g);

      if (chosen_path.empty()) {
         return false; // Chose source vertex with no general Internet
                       // connectivity.
      } else {
         graph_path_to_as_path(chosen_path, properties, &as_path);
         ASNumber mm_asn = as_path.back();

         std::size_t as_path_size = as_path.size();
         assert(as_path_size >= 6);
         auto dovetail_asn_idx = as_path_size - 3;
         ASNumber dovetail_asn = as_path[dovetail_asn_idx];

         // Ugly, lazy coding style here...
         if (dovetail_asn != adversary_asn) { continue; }

         // Find the first vertex that belongs to the dovetail AS
         auto vertex_owned_by_dovetail = [&] (const Vertex &u) -> bool
         {
            return properties.vertex_owner.at(u) == dovetail_asn;
         };

         auto dovetail_vertex_itr = std::find_if(chosen_path.cbegin(),
                                                 chosen_path.cend(),
                                                 vertex_owned_by_dovetail);

         auto dovetail_asn_itr = std::find(as_path.cbegin(), as_path.cend(),
                                           dovetail_asn);

         Weight cost_to_dovetail = std::distance(as_path.cbegin(),
                                                 dovetail_asn_itr);

         Weight cost_to_prev_hop = cost_to_dovetail - 1;

         Vertex prev_hop_vertex = *(dovetail_vertex_itr - 1);
         Vertex true_source_vertex = chosen_path.front();

         ASNumber true_source_asn =
            properties.vertex_owner.at(true_source_vertex);

         compute_available_costs(transpose_graph, prev_hop_vertex,
                                 cost_to_prev_hop, &cost_map);

         assert(cost_map[cost_to_prev_hop].count(true_source_vertex) > 0);

         std::set<ASNumber> possible_ases_current_conn;
         for (auto &u : cost_map[cost_to_prev_hop]) {
            possible_ases_current_conn.insert(properties.vertex_owner.at(u));
         }

         // We know the source will never choose a MM colocated in the source
         // AS
         auto rm_itr = possible_ases_current_conn.find(mm_asn);
         if (rm_itr != possible_ases_current_conn.end()) {
            possible_ases_current_conn.erase(rm_itr);
         }

         std::set<ASNumber> new_possible_ases;

         std::set_intersection(possible_ases.cbegin(), possible_ases.cend(),
               possible_ases_current_conn.cbegin(),
               possible_ases_current_conn.end(),
               std::inserter(new_possible_ases, new_possible_ases.end()));

         possible_ases = new_possible_ases;

         assert(possible_ases.count(true_source_asn) > 0);
      } // else

   } // for (connections)

   return true;
}

} // namespace nrl

#endif // DOVETAIL_EXPERIMENTS_HPP_

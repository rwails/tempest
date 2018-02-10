#ifndef DOVETAIL_HPP_
#define DOVETAIL_HPP_
#include <cassert>
#include <cmath>
#include <cstddef>
#include <algorithm>
#include <complex>
#include <functional>
#include <iterator>
#include <map>
#include <set>
#include <unordered_map>
#include <vector>

#include <syslog.h>

#include <tbb/concurrent_unordered_map.h>
#include <tbb/concurrent_vector.h>
#include <tbb/parallel_do.h>
#include <tbb/task_group.h>

#include "asrel.h"
#include "common_def.h"
#include "generic_container_algorithms.hpp"
#include "generic_container_ostreams.hpp"
#include "graph_algorithms.hpp"
#include "poly_solver.h"

namespace nrl {

/* Non-template functions */

void find_endhost_ases(const ASRelIR &as_rel_ir,
                       std::set<ASNumber> *endhost_ases);

/* Template functions */

template <typename T>
using CostMap = std::map< typename T::Weight,
                          std::set<typename T::Vertex> >;

template <typename T>
using CostWeights = std::map< typename T::Weight, double >;

template <typename T>
struct DovetailPath
{
   using Path = typename T::Path;
   using Vertex = typename T::Vertex;

   Path source_to_dovetail;
   Vertex dovetail;
   Path dovetail_to_destination;
};

template <typename T>
struct DovetailProperties {
   using Vertex = typename T::Vertex;
   using PropertyMap = std::map<ASNumber, Vertex>;
   using PropertySet = std::set<ASNumber>;

   PropertyMap customer_in;
   PropertyMap customer_out;
   PropertyMap host_in;
   PropertyMap host_out;
   PropertyMap peer_in;
   PropertyMap peer_out;
   PropertyMap provider_in;
   PropertyMap provider_out;

   PropertySet endhost_ases;
   PropertySet loose_vf_ases;
   PropertySet matchmaker_ases;

   std::unordered_map<Vertex, ASNumber> vertex_owner;
};

template <typename T>
void compute_available_costs(const T& graph,
                             const typename T::Vertex &source,
                             const typename T::Weight &max_cost,
                             CostMap<T> *cost_map)
{
   using VertexSet = std::set<typename T::Vertex>;

   auto update_cost_map = [&] (const VertexSet &vertex_set,
                               const typename T::Weight &weight) -> void
   {
      for (auto &u : vertex_set) {
         (*cost_map)[weight].insert(u);
      }
   };

   VertexSet zero, one;
   zero_nbhd_parallel(graph, VertexSet{source}, &zero);
   update_cost_map(zero, 0);

   for (typename T::Weight w = 1; w <= max_cost; ++w) {
      one.clear();
      k_step(graph, zero, 1, &one);
      zero.clear();
      zero_nbhd_parallel(graph, one, &zero);
      update_cost_map(zero, w);
   }
}

template <typename T>
void exp_k_cost_weights(const typename T::Vertex &u,
                        const CostMap<T> &cost_map,
                        const typename T::Weight &min_cost_k,
                        CostWeights<T> *cost_weights)
{
   using Weight = typename T::Weight;

   assert(min_cost_k > 0);

   auto comp = [] (const typename CostMap<T>::value_type &lhs,
                   const typename CostMap<T>::value_type &rhs) -> bool
   {
      return lhs.first < rhs.first;
   };

   auto max_cost = std::max_element(cost_map.cbegin(),
                                    cost_map.cend(), comp)->first;

   std::size_t num_coeff = max_cost + 1;

   double *poly_coeff = new double[num_coeff];
   poly_coeff[0] = -1.0;

   for (Weight wdx = 1; wdx <= max_cost; ++wdx) {
      if (wdx >= min_cost_k && cost_map.at(wdx).count(u) > 0) {
         poly_coeff[wdx] = 1.0;
      } else {
         poly_coeff[wdx] = 0.0;
      }
   }

   double target = 1.0;
   auto end_itr = std::find_end(poly_coeff, poly_coeff + num_coeff, &target,
                                (&target) + 1);

   // gsl doesn't like when the leading term of the polynomial is nonzero
   std::size_t effective_num_coeff = std::distance(poly_coeff, end_itr) + 1;
   double sum = std::accumulate(poly_coeff, poly_coeff + num_coeff, 0);

   if (sum == poly_coeff[0]) {
      syslog(LOG_INFO, "No paths for vertex %u.", u);
   } else {
      std::vector<Complex> roots;
      poly_roots(poly_coeff, effective_num_coeff, &roots);

      auto itr = std::find_if(roots.cbegin(), roots.cend(),
                              [] (const Complex &c) -> bool
                              { return (c.real() > 0.0 && c.imag() == 0.0); });

      assert(itr != roots.cend());
      double real_root = itr->real();

      (*cost_weights)[0] = 0.0;

      for (Weight wdx = 1; wdx <= max_cost; ++wdx) {
         if (poly_coeff[wdx] == 0.0) {
            (*cost_weights)[wdx] = 0.0;
         } else {
            (*cost_weights)[wdx] = std::pow(real_root, wdx);
         }
      } // for
   } // else

   delete[] poly_coeff; poly_coeff = nullptr;
}

template <typename T>
void graph_path_to_as_path(const typename T::Path &graph_path,
                           const DovetailProperties<T> &properties,
                           ASPath *as_path)
{
   for (auto &u : graph_path) {
      ASNumber asn = properties.vertex_owner.at(u);
      if (as_path->empty() || as_path->back() != asn) {
         as_path->push_back(asn);
      } // if
   } // for
}

template <typename T, typename URNG>
void init_graph_and_properties_from_asrel(const ASRelIR &as_rel_ir,
                                          std::size_t num_matchmakers,
                                          T *graph,
                                          DovetailProperties<T> *properties,
                                          URNG &&g)
{
   using Vertex = typename T::Vertex;

   std::set<ASNumber> unique_ases;
   extract_all_unique_ases(as_rel_ir, &unique_ases);

   find_endhost_ases(as_rel_ir, &(properties->endhost_ases));

   random_sample(unique_ases.cbegin(), unique_ases.cend(),
                 std::inserter(properties->matchmaker_ases,
                               properties->matchmaker_ases.end()),
                 num_matchmakers, g);

   // Adding vertices and internal pathlets to graph.
   Vertex ctr{0};

   for (auto &asn : unique_ases) {
      // Use Figure 1 in Dovetail arxiv paper for 'top', 'middle', 'bottom'
      // position references.

      // Helper lambda to reduce code duplication
      auto add_vertex = [&] (const Vertex &u) -> void
      {
         graph->add_vertex(u);
         properties->vertex_owner[u] = asn;
      };

      Vertex top_vertex = ctr++;
      add_vertex(top_vertex);

      Vertex bottom_vertex = ctr++;
      add_vertex(bottom_vertex);

      if (properties->loose_vf_ases.count(asn) > 0) { // Loose VF
         Vertex middle_vertex = ctr++;
         add_vertex(middle_vertex);

         properties->provider_in[asn] = bottom_vertex;
         properties->provider_out[asn] = top_vertex;

         properties->customer_in[asn] = top_vertex;
         properties->customer_out[asn] = bottom_vertex;

         properties->peer_in[asn] = middle_vertex;
         properties->peer_out[asn] = middle_vertex;

         graph->add_edge(top_vertex, middle_vertex, 0);
         graph->add_edge(top_vertex, bottom_vertex, 0);
         graph->add_edge(middle_vertex, bottom_vertex, 0);
      } else { // Strict VF -- no third vertex needed
         properties->provider_in[asn] = top_vertex;
         properties->provider_out[asn] = bottom_vertex;

         properties->customer_in[asn] = bottom_vertex;
         properties->customer_out[asn] = top_vertex;

         properties->peer_in[asn] = top_vertex;
         properties->peer_out[asn] = bottom_vertex;

         graph->add_edge(bottom_vertex, top_vertex, 0);
      } // if

      // Add host vertices and pathlets if AS is endhost or MM
      if (properties->endhost_ases.count(asn) > 0 ||
          properties->matchmaker_ases.count(asn) > 0)
      {
         // Need to split host vertices to prevent routing thru hosts
         Vertex host_vertex_in = ctr++;
         add_vertex(host_vertex_in);

         Vertex host_vertex_out = ctr++;
         add_vertex(host_vertex_out);

         properties->host_in[asn] = host_vertex_in;
         properties->host_out[asn] = host_vertex_out;

         graph->add_edge(host_vertex_out, properties->customer_in[asn], 0);
         graph->add_edge(properties->customer_out[asn], host_vertex_in, 0);
      } // if
   } // foreach asn

   // Add external pathlets from asrel
   for (auto &rel_line : as_rel_ir) {
      if (rel_line.rel_type == ASRelType::kP2C) {
         auto &provider = rel_line.x;
         auto &customer = rel_line.y;

         graph->add_edge(properties->provider_out[customer], // bottom
                         properties->customer_in[provider], 1); // top

         graph->add_edge(properties->customer_out[provider], // top
                         properties->provider_in[customer], 1); // bottom
      } else { // P2P
         auto &peer_lhs = rel_line.x;
         auto &peer_rhs = rel_line.y;

         graph->add_edge(properties->peer_out[peer_lhs],
                         properties->peer_in[peer_rhs], 1);

         graph->add_edge(properties->peer_out[peer_rhs],
                         properties->peer_in[peer_lhs], 1);
      }
   }
}

template <typename T>
void limited_dfs_parallel(const T& graph,
                          const typename T::Vertex &source,
                          const typename T::Vertex &target,
                          const typename T::Weight &cost,
                          std::size_t max_num_paths,
                          std::size_t max_path_length,
                          const CostMap<T> &cost_map,
                          std::vector<typename T::Path> *paths)
{
   using Graph = T;
   using Path = typename Graph::Path;
   using Weight = typename Graph::Weight;

   tbb::concurrent_vector<Path> threadsafe_paths;

   std::function<void(Path, Weight)> dfs_impl;

   dfs_impl = [&] (Path path, Weight cumul_cost) -> void {
      if (threadsafe_paths.size() >= max_num_paths) { return; }
      if (path.size() > max_path_length) { return; }
      if (path.back() == target && cumul_cost == cost) {
         threadsafe_paths.push_back(path);
      } else {
         auto u = path.back();
         tbb::task_group task_group;
         auto visit_nbrs = [&] (Weight k) {
            auto edges = graph.adj_vertices(u, k);
            Weight remaining_cost = cost - (cumul_cost + k);
            if (edges != nullptr) {
               for (auto &v : *edges) {
                  if (cost_map.count(remaining_cost) > 0
                      && cost_map.at(remaining_cost).count(v) > 0)
                  {
                     path.push_back(v);
                     task_group.run([=] { dfs_impl(path, cumul_cost + k); });
                     path.pop_back();
                  }
               } // for
            } // if
         }; // lambda
         visit_nbrs(0);
         visit_nbrs(1);
         task_group.wait();
      }
   };

   dfs_impl(Path{source}, 0);

   for (std::size_t idx = 0;
        idx < max_num_paths && idx < threadsafe_paths.size();
        ++idx)
   {
      paths->push_back(threadsafe_paths[idx]);
   }
}

template <typename T, typename URNG>
void create_path_to_random_matchmaker(const T &graph,
                                      const T &transpose_graph,
                                      const typename T::Weight &graph_diameter,
                                      const ASNumber &source_asn,
                                      const DovetailProperties<T> &properties,
                                      std::size_t max_num_paths,
                                      std::size_t max_path_length,
                                      typename T::Path *chosen_path,
                                      URNG &&g)
{
   static tbb::concurrent_unordered_map
      < ASNumber, tbb::concurrent_unordered_set<ASNumber> > mm_blacklist;

   mm_blacklist[source_asn].insert(source_asn);

   using Vertex = typename T::Vertex;
   Vertex source_vertex = properties.host_out.at(source_asn);

   std::vector<ASNumber> mm_ases;

   std::copy(properties.matchmaker_ases.cbegin(),
             properties.matchmaker_ases.cend(),
             std::back_inserter(mm_ases));

   std::shuffle(mm_ases.begin(), mm_ases.end(), g);
   CostMap<T> cost_map;
   CostWeights<T> cost_weights;

   ASNumber *chosen_mm_asn = nullptr;

   for (auto &mm_asn : mm_ases) {
      if (mm_blacklist[mm_asn].count(source_asn) > 0) {
         continue;
      }

      cost_map.clear();

      Vertex mm_vertex = properties.host_in.at(mm_asn);
      compute_available_costs(transpose_graph, mm_vertex, graph_diameter,
                              &cost_map);

      // Source ---> Matchmaker path uses exp6
      exp_k_cost_weights<T>(source_vertex, cost_map, 6, &cost_weights);

      if (cost_weights.empty()) {
         mm_blacklist[mm_asn].insert(source_asn);
         continue;
      } else {
         chosen_mm_asn = &mm_asn;
         break;
      }
   }

   // Cost map and cost weights are still populated correctly from above loop.
   if (chosen_mm_asn != nullptr) {
      Vertex mm_vertex = properties.host_in.at(*chosen_mm_asn);
      typename T::Weight sampled_path_cost;
      std::vector<typename T::Path> dfs_paths;

      sample_by_weights(cost_weights.cbegin(), cost_weights.cend(),
                        &sampled_path_cost, 1, g);

      limited_dfs_parallel(graph, source_vertex, mm_vertex, sampled_path_cost,
                           max_num_paths, max_path_length, cost_map,
                           &dfs_paths);

      *chosen_path = single_random_sample(dfs_paths.cbegin(),
                                          dfs_paths.cend(), g);
   }
}

template <typename T>
unsigned dovetail_path_cost(const typename T::Path &source_to_mm_path,
                            const typename T::Path &mm_to_destination_path,
                            const DovetailProperties<T> &properties)
{
   // Dovetail eligibility seems to be only predicated only the existence of
   // common *ASes*, not necessairly common vertices.

   using Vertex [[ gnu::unused ]] = typename T::Vertex;
   std::vector<ASNumber> common_ases;

   ASPath source_to_mm_ases, mm_to_destination_ases;

   graph_path_to_as_path(source_to_mm_path, properties, &source_to_mm_ases);

   graph_path_to_as_path(mm_to_destination_path, properties,
                         &mm_to_destination_ases);

   auto copy_pred = [&] (const ASNumber &asn) -> bool
   {
      auto itr = std::find(mm_to_destination_ases.cbegin(),
                           mm_to_destination_ases.cend(), asn);
      return itr != mm_to_destination_ases.cend();
   };

   std::copy_if(source_to_mm_ases.cbegin(), source_to_mm_ases.cend(),
                std::back_inserter(common_ases), copy_pred);

   std::cout << source_to_mm_ases << std::endl;
   std::cout << mm_to_destination_ases << std::endl;
   std::cout << common_ases << std::endl;
   std::cout << "*****************************************" << std::endl;

   return 0;
}

} // namespace nrl

#endif // DOVETAIL_HPP_

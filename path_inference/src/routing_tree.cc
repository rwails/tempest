#include "routing_tree.h"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>
#include <mutex>
#include <queue>
#include <set>
#include <thread>
#include <tuple>
#include <utility>

#include "generic.hpp"

namespace bgpsim {

// Helper for add_relationships...
using RelationshipInfo = std::tuple<ASNumber, ASNumber, Relationship>;

// Helper for add_relationships...
static Relationship interpret_rel_indicator(const char *rel_indicator)
{
   if (std::strcmp("0", rel_indicator) == 0) {
      return Relationship::kPeer;
   } else if (std::strcmp("-1", rel_indicator) == 0) {
      return Relationship::kProvider;
   } else {
      assert(false);
      return Relationship::kProvider;
   }
}

// Helper for add_relationships...
static int parse_relationship_line(const std::string &line,
                                   RelationshipInfo *into)
{
   if (line[0] == '#') {
      return -1;
   }

   const char *delim = "|";
   char *raw_str = new char[line.size() + 1];
   std::strcpy(raw_str, line.c_str());

   char *asn_1 = std::strtok(raw_str, delim);
   char *asn_2 = std::strtok(nullptr, delim);
   char *rel_indicator = std::strtok(nullptr, delim);

   std::get<0>(*into) = asn_1;
   std::get<1>(*into) = asn_2;
   std::get<2>(*into) = interpret_rel_indicator(rel_indicator);

   delete[] raw_str; raw_str = nullptr;

   return 0;
}

void add_relationships_to_adj_list(const std::string &relationship_filename,
                                   AdjList *adj_list)
{
   std::ifstream relationship_file(relationship_filename,
                                   std::ifstream::in);
   std::string line;
   RelationshipInfo info;
   AdjListElem insert_elem;

   while (std::getline(relationship_file, line)) {
      if (parse_relationship_line(line, &info) != 0) continue;

      const ASNumber &asn_1 = std::get<0>(info);
      const ASNumber &asn_2 = std::get<1>(info);

      if (std::get<2>(info) == Relationship::kPeer) {
         insert_elem.asn = asn_2;
         insert_elem.rel = Relationship::kPeer;
         (*adj_list)[asn_1].push_back(insert_elem);

         insert_elem.asn = asn_1;
         (*adj_list)[asn_2].push_back(insert_elem);
      } else {
         // Provider -> Customer
         insert_elem.asn = asn_2;
         insert_elem.rel = Relationship::kCustomer;
         (*adj_list)[asn_1].push_back(insert_elem);

         insert_elem.asn = asn_1;
         insert_elem.rel = Relationship::kProvider;
         (*adj_list)[asn_2].push_back(insert_elem);
      }
   }

   relationship_file.close();
}

static void add_origin_paths(const std::vector<Origin> origins,
                             IndexedPaths *out,
                             AdjList *adj_list)
{
   // TODO: Make this function cleaner.
   ASNumber true_origin;
   for (auto &origin : origins) {
      if (origin.origin_type == OriginType::kTrue) {
         true_origin = origin.asn;
      }
   }

   AdjListElem insert_elem;

   for (auto &origin : origins) {
      switch (origin.origin_type) {
         case OriginType::kTrue:
         case OriginType::kFalse:
            out->insert(std::make_pair(origin.asn, Path{origin.asn}));
            break;
         case OriginType::kOneHop:
            out->insert(std::make_pair(origin.asn,
                                       Path{true_origin, origin.asn}));
            // Add 'fake' edge to the graph
            insert_elem.asn = true_origin;
            insert_elem.rel = Relationship::kProvider;
            (*adj_list)[origin.asn].push_back(insert_elem);
            break;
         default:
            assert(false);
            break;
      }
   }
}

static void update_paths(const ASNumber &asn, const ASNumber &visited_by,
                         const std::string &pfx,
                         const SimulationPolicy &sim_policy,
                         IndexedPaths *out)
{
   bool path_exists = true, new_path_is_better = false;

   // If we don't have a path already, use the new path.
   auto itr = out->find(asn);
   if (itr == out->end()) {
      path_exists = false;
   }

   Path new_path = (*out)[visited_by];

   if (path_exists) { // Check to see if our current path is better.
      Path current_path = (*out)[asn];
      current_path.pop_back();
      if (!sim_policy.path_compare(asn, pfx, current_path, new_path)) {
         new_path_is_better = true;
      }
   }

   if (!path_exists || new_path_is_better) {
      new_path.push_back(asn);
      (*out)[asn] = new_path;
   }
}

struct BFSQueueElem {
   ASNumber asn, visited_by;
};

using BFSQueue = std::queue<BFSQueueElem>;

void bfs_stage_one(const AdjList &adj_list, const std::string &prefix,
                   const SimulationPolicy &sim_policy,
                   IndexedPaths *out, std::set<ASNumber> *visited)
{
   BFSQueue queue;

   for (auto &asn_path : *out) {
      queue.push(BFSQueueElem{ asn_path.first, asn_path.first });
   }

   while (!queue.empty()) {
      auto &current = queue.front();

      if (!sim_policy.import(current.asn, prefix, out->at(current.visited_by)))
      {
         queue.pop();
         continue;
      }

      // Check to see if we have already visited this node.
      auto itr = visited->find(current.asn);

      // This is a new node.
      if (itr == visited->end()) {
         for (const auto &adj : adj_list.at(current.asn)) {
            if (adj.rel == Relationship::kProvider)
               queue.push(BFSQueueElem{ adj.asn, current.asn });
         }
      }

      visited->insert(current.asn);

      // Insert the new path
      if (current.asn != current.visited_by) { // Make sure this node is init
         update_paths(current.asn, current.visited_by, prefix, sim_policy, out);
      }

      queue.pop();
   }
}

void bfs_stage_two(const AdjList &adj_list, const std::string &prefix,
                   const SimulationPolicy &sim_policy,
                   IndexedPaths *out, std::set<ASNumber> *visited)
{
   std::set<ASNumber> new_visited;

   for (auto &asn : (*visited)) {
      for (const auto &adj : adj_list.at(asn)) {
         if (adj.rel == Relationship::kPeer)
            // Ensure that we have not yet visited the new node.
            if (visited->find(adj.asn) == visited->end()) {
               update_paths(adj.asn, asn, prefix, sim_policy, out);
               new_visited.insert(adj.asn);
            }
      }
   }

   for (auto &asn : new_visited) {
      visited->insert(asn);
   }
}

void bfs_stage_three(const AdjList &adj_list, const std::string &prefix,
                     const SimulationPolicy &sim_policy,
                     IndexedPaths *out, std::set<ASNumber> *visited)
{
   BFSQueue queue;
   std::set<ASNumber> new_visited = *visited;

   for (auto &asn : *visited) {
      for (const auto &adj : adj_list.at(asn)) {
         if (adj.rel == Relationship::kCustomer)
            queue.push(BFSQueueElem{ adj.asn, asn });
      }
   }

   while (!queue.empty()) {
      auto &current = queue.front();

      if (!sim_policy.import(current.asn, prefix, out->at(current.visited_by)))
      {
         queue.pop();
         continue;
      }

      // Check to see if this is a new node.
      if (new_visited.find(current.asn) == new_visited.end()) {
         for (const auto &adj : adj_list.at(current.asn)) {
            if (adj.rel == Relationship::kCustomer)
               queue.push(BFSQueueElem{ adj.asn, current.asn });
         }

         new_visited.insert(current.asn);
      }

      // We don't want to overwrite existing paths, so we only add paths to
      // new nodes.
      if (visited->find(current.asn) == visited->end()) {
         update_paths(current.asn, current.visited_by, prefix, sim_policy, out);
      }

      queue.pop();
   }
}

void compute_paths(AdjList adj_list, const std::string &prefix,
                   const std::vector<Origin> &origins,
                   const SimulationPolicy &sim_policy, IndexedPaths *out)
{
   std::set<ASNumber> visited;
   add_origin_paths(origins, out, &adj_list);
   bfs_stage_one(adj_list, prefix, sim_policy, out, &visited);
   bfs_stage_two(adj_list, prefix, sim_policy, out, &visited);
   bfs_stage_three(adj_list, prefix, sim_policy, out, &visited);
}

static void
path_work(const std::vector<ASNumber> &jobs, const AdjList &adj_list,
          IndexedPathsTo *out, std::mutex *mtx)
{
   IndexedPaths paths;
   SimulationPolicy sim_policy{default_import, default_path_compare};

   std::vector< std::pair<ASNumber, IndexedPaths> > tmp;

   for (const auto &asn : jobs) {
      std::vector<Origin> origins{Origin{asn, OriginType::kTrue}};
      compute_paths(adj_list, "NIL", origins, sim_policy, &paths);
      tmp.push_back({asn, paths});
      paths.clear();
   }

   mtx->lock();
   for (auto &pair : tmp) out->insert(pair);
   mtx->unlock();
}

void compute_all_vanilla_paths(const std::vector<ASNumber> &asns,
                               const AdjList &adj_list,
                               IndexedPathsTo *indexed_paths_to,
                               std::size_t max_num_threads)
{
   std::vector<std::thread> threads;
   std::mutex mtx;

   std::size_t n = max_num_threads < asns.size() ?
                   max_num_threads : asns.size();

   std::vector<ASNumber> *chunks = new std::vector<ASNumber>[n];
   chunk(asns, chunks, n);

   for (std::size_t idx = 0; idx < n; ++idx) {
      threads.push_back(
         std::thread(path_work, chunks[idx], adj_list, indexed_paths_to, &mtx)
      );
   }

   for (auto &thread : threads) {
      thread.join();
   }

   delete[] chunks; chunks = nullptr;
}

bool default_import(const ASNumber&, const std::string &, const Path&)
{
   return true;
}

bool default_path_compare(const ASNumber &asn [[ gnu::unused ]],
                          const std::string &pfx [[ gnu::unused ]],
                          const Path &p1, const Path &p2)
{
   if (p1.size() < p2.size()) {
      return true;
   } else if (p1.size() == p2.size()) {
      return p1.back().compare(p2.back()) < 0;
   } else {
      return false;
   }
}

} // namespace bgpsim

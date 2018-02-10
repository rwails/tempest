#ifndef ROUTING_TREE_H_
#define ROUTING_TREE_H_

#include <cstddef>
#include <functional>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

namespace bgpsim {

using ASNumber = std::string;
enum class OriginType { kTrue, kFalse, kOneHop };
enum class Relationship { kCustomer, kProvider, kPeer, kSibling };

struct AdjListElem {
   ASNumber asn;
   Relationship rel;
};

using AdjList = std::unordered_map< ASNumber, std::vector<AdjListElem> >;

using Path = std::vector<ASNumber>;

using IndexedPaths = std::map<ASNumber, Path>;

using IndexedPathsTo =
   std::map< ASNumber, IndexedPaths >;

struct Origin {
   ASNumber asn;
   OriginType origin_type;
};

struct SimulationPolicy {
   // Import policy takes an ASN considering import, the origin prefix, and the
   // new path.
   std::function<bool(const ASNumber&, const std::string&, const Path&)> import;
   // Return true if P1 > P2
   std::function<bool(const ASNumber&, const std::string&, const Path&,
                      const Path&)> path_compare;
};

// Populates an AdjList from a CAIDA AS Relationship file.
void add_relationships_to_adj_list(const std::string &relationship_filename,
                                   AdjList *adj_list);

void compute_paths(AdjList adj_list, const std::string &prefix,
                   const std::vector<Origin> &origins,
                   const SimulationPolicy &sim_policy, IndexedPaths *out);

void compute_all_vanilla_paths(const std::vector<ASNumber> &asns,
                               const AdjList &adj_list,
                               IndexedPathsTo *indexed_paths_to,
                               std::size_t max_num_threads);

bool default_import(const ASNumber&, const std::string &, const Path&);

bool default_path_compare(const ASNumber&, const std::string &,
                          const Path &, const Path &);

} // namespace bgpsim

#endif // ROUTING_TREE_H_

#include "dovetail.hpp"
#include <algorithm>
#include <iterator>
#include <random>

namespace nrl {

void find_endhost_ases(const ASRelIR &as_rel_ir,
                       std::set<ASNumber> *endhost_ases)
{
   std::set<ASNumber> provider_ases, customer_ases;

   for (auto &line : as_rel_ir) {
      // Ignoring P2P relationships for now.
      if (line.rel_type == ASRelType::kP2C) {
         provider_ases.insert(line.x);
         customer_ases.insert(line.y);
      }
   }

   std::set_difference(customer_ases.cbegin(), customer_ases.cend(),
                       provider_ases.cbegin(), provider_ases.cend(),
                       std::inserter(*endhost_ases, endhost_ases->end()));
}

} // nrl

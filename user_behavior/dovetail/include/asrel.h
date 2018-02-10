#ifndef ASREL_H_
#define ASREL_H_
#include <set>
#include <vector>
#include "common_def.h"

namespace nrl {

enum class ASRelType : int { kP2C = -1, kP2P = 0 };

struct ASRelLine {
   ASNumber x;
   ASNumber y;
   ASRelType rel_type;
};

using ASRelIR = std::vector<ASRelLine>;

void extract_all_unique_ases(const ASRelIR &as_rel_ir,
                             std::set<ASNumber> *ases);

void parse_asrel_file(const char *asrel_filename, ASRelIR *ir_out);

} // namespace nrl

#endif // ASREL_H_

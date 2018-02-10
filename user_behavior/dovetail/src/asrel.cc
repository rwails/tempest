#include "asrel.h"
#include <cstdlib>
#include <fstream>
#include <string>
#include <boost/tokenizer.hpp>

namespace nrl {

void extract_all_unique_ases(const ASRelIR &as_rel_ir,
                             std::set<ASNumber> *ases)
{
   for (auto &line : as_rel_ir) {
      ases->insert(line.x);
      ases->insert(line.y);
   }
}

void parse_asrel_file(const char *asrel_filename, ASRelIR *ir_out)
{
   using Separator = boost::char_separator<char>;
   Separator sep("|");
   std::ifstream asrel_file(asrel_filename, std::ifstream::in);
   std::string line;
   ASRelLine rel_line;

   while (std::getline(asrel_file, line)) {
      if (line[0] == '#') { continue; }

      boost::tokenizer<Separator> tok(line, sep);

      {
         int field = 0, t = 0;
         for (auto itr = tok.begin();
              itr != tok.end();
              ++itr, ++field)
         {
            switch(field) {
               case 0:
                  rel_line.x = *itr; break;
               case 1:
                  rel_line.y = *itr; break;
               case 2:
                  t = std::strtol(itr->c_str(), nullptr, 10);
                  rel_line.rel_type = static_cast<ASRelType>(t);
                  break;
               default:
                  break;
            }
         } // for
      } // local scope

      ir_out->emplace_back(std::move(rel_line));

   } // while

   asrel_file.close();
}

} // namespace nrl

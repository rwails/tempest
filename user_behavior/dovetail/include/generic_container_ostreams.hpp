#ifndef GENERIC_CONTAINER_OSTREAMS
#define GENERIC_CONTAINER_OSTREAMS
#include <iostream>
#include <vector>

template <typename T>
std::ostream &operator<<(std::ostream &lhs, const std::vector<T> &rhs)
{
   if (rhs.empty()) {
      lhs << "[]";
   } else {
      auto itr_last_elem = rhs.cend() - 1;
      lhs << "[";
      for (auto itr = rhs.cbegin(); itr < itr_last_elem; ++itr) {
         lhs << *itr << ", ";
      }
      lhs << *itr_last_elem << "]";
   }
   return lhs;
}

#endif // GENERIC_CONTAINER_OSTREAMS

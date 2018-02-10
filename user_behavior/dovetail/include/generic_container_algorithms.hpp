#ifndef GENERIC_CONTAINER_ALGORITHMS_HPP_
#define GENERIC_CONTAINER_ALGORITHMS_HPP_
#include <cstddef>
#include <algorithm>
#include <iterator>
#include <random>
#include <vector>

namespace nrl {

/* Poor man's C++17 std::sample.
 * T1 should implement an input iterator concept,
 * T2 should implement an an output iterator concept.
 */
template <typename T1, typename T2, typename URNG>
void random_sample(T1 first, T1 last, T2 out, std::size_t n, URNG &&g)
{
   std::vector<typename T1::value_type> shuffled_elems;
   std::copy(first, last, std::inserter(shuffled_elems, shuffled_elems.end()));
   std::shuffle(shuffled_elems.begin(), shuffled_elems.end(), g);
   std::copy_n(shuffled_elems.cbegin(), n, out);
}

/*
 * T1 should implement an input iterator concept,
 * T2 should implement an an output iterator concept.
 * T1 should point to (element, weight) pairs.
 */
template <typename T1, typename T2, typename URNG>
void sample_by_weights(T1 first, T1 last, T2 out, std::size_t n, URNG &&g)
{
   using Element = typename T1::value_type::first_type;
   using Weight = typename T1::value_type::second_type;

   std::vector<Element *> elements;
   std::vector<Weight> idx_weights;

   for (auto itr = first; itr != last; ++itr) {
      elements.push_back(&itr->first);
      idx_weights.push_back(itr->second);
   }

   std::discrete_distribution<std::size_t> dist(idx_weights.cbegin(),
                                                idx_weights.cend());

   for (std::size_t idx = 0; idx < n; ++idx) {
      *out = *elements[dist(g)];
      ++out;
   }
}

template <typename T1, typename URNG>
typename T1::value_type single_random_sample(T1 first, T1 last, URNG &&g)
{
   auto n = std::distance(first, last);
   std::uniform_int_distribution<std::size_t> dist(0, n-1);
   auto itr = first + dist(g);
   return *itr;
}

} // namespace nrl

#endif // GENERIC_CONTAINER_ALGORITHMS_HPP_

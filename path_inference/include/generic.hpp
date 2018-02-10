#ifndef GENERIC_HPP_
#define GENERIC_HPP_

#include <cmath>
#include <cstddef>
#include <algorithm>
#include <functional>
#include <random>
#include <vector>

/**
 * Takes a container which provides iterator access to elements of type U.
 * Divides the container into unordered 'chunks'.
 * chunks points to an array of n vectors.
 * After this operator, each chunk vector will contain roughly the same number
 * of elements from the container.  Each chunk vector should be initially empty.
 */

template <typename T, typename U>
void chunk(const T& container, std::vector<U> *chunks, std::size_t n)
{
   assert(n > 0 && n <= container.size());

   std::size_t stride = container.size() / n;

   auto itr = container.begin();

   for (std::size_t idx = 0; idx < n - 1; ++idx) {
      chunks[idx].resize(stride);
      std::copy_n(itr, stride, chunks[idx].begin());
      itr += stride;
   }

   chunks[n - 1].resize(container.end() - itr);
   std::copy(itr, container.end(), chunks[n - 1].begin());
}

template <typename T, typename U, typename V>
void draw_keys_from_weights(
      const T &map,
      U num_draws,
      std::function<void(const typename T::key_type *)> ret_f,
      V *rng)
{
   // Vector used to 'map' keys to indices [0, n-1] for a map of size n.
   std::vector<const typename T::key_type *> keys;
   std::vector<typename T::mapped_type> idx_weights;

   for (auto itr = map.cbegin(); itr != map.cend(); ++itr) {
      keys.push_back(&itr->first);
      idx_weights.push_back(itr->second);
   }

   std::discrete_distribution<std::size_t> dist(idx_weights.cbegin(),
                                                idx_weights.cend());

   for (U i = 0; i < num_draws; ++i) {
      ret_f(keys[dist(*rng)]);
   }
}

std::vector<unsigned int> get_increments(unsigned int total_size,
                                         unsigned int divisions);

#endif // GENERIC_HPP_

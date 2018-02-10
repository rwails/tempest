#ifndef POLY_SOLVER_H_
#define POLY_SOLVER_H_
#include <cstddef>
#include <complex>
#include <vector>

namespace nrl {

using Complex = std::complex<double>;

/*
 * e.g.
 * The polynomial x^2 + 10x - 5 is represented as:
 * poly_coeff = { -5, 10, 1 }
 * num_coeff = 3
 */
void poly_roots(const double *poly_coeff, std::size_t num_coeff,
                std::vector<Complex> *roots);

} // namespace nrl

#endif // POLY_SOLVER_H_

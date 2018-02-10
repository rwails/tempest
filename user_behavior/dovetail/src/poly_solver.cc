#include "poly_solver.h"
#include <cmath>
#include <gsl/gsl_poly.h>

namespace nrl {

void poly_roots(const double *poly_coeff, std::size_t num_coeff,
                std::vector<Complex> *roots)
{
   std::size_t degree = num_coeff - 1;

   // Polynomial has <degree> complex roots, need to allocate doubles for real
   // and img parts.
   double *z = new double[2 * degree];

   auto workspace = gsl_poly_complex_workspace_alloc(num_coeff);

   gsl_poly_complex_solve(poly_coeff, num_coeff, workspace, z);

   gsl_poly_complex_workspace_free(workspace);

   for (std::size_t idx = 0; idx < degree; ++idx) {
      auto &real_part = z[2 * idx];
      auto &imaginary_part = z[2 * idx + 1];

      Complex root(real_part, imaginary_part);
      roots->push_back(root);
   }

   delete[] z; z = nullptr;
}

} // namespace nrl

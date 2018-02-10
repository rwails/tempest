#include <stdint.h>
#include <string.h>
#include "spooky.h"

extern "C" {

uint64_t hash_string(const char *str) {
   return SpookyHash::Hash64(str, strlen(str), 0);
}

} // extern "C"

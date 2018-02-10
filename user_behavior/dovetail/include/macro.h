#ifndef MACRO_H_
#define MACRO_H_

#define BOOL_TO_STR(Value) \
   (Value ? "true" : "false")

#define DISALLOW_COPY_AND_ASSIGN(Typename) \
   Typename(const Typename &rhs) = delete; \
   Typename &operator=(const Typename &rhs) = delete;

#endif // MACRO_H_

add_library(spookyhash SHARED hash.cc spooky.cc)

add_executable(pfi_index index.cc)
target_link_libraries(pfi_index PRIVATE spookyhash gmp)

install(TARGETS spookyhash pfi_index
        RUNTIME DESTINATION bin/
        LIBRARY DESTINATION lib/)

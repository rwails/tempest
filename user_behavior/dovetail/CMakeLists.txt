FILE(GLOB DOVETAIL_SRC src/*.cc)

add_executable(dovetail ${DOVETAIL_SRC})
target_include_directories(dovetail PRIVATE include/)
target_link_libraries(dovetail PRIVATE tbb gsl)

install(TARGETS dovetail
        RUNTIME DESTINATION bin/)

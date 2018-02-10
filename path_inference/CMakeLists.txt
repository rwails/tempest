FILE(GLOB PATH_INFERENCE_SRC src/*.cc)

add_executable(path_inference ${PATH_INFERENCE_SRC})
target_include_directories(path_inference PRIVATE include/)
target_link_libraries(path_inference PRIVATE tbb)

install(TARGETS path_inference
        RUNTIME DESTINATION bin/)

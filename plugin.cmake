###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

add_python_style_test(
  python_static_analysis_large_image
  "${CMAKE_CURRENT_LIST_DIR}/server"
)
add_python_style_test(
  python_static_analysis_large_image_tests
  "${CMAKE_CURRENT_LIST_DIR}/plugin_tests"
)
add_python_style_test(
  python_static_analysis_large_image_scripts
  "${CMAKE_CURRENT_LIST_DIR}/scripts"
)

add_eslint_test(
  js_static_analysis_large_image_gruntfile
  "${CMAKE_CURRENT_LIST_DIR}/Gruntfile.js"
  ESLINT_CONFIG_FILE "${CMAKE_CURRENT_LIST_DIR}/.eslintrc"
)
add_eslint_test(
  js_static_analysis_large_image_source
  "${CMAKE_CURRENT_LIST_DIR}/web_client"
  ESLINT_CONFIG_FILE "${CMAKE_CURRENT_LIST_DIR}/.eslintrc"
  ESLINT_IGNORE_FILE "${CMAKE_CURRENT_LIST_DIR}/.eslintignore"
)
add_eslint_test(
  js_static_analysis_large_image_tests
  "${CMAKE_CURRENT_LIST_DIR}/plugin_tests/client"
  ESLINT_CONFIG_FILE "${CMAKE_CURRENT_LIST_DIR}/plugin_tests/client/.eslintrc"
)

add_python_test(cache PLUGIN large_image BIND_SERVER)

add_python_test(tiles PLUGIN large_image BIND_SERVER EXTERNAL_DATA
  "plugins/large_image/sample_image.ptif"
  "plugins/large_image/sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs"
  )
set_property(TEST server_large_image.tiles APPEND PROPERTY ENVIRONMENT
  "LARGE_IMAGE_DATA=${PROJECT_BINARY_DIR}/data/plugins/large_image")

add_python_test(cached_tiles PLUGIN large_image SUBMODULE MemcachedCache
  BIND_SERVER EXTERNAL_DATA
  "plugins/large_image/sample_jp2k_33003_TCGA-CV-7242-11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs")
set_property(TEST server_large_image.cached_tiles.MemcachedCache APPEND
  PROPERTY ENVIRONMENT
  "LARGE_IMAGE_CACHE_BACKEND=memcached"
  "LARGE_IMAGE_DATA=${PROJECT_BINARY_DIR}/data/plugins/large_image")

add_python_test(cached_tiles PLUGIN large_image SUBMODULE PythonCache
  BIND_SERVER)
set_property(TEST server_large_image.cached_tiles.PythonCache APPEND PROPERTY
  ENVIRONMENT
  "LARGE_IMAGE_CACHE_BACKEND=python"
  "LARGE_IMAGE_DATA=${PROJECT_BINARY_DIR}/data/plugins/large_image")

add_python_test(sources PLUGIN large_image BIND_SERVER EXTERNAL_DATA
  "plugins/large_image/sample_image.ptif"
  "plugins/large_image/sample_jp2k_33003_TCGA-CV-7242-11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs"
  )
set_property(TEST server_large_image.sources APPEND PROPERTY ENVIRONMENT
  "LARGE_IMAGE_DATA=${PROJECT_BINARY_DIR}/data/plugins/large_image")


add_python_test(import PLUGIN large_image BIND_SERVER)

add_python_test(girderless PLUGIN large_image EXTERNAL_DATA
  "plugins/large_image/sample_image.ptif"
  "plugins/large_image/sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs"
  )
set_property(TEST server_large_image.girderless APPEND PROPERTY ENVIRONMENT
  "LARGE_IMAGE_DATA=${PROJECT_BINARY_DIR}/data/plugins/large_image")

add_web_client_test(
    large_image
    "${CMAKE_CURRENT_LIST_DIR}/plugin_tests/largeImageSpec.js"
    PLUGIN large_image)

add_web_client_test(annotation "${CMAKE_CURRENT_LIST_DIR}/plugin_tests/client/annotation.js" PLUGIN large_image)

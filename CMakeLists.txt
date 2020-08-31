cmake_minimum_required(VERSION 3.13.4)

project(ABLTemporalBoneSegmentation)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/Auditory-Biophysics-Lab/Slicer-ABLTemporalBoneSegmentation")
set(EXTENSION_CATEGORY "Otolaryngology")
set(EXTENSION_CONTRIBUTORS "Evan Simpson (ABL at UWO), Ben Connors (ABL at UWO)")
set(EXTENSION_DESCRIPTION "Temporal bone deep-learning segmentation and pre-processing module.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/Auditory-Biophysics-Lab/Slicer-ABLTemporalBoneSegmentation/master/ABLTemporalBoneSegmentationModule/Resources/Icons/ABLTemporalBoneSegmentationModule.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/Auditory-Biophysics-Lab/Slicer-ABLTemporalBoneSegmentation/master/Images/main.png")
set(EXTENSION_DEPENDS "SlicerElastix") # Specified as a list or "NA" if no dependencies
set(EXTENSION_BUILD_SUBDIRECTORY inner-build)

set(SUPERBUILD_TOPLEVEL_PROJECT inner)

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})
mark_as_superbuild(Slicer_DIR)

find_package(Git REQUIRED)
mark_as_superbuild(GIT_EXECUTABLE)

#-----------------------------------------------------------------------------
# SuperBuild setup
option(${EXTENSION_NAME}_SUPERBUILD "Build ${EXTENSION_NAME} and the projects it depends on." ON)
mark_as_advanced(${EXTENSION_NAME}_SUPERBUILD)
if(${EXTENSION_NAME}_SUPERBUILD)
  include("${CMAKE_CURRENT_SOURCE_DIR}/SuperBuild.cmake")
  return()
endif()

#-----------------------------------------------------------------------------
# Extension modules
## NEXT_MODULE
add_subdirectory(ABLTemporalBoneSegmentationModule)
add_subdirectory(IntraSampleRegistration)
#install(
#	DIRECTORY "${CMAKE_BINARY_DIR}/../python-packages-install/"
#	DESTINATION ${Slicer_INSTALL_ROOT}${Slicer_BUNDLE_EXTENSIONS_LOCATION}
#	COMPONENT RuntimeLibraries
#)
#-----------------------------------------------------------------------------
set(EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS)
#list(APPEND EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS "${Foo_DIR};Foo;RuntimeLibraries;/")
set(${EXTENSION_NAME}_CPACK_INSTALL_CMAKE_PROJECTS "${EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS}" CACHE STRING "List of external projects to install" FORCE)

#-----------------------------------------------------------------------------
list(APPEND CPACK_INSTALL_CMAKE_PROJECTS "${CMAKE_BINARY_DIR};${EXTENSION_NAME};ALL;/")
list(APPEND CPACK_INSTALL_CMAKE_PROJECTS "${${EXTENSION_NAME}_CPACK_INSTALL_CMAKE_PROJECTS}")
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})

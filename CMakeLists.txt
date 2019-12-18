cmake_minimum_required(VERSION 3.5)

project(AuditoryBiophysicsLabOtolaryngology)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/TemporalDeepLearningPreProcessModule")
set(EXTENSION_CATEGORY "Examples")
set(EXTENSION_CONTRIBUTORS "Evan Simpson (HML & SKA Lab.)")
set(EXTENSION_DESCRIPTION "Temporal bone deep learning pre processing module.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/TemporalDeepLearningPreProcessModule.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/TemporalDeepLearningPreProcessModule/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(DeepLearningPreProcessModule)
add_subdirectory(IntraSampleRegistration)
add_subdirectory(SkullThicknessMapping)
add_subdirectory(SlicerRadiomicsCLI)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
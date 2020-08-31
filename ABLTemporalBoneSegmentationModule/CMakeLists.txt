#-----------------------------------------------------------------------------
set(MODULE_NAME ABLTemporalBoneSegmentationModule)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/Atlases/Fiducial_L.fcsv
  Resources/Atlases/Fiducial_R.fcsv
  Resources/Icons/check.png
  Resources/Icons/fiducial.png
  Resources/Icons/fit.png
  Resources/Masks/CochleaRegistrationMask_L.nrrd
  Resources/Masks/CochleaRegistrationMask_R.nrrd
  Resources/Parameters/Parameters_Rigid.txt
  Resources/Parameters/Parameters_Rigid_Sumit.txt
  Resources/Models/ABLTempSeg.json
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()

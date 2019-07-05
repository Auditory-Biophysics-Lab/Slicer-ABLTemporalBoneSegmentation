# general imports
# import PyQt5.Qt as qt
import qt
import slicer
import ctk
import vtk
import SimpleITK as itk
import sitkUtils as itku
import logging
import inspect
from slicer.ScriptedLoadableModule import *

# custom imports
import uiTools


# Main Initialization & Info
class DeepLearningPreProcessModule(ScriptedLoadableModule):
    """
    Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Cochlea Deep-Learning Pre-Process"
        self.parent.categories = ["Otolaryngology"]
        self.parent.dependencies = []
        self.parent.contributors = ["Luke Helpard (Western University) and Evan Simpson (Western University)"]
        self.parent.helpText = """
        
            """
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This file was originally developed by Luke Helpard and Evan Simpson at" \
                                          "the University of Western Ontario. "


# User Interface
class DeepLearningPreProcessModuleWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
    # Data members
    atlasNode = None            # TODO remove?
    atlasFiducialNode = None    # TODO remove?
    inputNode = None
    fiducialSet = None

    # TODO make as many local
    # TODO set tooltip for most
    # UI members
    inputSelector = None
    fitAllButton = None
    leftBoneCheckBox = None
    rightBoneCheckBox = None
    resampleSection = None
    resamplingInfoLabel = None
    resampleSpacingXBox = None
    resampleSpacingYBox = None
    resampleSpacingZBox = None
    resampleButton = None
    fiducialSection = None
    fiducialTabs = None
    fiducialApplyButton = None
    fiducialOverlayCheckbox = None
    fiducialHardenButton = None
    rigidSection = None
    rigidApplyButton = None

    # TODO remove
    # cropButton = None
    # defineROIButton = None
    # flipButton = None
    # outputSelector = None

    # main initialization ------------------------------------------------------------------------------
    def __init__(self, parent):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.init_input_tools()
        self.init_resample_tools()
        self.init_fiducial_registration()
        self.init_rigid_registration()

    def init_input_tools(self):
        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputSelector.selectNodeUponCreation = True
        self.inputSelector.addEnabled = False
        # self.inputSelector.removeEnabled = False
        self.inputSelector.noneEnabled = True
        self.inputSelector.setMRMLScene(slicer.mrmlScene)
        self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.click_load_volume)
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Icons/fit.png'
        icon = qt.QPixmap(path).scaled(qt.QSize(16, 16), qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
        self.fitAllButton = qt.QToolButton()
        self.fitAllButton.setIcon(qt.QIcon(icon))
        self.fitAllButton.setFixedHeight(22)
        self.fitAllButton.enabled = False
        self.fitAllButton.setToolTip("Fit all Slice Viewers to match the extent of the lowest non-Null volume layer.")
        self.fitAllButton.connect('clicked(bool)', self.click_fit_all_views)
        self.leftBoneCheckBox = qt.QCheckBox("Left Temporal Bone")
        self.leftBoneCheckBox.checked = False
        self.leftBoneCheckBox.connect('toggled(bool)', self.click_left_bone)
        self.rightBoneCheckBox = qt.QCheckBox("Right Temporal Bone")
        self.rightBoneCheckBox.checked = False
        self.rightBoneCheckBox.connect('toggled(bool)', self.click_right_bone)

    def init_resample_tools(self):
        self.resampleSection = uiTools.dropdown("Spacing Resample Tools", disabled=True)
        self.resamplingInfoLabel = qt.QLabel("Load in a sample to enable spacing resample.")
        self.resampleSpacingXBox = uiTools.spin_box(0, 1000, self.click_spacing_spin_box)
        self.resampleSpacingYBox = uiTools.spin_box(0, 1000, self.click_spacing_spin_box)
        self.resampleSpacingZBox = uiTools.spin_box(0, 1000, self.click_spacing_spin_box)
        self.resampleButton = qt.QPushButton("Resample Input to New Volume")
        self.resampleButton.setFixedHeight(23)
        self.resampleButton.enabled = False
        self.resampleButton.connect('clicked(bool)', self.click_resample_volume)

    def init_fiducial_registration(self):
        self.fiducialSection = uiTools.dropdown("Fiducial Registration", disabled=True)
        self.fiducialTabs = qt.QTabWidget()
        self.fiducialTabs.connect('currentChanged(int)', self.click_fiducial_tab)
        self.fiducialApplyButton = qt.QPushButton("Apply")
        self.fiducialApplyButton.connect('clicked(bool)', self.click_fiducial_apply)
        self.fiducialApplyButton.enabled = False
        self.fiducialOverlayCheckbox = qt.QCheckBox("Overlay")
        self.fiducialOverlayCheckbox.connect('toggled(bool)', self.click_fiducial_overlay)
        self.fiducialOverlayCheckbox.enabled = False
        self.fiducialHardenButton = qt.QPushButton("Harden")
        self.fiducialHardenButton.connect('clicked(bool)', self.click_fiducial_harden)
        self.fiducialHardenButton.enabled = False

    def init_rigid_registration(self):
        self.rigidSection = uiTools.dropdown("Rigid Registration", disabled=True)
        self.rigidApplyButton = qt.QPushButton("Apply\n Rigid Registration")
        self.rigidApplyButton.connect('clicked(bool)', self.click_rigid_apply)

    # TODO remove
    def init_crop_tools(self):
        self.defineROIButton = qt.QPushButton("Define ROI")
        self.defineROIButton.enabled = True
        self.cropButton = qt.QPushButton("Crop")
        self.cropButton.enabled = True

    # TODO remove
    def init_flip_tools(self):
        self.flipButton = qt.QPushButton("Flip Volume")
        self.flipButton.enabled = False
        self.flipButton.connect('clicked(bool)', self.click_flip_volume)

    # TODO remove
    def init_output_tools(self):
        self.outputSelector = slicer.qMRMLNodeComboBox()
        self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.outputSelector.selectNodeUponCreation = True
        self.outputSelector.addEnabled = False
        self.outputSelector.removeEnabled = False
        self.outputSelector.noneEnabled = True
        self.outputSelector.showHidden = False
        self.outputSelector.showChildNodeTypes = False
        self.outputSelector.setMRMLScene(slicer.mrmlScene)

    # main ui layout building ------------------------------------------------------------------------------
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.layout.addWidget(self.build_input_tools())
        self.layout.addWidget(self.build_resample_tools())
        # self.layout.addWidget(self.build_reference_tools())
        self.layout.addWidget(self.build_fiducial_registration())
        self.layout.addWidget(self.build_rigid_registration())
        self.layout.addStretch()

    def build_input_tools(self):
        dropdown = uiTools.dropdown("Input Selection")
        layout = qt.QFormLayout(dropdown)
        layout.addRow(qt.QLabel("Select an input volume to begin, then ensure the correct side is selected."))
        box = qt.QHBoxLayout()
        box.addWidget(self.inputSelector)
        box.addWidget(self.fitAllButton)
        layout.addRow("Input Volume: ", box)
        sideSelection = qt.QHBoxLayout()
        sideSelection.addWidget(self.leftBoneCheckBox)
        sideSelection.addWidget(self.rightBoneCheckBox)
        layout.addRow("Side Selection: ", sideSelection)
        layout.setMargin(10)
        return dropdown

    def build_resample_tools(self):
        grid = qt.QGridLayout()
        label = qt.QLabel("X:")
        label.setAlignment(qt.Qt.AlignCenter)
        grid.addWidget(label, 0, 0, 1, 1)
        grid.addWidget(self.resampleSpacingXBox, 0, 1, 1, 1)
        label = qt.QLabel("um    Y:")
        label.setAlignment(qt.Qt.AlignCenter)
        grid.addWidget(label, 0, 3, 1, 1)
        grid.addWidget(self.resampleSpacingYBox, 0, 4, 1, 1)
        label = qt.QLabel("um    Z:")
        label.setAlignment(qt.Qt.AlignCenter)
        grid.addWidget(label, 0, 5, 1, 1)
        grid.addWidget(self.resampleSpacingZBox, 0, 6, 1, 1)
        label = qt.QLabel("um")
        label.setAlignment(qt.Qt.AlignCenter)
        grid.addWidget(label, 0, 7, 1, 1)
        grid.addWidget(self.resampleButton, 0, 8, 1, 20)

        layout = qt.QVBoxLayout(self.resampleSection)
        layout.addWidget(self.resamplingInfoLabel)
        layout.addLayout(grid)
        layout.setMargin(10)
        return self.resampleSection

    def build_fiducial_registration(self):
        row = qt.QHBoxLayout()
        row.addWidget(self.fiducialApplyButton)
        row.addWidget(self.fiducialOverlayCheckbox)
        row.addWidget(self.fiducialHardenButton)

        layout = qt.QVBoxLayout(self.fiducialSection)
        layout.addWidget(qt.QLabel("Set at least 3 fiducials. Setting all 5 yields the best results."))
        layout.addWidget(self.fiducialTabs)
        layout.addLayout(row)
        layout.setMargin(10)
        return self.fiducialSection

    def build_rigid_registration(self):
        layout = qt.QHBoxLayout(self.rigidSection)
        layout.addWidget(self.rigidApplyButton)
        layout.setMargin(10)
        return self.rigidSection

    # TODO remove
    def build_crop_dropdown(self):
        dropdown = ctk.ctkCollapsibleButton()
        dropdown.text = "Crop Tools"
        layout = qt.QFormLayout(dropdown)
        layout.addRow(self.defineROIButton)
        layout.addRow(self.cropButton)
        layout.setMargin(10)
        return dropdown

    # TODO remove
    def build_flip_tools(self):
        dropdown = ctk.ctkCollapsibleButton()
        dropdown.text = "Flip Volume"
        layout = qt.QFormLayout(dropdown)
        layout.addRow(self.flipButton)
        layout.setMargin(10)
        return dropdown

    # TODO remove
    def build_output_tools(self):
        dropdown = ctk.ctkCollapsibleButton()
        dropdown.text = "Output"
        layout = qt.QFormLayout(dropdown)
        layout.addRow("Output Volume: ", self.outputSelector)
        layout.setMargin(10)
        return dropdown

    # step completion checks
    # TODO break up this function
    def update_state(self):
        # check input stage complete
        if self.inputNode is not None and (self.leftBoneCheckBox.isChecked() or self.rightBoneCheckBox.isChecked()):
            self.fitAllButton.enabled = True
            self.resampleSection.enabled = True
            self.resampleSection.collapsed = False
            self.fiducialSection.enabled = True
            self.fiducialSection.collapsed = False
            self.rigidSection.enabled = True
            self.rigidSection.collapsed = False
            # TODO check if fiducials already displayed
            # TODO move around
            self.finalize_input()
            self.update_view()
        else:
            self.fitAllButton.enabled = False
            self.resampleSection.enabled = False
            self.resampleSection.collapsed = True
            self.fiducialSection.enabled = False
            self.fiducialSection.collapsed = True
            self.rigidSection.enabled = False
            self.rigidSection.collapsed = True

    # input complete - fetch atlas, fiducials, and populate table
    def finalize_input(self):
        # TODO add checks to see if everything went in properly (i.e. we have some fiducials)
        # TODO change to fiducial based?
        if self.atlasNode is None:
            side_indicator = 'R' if self.rightBoneCheckBox.isChecked() else 'L'
            self.atlasNode, self.atlasFiducialNode = DeepLearningPreProcessModuleLogic().load_atlas_and_fiducials(side_indicator)
            self.fiducialSet = DeepLearningPreProcessModuleLogic().initialize_fiducial_set(self.atlasFiducialNode)
            for f in self.fiducialSet: self.fiducialTabs.addTab(uiTools.build_fiducial_tab(f, self.click_fiducial_set), f["label"])

    # layout work
    def update_view(self):
        # TODO change colour and label to display that is atlas
        # set 3 over 3 view
        slicer.app.layoutManager().setLayout(21)
        # update input and atlas slice views
        if self.inputNode is not None:
            volume_id = self.inputNode.GetID()
            slicer.app.layoutManager().sliceWidget("Red").sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volume_id)
            slicer.app.layoutManager().sliceWidget("Yellow").sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volume_id)
            slicer.app.layoutManager().sliceWidget("Green").sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volume_id)
        if self.atlasNode is not None:
            volume_id = self.atlasNode.GetID()
            slicer.app.layoutManager().sliceWidget("Red+").sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volume_id)
            slicer.app.layoutManager().sliceWidget("Yellow+").sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volume_id)
            slicer.app.layoutManager().sliceWidget("Green+").sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volume_id)
        self.click_fit_all_views()

    # ui button actions ------------------------------------------------------------------------------
    def click_load_volume(self):
        self.inputNode = self.inputSelector.currentNode()
        if self.inputNode is None: return self.update_state()
        # check for side selection
        for c in self.inputNode.GetName():
            if c.isdigit(): continue
            if c.isalpha():
                if c.upper() == 'R': self.click_right_bone(force=True)
                if c.upper() == 'L': self.click_left_bone(force=True)
            break
        # set spacing
        spacing = DeepLearningPreProcessModuleLogic().get_um_spacing(self.inputNode.GetSpacing())
        self.resamplingInfoLabel.text = "The input volume was imported with a spacing of (X: " + str(spacing[0]) + "um,  Y: " + str(spacing[1]) + "um,  Z: " + str(spacing[2]) + "um)"
        self.resampleSpacingXBox.value, self.resampleSpacingYBox.value, self.resampleSpacingZBox.value = spacing[0], spacing[1], spacing[2]
        # update state
        self.update_state()

    def click_fit_all_views(self):
        logic = slicer.app.layoutManager().mrmlSliceLogics()
        for i in range(logic.GetNumberOfItems()): logic.GetItemAsObject(i).FitSliceToAll()
        if self.fiducialSet is not None and len(self.fiducialSet) > 0:
            self.click_fiducial_tab(self.fiducialTabs.currentIndex)

    def click_right_bone(self, force=False):
        if force: self.rightBoneCheckBox.setChecked(True)
        if self.rightBoneCheckBox.isChecked(): self.leftBoneCheckBox.setChecked(False)
        self.update_state()

    def click_left_bone(self, force=False):
        if force: self.leftBoneCheckBox.setChecked(True)
        if self.leftBoneCheckBox.isChecked(): self.rightBoneCheckBox.setChecked(False)
        self.update_state()

    def click_spacing_spin_box(self):
        if self.inputNode is None: return
        currentSpacing = DeepLearningPreProcessModuleLogic().get_um_spacing(self.inputNode.GetSpacing())
        boxSpacing = [self.resampleSpacingXBox.value, self.resampleSpacingYBox.value, self.resampleSpacingZBox.value]
        self.resampleButton.enabled = currentSpacing != boxSpacing

    def click_resample_volume(self):
        self.resampleButton.enabled = False
        resampledNode = DeepLearningPreProcessModuleLogic().pull_node_resample_push(self.inputNode, [self.resampleSpacingXBox.value/1000, self.resampleSpacingYBox.value/1000, self.resampleSpacingZBox.value/1000])
        # TODO maybe remove and add a table?
        self.inputSelector.setCurrentNode(resampledNode)
        self.click_load_volume()

    def click_fiducial_tab(self, index):
        ras = self.fiducialSet[index]['atlas_indices']
        slicer.app.layoutManager().sliceWidget("Red+").sliceView().mrmlSliceNode().JumpSlice(ras[0], ras[1], ras[2])
        slicer.app.layoutManager().sliceWidget("Yellow+").sliceView().mrmlSliceNode().JumpSlice(ras[0], ras[1], ras[2])
        slicer.app.layoutManager().sliceWidget("Green+").sliceView().mrmlSliceNode().JumpSlice(ras[0], ras[1], ras[2])

    def click_fiducial_set(self, fiducial):
        # TODO
        return

    def click_fiducial_apply(self):
        # TODO
        return

    def click_fiducial_overlay(self):
        # TODO
        return

    def click_fiducial_harden(self):
        # TODO
        return

    def click_rigid_apply(self):
        # TODO
        return

    # def click_flip_volume(self):
    #     logic = DeepLearningPreProcessModuleLogic()
    #     print("Flipping...")
    #
    #     vtkMatrix = vtk.vtkMatrix4x4()
    #     for row in range(4):
    #         for col in range(4):
    #             if row == col and row == 0:
    #                 vtkMatrix.SetElement(row, col, -1)
    #             elif row == col:
    #                 vtkMatrix.SetElement(row, col, 1)
    #             else:
    #                 vtkMatrix.SetElement(row, col, 0)
    #
    #     # Create MRML transform node
    #     self.transformNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
    #     self.transformNode.SetAndObserveMatrixTransformToParent(vtkMatrix)
    #
    #     self.inputNode.SetAndObserveTransformNodeID(self.transformNode.GetID())
    #     slicer.vtkSlicerTransformLogic().hardenTransform(self.inputNode)
    #
    #     self.resampleButton.enabled = True

    # def onApplyButton(self):
    # logic = DeepLearningTestLogic()
    # enableScreenshotsFlag = self.enableScreenshotsFlagCheckBox.checked
    # logic.run(self.inputSelector.currentNode())


# Main Logic
# noinspection PyMethodMayBeStatic
class DeepLearningPreProcessModuleLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def initialize_fiducial_set(self, atlas_fiducial_node):
        fiducial_set = []
        for i in range(1, atlas_fiducial_node.GetNumberOfFiducials()):
            f = {'label': atlas_fiducial_node.GetNthFiducialLabel(i), 'input_indices': None, 'atlas_indices': [0, 0, 0]}
            atlas_fiducial_node.GetNthFiducialPosition(i, f['atlas_indices'])
            fiducial_set.append(f)
        return fiducial_set

    def load_atlas_and_fiducials(self, side_indicator):
        # TODO possibly add check to see if atlas already persisting comparing hash?
        framePath = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Atlases/"
        atlasPath = framePath + 'Atlas_' + side_indicator + '.mha'
        fiducialPath = framePath + 'Fiducial_' + side_indicator + '.fcsv'
        atlasNode = slicer.util.loadVolume(atlasPath, returnNode=True)[1]
        atlasFiducialNode = slicer.util.loadMarkupsFiducialList(fiducialPath, returnNode=True)[1]
        atlasFiducialNode.SetName("Atlas Fiducials")
        atlasFiducialNode.SetLocked(True)
        return atlasNode, atlasFiducialNode

    def get_um_spacing(self, node):
        return [int(s*1000) for s in node]

    def resample_image(self, image, spacing_in_um):
        oldSpacing = [float("%.3f" % f) for f in image.GetSpacing()]
        newSpacing = [spacing_in_um[0] / 1000, spacing_in_um[1] / 1000, spacing_in_um[2] / 1000]
        oldSize = image.GetSize()
        newSize = [int(a * (b / c)) for a, b, c in zip(oldSize, oldSpacing, newSpacing)]
        resampler = itk.ResampleImageFilter()
        # resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetOutputDirection(image.GetDirection())
        resampler.SetOutputOrigin(image.GetOrigin())
        resampler.SetOutputSpacing(newSpacing)
        resampler.SetSize(newSize)
        resampledImage = resampler.Execute(image)
        return resampledImage

    def pull_node_resample_push(self, node, spacing_in_um):
        image = itku.PullVolumeFromSlicer(node.GetID())
        resampledImage = self.resample_image(image, spacing_in_um)
        resampledNode = itku.PushVolumeToSlicer(resampledImage, None, node.GetName() + "_Resampled", "vtkMRMLScalarVolumeNode")
        return resampledNode

    # def run_flip(self, volume):
    #     # Create VTK matrix object #Credit to Fernando
    #     vtkMatrix = vtk.vtkMatrix4x4()
    #     for row in range(4):
    #         for col in range(4):
    #             if row == col and row == 0:
    #                 vtkMatrix.SetElement(row, col, -1)
    #             elif row == col:
    #                 vtkMatrix.SetElement(row, col, 1)
    #             else:
    #                 vtkMatrix.SetElement(row, col, 0)
    #
    #     # Create MRML transform node
    #     self.transformNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
    #     self.transformNode.SetAndObserveMatrixTransformToParent(vtkMatrix)
    #
    #     volume.SetAndObserveTransformNodeID(self.transformNode.GetID())
    #     slicer.vtkSlicerTransformLogic().hardenTransform(volume)
    #
    # def has_image_data(self, volume_node):
    #     """This is an example logic method that
    # returns true if the passed in volume
    # node has valid image data
    # """
    #     if not volume_node:
    #         logging.debug('hasImageData failed: no volume node')
    #         return False
    #     if volume_node.GetImageData() is None:
    #         logging.debug('hasImageData failed: no image data in volume node')
    #         return False
    #     return True
    #
    # def is_valid_input_output_data(self, input_volume_node, output_volume_node):
    #     """Validates if the output is not the same as input
    # """
    #     if not input_volume_node:
    #         logging.debug('isValidInputOutputData failed: no input volume node defined')
    #         return False
    #     if input_volume_node.GetID() == output_volume_node.GetID():
    #         logging.debug(
    #             'isValidInputOutputData failed: input and output volume is the same. Create a new volume for output '
    #             'to avoid this error.'
    #         )
    #         return False
    #     return True
    #
    # def run(self, input_volume, output_volume, image_threshold, enable_screenshots=0):
    #     """
    # Run the actual algorithm
    # """
    #     return True


# Testing
class DeepLearningPreProcessModuleTest(ScriptedLoadableModuleTest):
    """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        """Run as few or as many tests as needed here.
    """
        self.setUp()
        self.test_DeepLearningPreProcessModule1()

    def test_DeepLearningPreProcessModule1(self):
        """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

        self.delayDisplay("Starting the test")
        # #
        # # first, get some data
        # #
        # import SampleData
        # SampleData.downloadFromURL(
        #     nodeNames='FA',
        #     fileNames='FA.nrrd',
        #     uris='http://slicer.kitware.com/midas3/download?items=5767')
        # self.delayDisplay('Finished with download and loading')
        #
        # volumeNode = slicer.util.getNode(pattern="FA")
        # logic = DeepLearningPreProcessModuleLogic()
        # self.assertIsNotNone(logic.has_image_data(volumeNode))
        # self.delayDisplay('Test passed!')

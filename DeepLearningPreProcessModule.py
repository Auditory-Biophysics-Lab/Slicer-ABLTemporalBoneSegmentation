import PyQt5.Qt as QtReference  # TODO delete reference
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
    # TODO possibly move to logic block?
    atlasNode = None
    atlasFiducialNode = None
    inputNode = None
    inputFiducialNode = None
    fiducialSet = None
    fiducialTransformedNode = None

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
    fiducialPlacer = None
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
        self.fiducialPlacer = slicer.qSlicerMarkupsPlaceWidget()
        self.fiducialPlacer.buttonsVisible = False
        self.fiducialPlacer.placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceSingleMarkup
        self.fiducialPlacer.setMRMLScene(slicer.mrmlScene)
        self.fiducialPlacer.placeButton().show()
        self.fiducialPlacer.connect('activeMarkupsFiducialPlaceModeChanged(bool)', self.click_fiducial_place)

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

        # testing TODO remove
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Atlases/1512L_AtlasTemplate.mha"
        node = slicer.util.loadVolume(path, returnNode=True)[1]
        self.inputSelector.setCurrentNode(node)
        self.click_load_volume()
        # end testing area

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
        layout = qt.QVBoxLayout(self.fiducialSection)
        layout.addWidget(qt.QLabel("Set at least 3 fiducials. Setting all 5 yields the best results."))
        layout.addWidget(self.fiducialTabs)
        row = qt.QHBoxLayout()
        row.addWidget(self.fiducialApplyButton)
        row.addWidget(self.fiducialOverlayCheckbox)
        row.addWidget(self.fiducialHardenButton)
        layout.addLayout(row)
        layout.setMargin(10)
        return self.fiducialSection

    def build_rigid_registration(self):
        layout = qt.QHBoxLayout(self.rigidSection)
        layout.addWidget(self.rigidApplyButton)
        layout.setMargin(10)
        return self.rigidSection

    # TODO remove
    # def build_crop_dropdown(self):
    #     dropdown = ctk.ctkCollapsibleButton()
    #     dropdown.text = "Crop Tools"
    #     layout = qt.QFormLayout(dropdown)
    #     layout.addRow(self.defineROIButton)
    #     layout.addRow(self.cropButton)
    #     layout.setMargin(10)
    #     return dropdown
    #
    # def build_flip_tools(self):
    #     dropdown = ctk.ctkCollapsibleButton()
    #     dropdown.text = "Flip Volume"
    #     layout = qt.QFormLayout(dropdown)
    #     layout.addRow(self.flipButton)
    #     layout.setMargin(10)
    #     return dropdown
    #
    # def build_output_tools(self):
    #     dropdown = ctk.ctkCollapsibleButton()
    #     dropdown.text = "Output"
    #     layout = qt.QFormLayout(dropdown)
    #     layout.addRow("Output Volume: ", self.outputSelector)
    #     layout.setMargin(10)
    #     return dropdown

    # step completion checks
    def check_input_complete(self):
        if self.inputNode is not None and (self.leftBoneCheckBox.isChecked() or self.rightBoneCheckBox.isChecked()):
            self.fitAllButton.enabled = True
            self.resampleSection.enabled = True
            self.resampleSection.collapsed = False
            self.fiducialSection.enabled = True
            self.fiducialSection.collapsed = False
            self.rigidSection.enabled = True
            self.rigidSection.collapsed = False
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

    def check_fiducials_complete(self):
        completed = 0
        for f in self.fiducialSet: completed += 0 if f['input_indices'] == [0, 0, 0] else 1
        self.fiducialApplyButton.enabled = completed >= 3

    # input complete - fetch atlas, fiducials, and populate table
    def finalize_input(self):
        # TODO add checks to see if everything went in properly (i.e. we have some fiducials)
        side_indicator = 'R' if self.rightBoneCheckBox.isChecked() else 'L'
        if self.atlasNode is not None and not self.atlasNode.GetName().startswith('Atlas_' + side_indicator):
            self.atlasNode = None
            self.inputFiducialNode = None
        if self.atlasNode is None:
            self.atlasNode, self.atlasFiducialNode = DeepLearningPreProcessModuleLogic().load_atlas_and_fiducials(side_indicator)
            self.fiducialSet = DeepLearningPreProcessModuleLogic().initialize_fiducial_set(self.atlasFiducialNode)
            self.fiducialTabs.clear()
            for f in self.fiducialSet:
                tab, table = uiTools.build_fiducial_tab(f, self.click_fiducial_set_button)
                f["table"] = table
                self.fiducialTabs.addTab(tab, f["label"])
        if self.inputFiducialNode is None:
            self.inputFiducialNode = slicer.vtkMRMLMarkupsFiducialNode()
            self.inputFiducialNode.SetName("Fiducial Input")
            slicer.mrmlScene.AddNode(self.inputFiducialNode)
            self.fiducialPlacer.setCurrentNode(self.inputFiducialNode)

    # layout work
    def update_view(self):
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
        if self.inputNode is None: return self.check_input_complete()
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
        self.check_input_complete()

    def click_fit_all_views(self):
        logic = slicer.app.layoutManager().mrmlSliceLogics()
        for i in range(logic.GetNumberOfItems()): logic.GetItemAsObject(i).FitSliceToAll()
        if self.fiducialSet is not None and len(self.fiducialSet) > 0:
            self.click_fiducial_tab(self.fiducialTabs.currentIndex)

    def click_right_bone(self, force=False):
        if force: self.rightBoneCheckBox.setChecked(True)
        if self.rightBoneCheckBox.isChecked(): self.leftBoneCheckBox.setChecked(False)
        self.check_input_complete()

    def click_left_bone(self, force=False):
        if force: self.leftBoneCheckBox.setChecked(True)
        if self.leftBoneCheckBox.isChecked(): self.rightBoneCheckBox.setChecked(False)
        self.check_input_complete()

    def click_spacing_spin_box(self):
        if self.inputNode is None: return
        currentSpacing = DeepLearningPreProcessModuleLogic().get_um_spacing(self.inputNode.GetSpacing())
        boxSpacing = [self.resampleSpacingXBox.value, self.resampleSpacingYBox.value, self.resampleSpacingZBox.value]
        self.resampleButton.enabled = currentSpacing != boxSpacing

    def click_resample_volume(self):
        self.resampleButton.enabled = False
        spacing = [float(self.resampleSpacingXBox.value)/1000, float(self.resampleSpacingYBox.value)/1000, float(self.resampleSpacingZBox.value)/1000]
        resampledNode = DeepLearningPreProcessModuleLogic().pull_node_resample_push(self.inputNode, spacing)
        # TODO maybe remove and add a table?
        self.inputSelector.setCurrentNode(resampledNode)
        self.click_load_volume()

    def click_fiducial_tab(self, index):
        ras = self.fiducialSet[index]['atlas_indices']
        slicer.app.layoutManager().sliceWidget("Red+").sliceView().mrmlSliceNode().JumpSlice(ras[0], ras[1], ras[2])
        slicer.app.layoutManager().sliceWidget("Yellow+").sliceView().mrmlSliceNode().JumpSlice(ras[0], ras[1], ras[2])
        slicer.app.layoutManager().sliceWidget("Green+").sliceView().mrmlSliceNode().JumpSlice(ras[0], ras[1], ras[2])

    def click_fiducial_set_button(self, fiducial):
        for i in range(0, self.inputFiducialNode.GetNumberOfFiducials()):
            if self.inputFiducialNode.GetNthFiducialLabel(i) == fiducial["label"]:
                self.inputFiducialNode.RemoveMarkup(i)
                break
        self.fiducialPlacer.setPlaceModeEnabled(True)
        # TODO fix clicking set then changing tab

    def click_fiducial_place(self, placing):
        if placing:
            path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Icons/fiducial.png'
            icon = qt.QPixmap(path).scaled(qt.QSize(16, 16), qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
            self.fiducialTabs.setTabIcon(self.fiducialTabs.currentIndex, qt.QIcon(icon))
        else:
            fiducial = self.fiducialSet[self.fiducialTabs.currentIndex]
            nodeIndex = self.inputFiducialNode.GetNumberOfFiducials() - 1
            self.inputFiducialNode.SetNthFiducialLabel(nodeIndex, fiducial["label"])
            self.inputFiducialNode.GetNthFiducialPosition(nodeIndex, fiducial["input_indices"])
            for i in (range(0, 3)): fiducial["table"].item(0, i).setText(fiducial["input_indices"][i])
            path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Icons/check.png'
            icon = qt.QPixmap(path).scaled(qt.QSize(16, 16), qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
            self.fiducialTabs.setTabIcon(self.fiducialTabs.currentIndex, qt.QIcon(icon))
            self.check_fiducials_complete()

    def click_fiducial_apply(self):
        output, self.fiducialTransformedNode = DeepLearningPreProcessModuleLogic().apply_fiducial_registration(self.inputNode, self.fiducialTransformedNode, self.atlasFiducialNode, self.inputFiducialNode)

        # TODO display
        slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(self.fiducialTransformedNode.GetID())
        slicer.app.layoutManager().sliceWidget('Yellow').sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(self.fiducialTransformedNode.GetID())
        slicer.app.layoutManager().sliceWidget('Green').sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(self.fiducialTransformedNode.GetID())

        # slicer.app.applicationLogic().GetSelectionNode().SetSecondaryVolumeID(self.atlasVolume.GetID())
        # slicer.app.applicationLogic().PropagateForegroundVolumeSelection(0)

        # TODO move to check_state
        self.fiducialOverlayCheckbox.setEnabled(True)
        self.fiducialOverlayCheckbox.setChecked(True)
        self.click_fiducial_overlay()
        self.fiducialHardenButton.setEnabled(True)
        return

    def click_fiducial_overlay(self):
        if self.fiducialOverlayCheckbox.isChecked():
            slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(0.4)
            slicer.app.layoutManager().sliceWidget('Yellow').sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(0.4)
            slicer.app.layoutManager().sliceWidget('Green').sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(0.4)
        else:
            slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(0)
            slicer.app.layoutManager().sliceWidget('Yellow').sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(0)
            slicer.app.layoutManager().sliceWidget('Green').sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(0)

    def click_fiducial_harden(self):
        DeepLearningPreProcessModuleLogic().harden_fiducial_registration(self.fiducialTransformedNode)
        self.fiducialHardenButton.setEnabled(False)
        # TODO set as input
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
class DeepLearningPreProcessModuleLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    @staticmethod
    def initialize_fiducial_set(atlas_fiducial_node):
        fiducial_set = []
        for i in range(0, atlas_fiducial_node.GetNumberOfFiducials()):
            f = {'label': atlas_fiducial_node.GetNthFiducialLabel(i), 'table': None, 'input_indices': [0, 0, 0], 'atlas_indices': [0, 0, 0]}
            atlas_fiducial_node.GetNthFiducialPosition(i, f['atlas_indices'])
            fiducial_set.append(f)
        return fiducial_set

    @staticmethod
    def load_atlas_and_fiducials(side_indicator):
        # TODO possibly add check to see if atlas already persisting?
        framePath = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Atlases/"
        atlasPath = framePath + 'Atlas_' + side_indicator + '.mha'
        fiducialPath = framePath + 'Fiducial_' + side_indicator + '.fcsv'
        atlasNode = slicer.util.loadVolume(atlasPath, returnNode=True)[1]
        atlasFiducialNode = slicer.util.loadMarkupsFiducialList(fiducialPath, returnNode=True)[1]
        atlasFiducialNode.SetName("Atlas Fiducials")
        atlasFiducialNode.SetLocked(True)
        return atlasNode, atlasFiducialNode

    @staticmethod
    def get_um_spacing(node):
        return [int(s*1000) for s in node]

    @staticmethod
    def resample_image(image, spacing):
        oldSpacing = [float("%.3f" % f) for f in image.GetSpacing()]
        oldSize = image.GetSize()
        newSize = [int(a * (b / c)) for a, b, c in zip(oldSize, oldSpacing, spacing)]
        resampler = itk.ResampleImageFilter()
        # resampler.SetInterpolator(itk.sitkBSpline)
        resampler.SetOutputDirection(image.GetDirection())
        resampler.SetOutputOrigin(image.GetOrigin())
        resampler.SetOutputSpacing(spacing)
        resampler.SetSize(newSize)
        resampledImage = resampler.Execute(image)
        return resampledImage

    @staticmethod
    def pull_node_resample_push(node, spacing_in_um):
        image = itku.PullVolumeFromSlicer(node.GetID())
        resampledImage = DeepLearningPreProcessModuleLogic().resample_image(image, spacing_in_um)
        resampledNode = itku.PushVolumeToSlicer(resampledImage, None, node.GetName() + "_Resampled", "vtkMRMLScalarVolumeNode")
        return resampledNode

    @staticmethod
    def apply_fiducial_registration(input_node, fiducial_transformed_node, atlas_fiducial_node, input_fiducial_node):
        # create temporary trimmed atlas fiducial set node (locked & hidden)
        trimmed_atlas_fiducial_node = slicer.vtkMRMLMarkupsFiducialNode()
        for i_f in range(0, input_fiducial_node.GetNumberOfFiducials()):
            for a_f in range(0, atlas_fiducial_node.GetNumberOfFiducials()):
                if input_fiducial_node.GetNthFiducialLabel(i_f) == atlas_fiducial_node.GetNthFiducialLabel(a_f):
                    pos = [0, 0, 0]
                    atlas_fiducial_node.GetNthFiducialPosition(a_f, pos)
                    trimmed_atlas_fiducial_node.AddFiducialFromArray(pos, atlas_fiducial_node.GetNthFiducialLabel(a_f))
                    break
        slicer.mrmlScene.AddNode(trimmed_atlas_fiducial_node)
        trimmed_atlas_fiducial_node.SetName("Trimmed Atlas Fiducials")
        trimmed_atlas_fiducial_node.SetLocked(True)
        for f in range(0, trimmed_atlas_fiducial_node.GetNumberOfFiducials()): trimmed_atlas_fiducial_node.SetNthFiducialVisibility(f, True)
        # set up cli parameters
        transform = slicer.vtkMRMLTransformNode()
        slicer.mrmlScene.AddNode(transform)
        parameters = {'fixedLandmarks'  : trimmed_atlas_fiducial_node.GetID(),
                      'movingLandmarks' : input_fiducial_node.GetID(),
                      'transformType'   : 'Rigid',
                      'saveTransform' 	: transform.GetID()}
        output = slicer.cli.run(slicer.modules.fiducialregistration, None, parameters, wait_for_completion=True)
        # create/add transform node if needed
        if fiducial_transformed_node is None:
            fiducial_transformed_node = slicer.vtkMRMLScalarVolumeNode()
            fiducial_transformed_node.SetName("Fiducial Registered Input Volume")
            slicer.mrmlScene.AddNode(fiducial_transformed_node)
        # apply transform
        fiducial_transformed_node.Copy(input_node)
        # fiducial_transformed_node.SetAndObserveTransformNodeID(transform.GetID())
        fiducial_transformed_node.ApplyTransform(transform.GetTransformToParent())
        # clean up transform and trimmed atlas
        # slicer.mrmlScene.RemoveNode(transform)
        slicer.mrmlScene.RemoveNode(trimmed_atlas_fiducial_node)
        return output, fiducial_transformed_node

    @staticmethod
    def harden_fiducial_registration(fiducial_transformed_node):
        fiducial_transformed_node.HardenTransform()


    # TODO remove
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

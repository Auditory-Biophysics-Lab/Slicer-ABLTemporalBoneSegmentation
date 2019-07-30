import inspect
import re
import qt
import slicer
import SimpleITK as sitk
import sitkUtils as sitku
import Elastix
from slicer.ScriptedLoadableModule import *
from Utilities.InterfaceTools import InterfaceTools

supportedResampleInterpolations = [
    {'title': 'Linear', 'value': sitk.sitkLinear},
    {'title': 'Nearest neighbour', 'value': sitk.sitkNearestNeighbor},
    {'title': 'B-spline', 'value': sitk.sitkBSpline},
    {'title': 'Gaussian', 'value': sitk.sitkGaussian},
    {'title': 'Hamming windowed sinc', 'value': sitk.sitkHammingWindowedSinc},
    {'title': 'Blackman windowed sinc', 'value': sitk.sitkBlackmanWindowedSinc},
    {'title': 'Cosine windowed sinc', 'value': sitk.sitkCosineWindowedSinc},
    {'title': 'Welch windowed sinc', 'value': sitk.sitkWelchWindowedSinc},
    {'title': 'Lanczos windowed sinc', 'value': sitk.sitkLanczosWindowedSinc}
]

supportedResamplePresets = [
    {'title': 'X:154um,  Y:154um,  Z:154um', 'value': [154, 154, 154]},
    {'title': 'X:50um,  Y:50um,  Z:50um', 'value': [50, 50, 50]}
]


# Main Initialization & Info
class DeepLearningPreProcessModule(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Temporal Bone Deep-Learning Pre-Process"
        self.parent.categories = ["Otolaryngology"]
        self.parent.dependencies = []
        self.parent.contributors = ["Luke Helpard (Western University) and Evan Simpson (Western University)"]
        self.parent.helpText = "" + self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This file was originally developed by Luke Helpard and Evan Simpson at The University of Western Ontario in the HML/SKA Auditory Biophysics Lab."


# User Interface Build
class DeepLearningPreProcessModuleWidget(ScriptedLoadableModuleWidget):
    # Data members --------------
    # TODO Comment
    atlasNode = None
    atlasFiducialNode = None
    maskNode = None
    inputFiducialNode = None
    fiducialSet = []
    intermediateNode = None

    # UI members --------------
    sectionsList = []
    inputSelector = None
    fitAllButton = None
    leftBoneCheckBox = None
    rightBoneCheckBox = None
    clearMarkupsFromSceneButton = None
    resampleInfoLabel = None
    resampleTabBox = None
    resamplePresetBox = None
    resampleSpacingXBox = None
    resampleSpacingYBox = None
    resampleSpacingZBox = None
    resampleInterpolation = None
    resampleButton = None
    fiducialPlacer = None
    fiducialTabs = None
    fiducialTabsLastIndex = None
    fiducialApplyButton = None
    fiducialRevertButton = None
    fiducialAtlasOverlay = None
    fiducialHardenButton = None
    rigidStatus = None
    rigidProgress = None
    rigidApplyButton = None
    movingSelector = None

    # main initialization ------------------------------------------------------------------------------
    def __init__(self, parent):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.init_volume_tools()
        self.init_resample_tools()
        self.init_fiducial_registration()
        self.init_rigid_registration()

    def init_volume_tools(self):
        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputSelector.addEnabled = False
        self.inputSelector.renameEnabled = True
        self.inputSelector.noneEnabled = True
        self.inputSelector.setMRMLScene(slicer.mrmlScene)
        self.inputSelector.connect("currentNodeChanged(bool)", self.click_input_selector)
        self.inputSelector.setToolTip("Select an existing input volume. If the volume's name start with numbers followed by an 'L' or an 'R', the side will be automatically selected.")
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Icons/fit.png'
        icon = qt.QPixmap(path).scaled(qt.QSize(16, 16), qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
        self.fitAllButton = qt.QToolButton()
        self.fitAllButton.setIcon(qt.QIcon(icon))
        self.fitAllButton.setFixedHeight(24)
        self.fitAllButton.enabled = False
        self.fitAllButton.setToolTip("Fit all Slice Viewers to match the extent of the lowest non-Null volume layer.")
        self.fitAllButton.connect('clicked(bool)', self.click_fit_all_views)
        self.leftBoneCheckBox = qt.QCheckBox("Left Temporal Bone")
        self.leftBoneCheckBox.checked = False
        self.leftBoneCheckBox.connect('toggled(bool)', self.click_left_bone)
        self.rightBoneCheckBox = qt.QCheckBox("Right Temporal Bone")
        self.rightBoneCheckBox.checked = False
        self.rightBoneCheckBox.connect('toggled(bool)', self.click_right_bone)
        self.movingSelector = slicer.qMRMLNodeComboBox()
        self.movingSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.movingSelector.setMRMLScene(slicer.mrmlScene)
        self.movingSelector.addEnabled = False
        self.movingSelector.renameEnabled = True
        self.movingSelector.noneEnabled = False
        self.movingSelector.removeEnabled = True
        self.movingSelector.enabled = False
        self.movingSelector.connect("currentNodeChanged(bool)", self.click_moving_selector)
        self.clearMarkupsFromSceneButton = qt.QCheckBox("Clear All Markups When Loading New Input Volume")

    def init_resample_tools(self):
        self.resampleInfoLabel = qt.QLabel("Load in a sample to enable spacing resample.")
        self.resampleInfoLabel.setWordWrap(True)
        self.resamplePresetBox = qt.QComboBox()
        self.resamplePresetBox.setFixedHeight(34)
        for i in supportedResamplePresets: self.resamplePresetBox.addItem(i["title"])
        self.resampleSpacingXBox = InterfaceTools.build_spin_box(1, 9999)
        self.resampleSpacingYBox = InterfaceTools.build_spin_box(1, 9999)
        self.resampleSpacingZBox = InterfaceTools.build_spin_box(1, 9999)
        self.resampleInterpolation = qt.QComboBox()
        for i in supportedResampleInterpolations: self.resampleInterpolation.addItem(i["title"])
        self.resampleInterpolation.currentIndex = 2
        self.resampleButton = qt.QPushButton("Resample Output to New Volume")
        self.resampleButton.setFixedHeight(24)
        self.resampleButton.connect('clicked(bool)', self.click_resample_volume)

    def init_fiducial_registration(self):
        self.fiducialTabs = qt.QTabWidget()
        self.fiducialTabs.setIconSize(qt.QSize(16, 16))
        self.fiducialTabs.connect('currentChanged(int)', self.click_fiducial_tab)
        self.fiducialApplyButton = qt.QPushButton("Apply")
        self.fiducialApplyButton.connect('clicked(bool)', self.click_fiducial_apply)
        self.fiducialApplyButton.enabled = False
        self.fiducialRevertButton = qt.QPushButton("Revert")
        self.fiducialRevertButton.setFixedWidth(60)
        self.fiducialRevertButton.connect('clicked(bool)', self.click_fiducial_revert)
        self.fiducialRevertButton.enabled = False
        self.fiducialAtlasOverlay = qt.QCheckBox("Atlas Overlay")
        self.fiducialAtlasOverlay.connect('toggled(bool)', self.click_fiducial_overlay)
        self.fiducialHardenButton = qt.QPushButton("Harden")
        self.fiducialHardenButton.connect('clicked(bool)', self.click_fiducial_harden)
        self.fiducialHardenButton.enabled = False
        self.fiducialPlacer = slicer.qSlicerMarkupsPlaceWidget()
        self.fiducialPlacer.buttonsVisible = False
        self.fiducialPlacer.placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceSingleMarkup
        self.fiducialPlacer.setMRMLScene(slicer.mrmlScene)
        self.fiducialPlacer.placeButton().show()
        self.fiducialPlacer.connect('activeMarkupsFiducialPlaceModeChanged(bool)', self.click_fiducial_placement)

    def init_rigid_registration(self):
        self.rigidStatus = qt.QLabel("Status:")
        p = qt.QPalette()
        p.setColor(qt.QPalette.WindowText, qt.Qt.gray)
        self.rigidStatus.setPalette(p)
        self.rigidProgress = qt.QProgressBar()
        self.rigidProgress.minimum = 0
        self.rigidProgress.maximum = 100
        self.rigidProgress.value = 0
        self.rigidProgress.visible = False
        self.rigidApplyButton = qt.QPushButton("Apply\n Rigid Registration")
        self.rigidApplyButton.connect('clicked(bool)', self.click_rigid_apply)

    # main ui layout building ------------------------------------------------------------------------------
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.sectionsList.append(self.build_volume_tools())
        self.sectionsList.append(self.build_resample_tools())
        self.sectionsList.append(self.build_fiducial_registration())
        self.sectionsList.append(self.build_rigid_registration())
        for s in self.sectionsList: self.layout.addWidget(s)
        self.layout.addStretch()
        self.update_slicer_view()

        # testing TODO remove
        # slicer.mrmlScene.Clear()
        # path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Atlases/1512R_Clinical_Aligned_Test_Input.nrrd"
        # node = slicer.util.loadVolume(path, returnNode=True)[1]
        # self.inputSelector.setCurrentNode(node)
        # end testing area

    def build_volume_tools(self):
        section = InterfaceTools.build_dropdown("Volume Tools")
        layout = qt.QFormLayout(section)
        label = qt.QLabel("Select an input volume to begin, then ensure the correct side is selected.")
        label.setWordWrap(True)
        layout.addRow(label)
        layout.addRow(self.clearMarkupsFromSceneButton)
        box = qt.QHBoxLayout()
        box.addWidget(self.inputSelector)
        box.addWidget(self.fitAllButton)
        layout.addRow("Input Volume: ", box)
        sideSelection = qt.QHBoxLayout()
        sideSelection.addWidget(self.leftBoneCheckBox)
        sideSelection.addWidget(self.rightBoneCheckBox)
        layout.addRow("Side Selection: ", sideSelection)
        label = qt.QLabel("A moving volume is generated from the input and displayed on the top three views. It will update as transforms are applied.")
        label.setWordWrap(True)
        layout.addRow(label)
        layout.addRow("Moving Volume: ", self.movingSelector)
        layout.setMargin(10)
        return section

    def build_resample_tools(self):
        section = InterfaceTools.build_dropdown("Spacing Resample Tools", disabled=True)
        # presets
        presets = qt.QWidget()
        layout = qt.QVBoxLayout(presets)
        layout.addWidget(self.resamplePresetBox)
        layout.setMargin(10)
        # manual
        manual = qt.QWidget()
        layout = qt.QHBoxLayout(manual)
        def label(t):
            l = qt.QLabel(t)
            l.setAlignment(qt.Qt.AlignCenter)
            return l
        layout.addWidget(label("X:"))
        layout.addWidget(self.resampleSpacingXBox)
        layout.addWidget(qt.QLabel("um"))
        layout.addWidget(label("Y:"))
        layout.addWidget(self.resampleSpacingYBox)
        layout.addWidget(qt.QLabel("um"))
        layout.addWidget(label("Z:"))
        layout.addWidget(self.resampleSpacingZBox)
        layout.addWidget(qt.QLabel("um"))

        self.resampleTabBox = qt.QTabWidget()
        self.resampleTabBox.addTab(presets, "Presets")
        self.resampleTabBox.addTab(manual, "Manual")

        grid = qt.QGridLayout()
        grid.addWidget(qt.QLabel("Interpolation Mode:"), 0, 0, 1, 1)
        grid.addWidget(self.resampleInterpolation, 0, 1, 1, 1)
        grid.addWidget(self.resampleButton, 0, 2, 1, 2)

        layout = qt.QVBoxLayout(section)
        layout.addWidget(self.resampleInfoLabel)
        layout.addWidget(self.resampleTabBox)
        layout.addLayout(grid)
        layout.setMargin(10)
        return section

    def build_fiducial_registration(self):
        section = InterfaceTools.build_dropdown("Fiducial Registration", disabled=True)
        layout = qt.QVBoxLayout(section)
        layout.addWidget(qt.QLabel("Set at least 3 fiducials. Setting more yields better results."))
        layout.addWidget(self.fiducialTabs)
        row = qt.QHBoxLayout()
        row.addWidget(self.fiducialApplyButton)
        row.addWidget(self.fiducialRevertButton)
        row.addWidget(self.fiducialAtlasOverlay)
        row.addWidget(self.fiducialHardenButton)
        layout.addLayout(row)
        layout.setMargin(10)
        return section

    def build_rigid_registration(self):
        section = InterfaceTools.build_dropdown("Rigid Registration", disabled=True)
        # row = qt.QHBoxLayout()
        # row.addWidget(qt.QLabel("Parameters: Elastix Rigid Registration"))
        # row.addWidget(self.rigidStatus)
        layout = qt.QVBoxLayout(section)
        # layout.addLayout(row)
        layout.addWidget(qt.QLabel("Parameters: Elastix Rigid Registration"))
        layout.addWidget(self.rigidStatus)
        layout.addWidget(self.rigidProgress)
        layout.addWidget(self.rigidApplyButton)
        layout.setMargin(10)
        return section

    # state checking ------------------------------------------------------------------------------
    def check_input_complete(self):
        if self.inputSelector.currentNode() is not None and (self.leftBoneCheckBox.isChecked() or self.rightBoneCheckBox.isChecked()):
            self.finalize_input()
            self.update_slicer_view()
            self.click_fit_all_views()
            self.update_sections_enabled(enabled=True)
        else:
            self.update_sections_enabled(enabled=False)

    def finalize_input(self):
        side_indicator = 'R' if self.rightBoneCheckBox.isChecked() else 'L'
        # check if side has been switched
        if self.atlasNode is not None and not self.atlasNode.GetName().startswith('Atlas_' + side_indicator):
            self.atlasNode = self.atlasFiducialNode = self.inputFiducialNode = None
        if self.clearMarkupsFromSceneButton.isChecked(): DeepLearningPreProcessModuleLogic.clear_all_markups_from_scene()
        # check if we need an atlas imported
        # if self.atlasNode is None or True:
        if True:
            self.atlasNode, self.atlasFiducialNode, self.maskNode = DeepLearningPreProcessModuleLogic().load_atlas_and_fiducials_and_mask(side_indicator)
            self.inputFiducialNode, self.fiducialSet = DeepLearningPreProcessModuleLogic().initialize_fiducial_set(self.atlasFiducialNode, self.fiducialPlacer, name=self.inputSelector.currentNode().GetName())
            self.fiducialTabs.clear()
            for f in self.fiducialSet:
                tab, f["table"] = InterfaceTools.build_fiducial_tab(f, self.click_fiducial_set_button, self.click_fiducial_clear_button)
                self.fiducialTabs.addTab(tab, f["label"])
        # set spacing
        spacing = DeepLearningPreProcessModuleLogic().get_um_spacing(self.inputSelector.currentNode().GetSpacing())
        self.resampleInfoLabel.text = "The input volume was imported with a spacing of (X: " + str(spacing[0]) + "um,  Y: " + str(spacing[1]) + "um,  Z: " + str(spacing[2]) + "um)"

    def initialize_moving_volume(self):
        node = slicer.vtkMRMLScalarVolumeNode()
        current = self.inputSelector.currentNode()
        node.Copy(current)
        node.SetName(current.GetName() + ' [MOVING]')
        slicer.mrmlScene.AddNode(node)
        self.movingSelector.setCurrentNode(node)
        self.movingSelector.enabled = True
        spacing = DeepLearningPreProcessModuleLogic().get_um_spacing(node.GetSpacing())
        self.resampleSpacingXBox.value, self.resampleSpacingYBox.value, self.resampleSpacingZBox.value = spacing[0], spacing[1], spacing[2]

    def process_transform(self, function, corresponding_button=None, set_moving_volume=False):
        try:
            slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
            if corresponding_button is not None: corresponding_button.enabled = False
            output = function()
            if set_moving_volume: self.movingSelector.setCurrentNode(output)
        except Exception as e:
            self.update_rigid_progress("Error: {0}".format(e))
            import traceback
            traceback.print_exc()
        finally:
            slicer.app.restoreOverrideCursor()
            if corresponding_button is not None: corresponding_button.enabled = corresponding_button.visible = True
            self.update_slicer_view()

    # UI updating ------------------------------------------------------------------------------
    def update_sections_enabled(self, enabled):
        self.fitAllButton.enabled = enabled
        self.movingSelector.enabled = enabled
        for i in range(1, len(self.sectionsList)):
            self.sectionsList[i].enabled = enabled
            # self.sectionsList[i].collapsed = not enabled

    def update_slicer_view(self):
        slicer.app.layoutManager().setLayout(21)
        moving = self.intermediateNode.GetID() if self.intermediateNode is not None else self.movingSelector.currentNode().GetID() if self.movingSelector.currentNode() is not None else None
        atlas = overlay = self.atlasNode.GetID() if self.atlasNode is not None else None
        overlayOpacity = 0.4 if self.fiducialAtlasOverlay.isChecked() else 0
        for c in ['Red', 'Yellow', 'Green']:
            slicer.app.layoutManager().sliceWidget(c).sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(moving)
            slicer.app.layoutManager().sliceWidget(c).sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(overlay)
            slicer.app.layoutManager().sliceWidget(c).sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(overlayOpacity)
            slicer.app.layoutManager().sliceWidget(c + '+').sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(atlas)

    def update_fiducial_table(self):
        completed = 0
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Icons/'
        for i in range(0, len(self.fiducialSet)):
            if self.fiducialSet[i]['input_indices'] != [0, 0, 0]: completed += 1
            if self.fiducialPlacer.placeModeEnabled and i == self.fiducialTabs.currentIndex: icon = qt.QIcon(path + 'fiducial.png')
            else: icon = qt.QIcon(path + 'check.png') if self.fiducialSet[i]['input_indices'] != [0, 0, 0] else qt.QIcon()
            self.fiducialTabs.setTabIcon(i, icon)
            for j in (range(0, 3)): self.fiducialSet[i]["table"].item(0, j).setText('%.3f' % self.fiducialSet[i]["input_indices"][j])
        self.fiducialApplyButton.enabled = True if completed >= 3 else False

    def update_fiducial_buttons(self):
        condition = self.intermediateNode is not None
        self.fiducialHardenButton.enabled = condition
        self.fiducialRevertButton.enabled = condition

    def update_rigid_progress(self, text):
        print(text)
        self.rigidStatus.text = 'Status: ' + ((text[:60] + '..') if len(text) > 60 else text)
        progress = None
        if text.startswith('Register volumes'): progress = 1
        elif text.startswith('-fMask'): progress = 3
        elif text.startswith('Reading images'): progress = 7
        elif text.startswith('Time spent in resolution 0'): progress = 14
        elif text.startswith('Time spent in resolution 1'): progress = 40
        elif text.startswith('Time spent in resolution 2'): progress = 60
        elif text.startswith('Time spent in resolution 3'): progress = 80
        elif text.startswith('Applying final transform'): progress = 85
        elif text.startswith('Time spent on saving the results'): progress = 90
        elif text.startswith('Generate output'): progress = 93
        elif text.startswith('Reading input image'): progress = 94
        elif text.startswith('Resampling image and writing to disk'): progress = 96
        elif text.startswith('Registration is completed'): progress = 100
        if progress is not None: self.rigidProgress.value = progress
        if progress is 100:
            self.rigidProgress.visible = False
            p = qt.QPalette()
            p.setColor(qt.QPalette.WindowText, qt.Qt.green)
            self.rigidStatus.setPalette(p)
        slicer.app.processEvents()  # force update

    # ui button actions ------------------------------------------------------------------------------
    def click_input_selector(self, validity):
        if not validity and self.inputSelector.currentNode() is None: return self.update_sections_enabled(enabled=False)
        # check for auto side selection
        s = re.search("\d+\w_", self.inputSelector.currentNode().GetName())
        if s is not None:
            s = s.group(0)[-2]
            if s == 'R': self.click_right_bone(force=True)
            elif s == 'L': self.click_left_bone(force=True)
        self.initialize_moving_volume()
        self.check_input_complete()

    def click_fit_all_views(self):
        logic = slicer.app.layoutManager().mrmlSliceLogics()
        for i in range(logic.GetNumberOfItems()): logic.GetItemAsObject(i).FitSliceToAll()
        if self.fiducialSet is not None and len(self.fiducialSet) > 0: self.click_fiducial_tab(self.fiducialTabs.currentIndex)

    def click_right_bone(self, force=False):
        if force: self.rightBoneCheckBox.setChecked(True)
        if self.rightBoneCheckBox.isChecked(): self.leftBoneCheckBox.setChecked(False)
        self.check_input_complete()

    def click_left_bone(self, force=False):
        if force: self.leftBoneCheckBox.setChecked(True)
        if self.leftBoneCheckBox.isChecked(): self.rightBoneCheckBox.setChecked(False)
        self.check_input_complete()

    def click_moving_selector(self, validity):
        if validity: self.update_slicer_view()

    def click_resample_volume(self):
        def function():
            if self.resampleTabBox.currentIndex == 0: spacing = supportedResamplePresets[self.resamplePresetBox.currentIndex]['value']
            else: spacing = [self.resampleSpacingXBox.value, self.resampleSpacingYBox.value, self.resampleSpacingZBox.value]
            spacing = [float(i)/1000 for i in spacing]
            return DeepLearningPreProcessModuleLogic().pull_node_resample_push(self.movingSelector.currentNode(), spacing, supportedResampleInterpolations[self.resampleInterpolation.currentIndex]['value'])
        self.process_transform(function, set_moving_volume=True)
        # TODO renaming to have number

    def click_fiducial_tab(self, index):
        if self.fiducialPlacer.placeModeEnabled: self.fiducialPlacer.setPlaceModeEnabled(False)
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

    def click_fiducial_clear_button(self, fiducial):
        for i in range(0, self.inputFiducialNode.GetNumberOfFiducials()):
            if self.inputFiducialNode.GetNthFiducialLabel(i) == fiducial["label"]:
                self.inputFiducialNode.RemoveMarkup(i)
                break
        fiducial["input_indices"] = [0, 0, 0]
        self.update_fiducial_table()

    def click_fiducial_placement(self, placing):
        if placing: self.fiducialTabsLastIndex = self.fiducialTabs.currentIndex
        if not placing and self.fiducialTabsLastIndex == self.fiducialTabs.currentIndex:
            self.fiducialTabsLastIndex = None
            fiducial = self.fiducialSet[self.fiducialTabs.currentIndex]
            nodeIndex = self.inputFiducialNode.GetNumberOfFiducials() - 1
            # self.inputFiducialNode.GetNthDisplayNode(nodeIndex).SetColor(0, 1, 0)
            self.inputFiducialNode.SetNthFiducialLabel(nodeIndex, fiducial["label"])
            self.inputFiducialNode.GetNthFiducialPosition(nodeIndex, fiducial["input_indices"])
        self.update_fiducial_table()

    def click_fiducial_apply(self):
        def function():
            if self.intermediateNode is None:
                self.intermediateNode = slicer.vtkMRMLScalarVolumeNode()
                slicer.mrmlScene.AddNode(self.intermediateNode)
            self.intermediateNode.Copy(self.inputSelector.currentNode())
            self.intermediateNode.SetName(self.movingSelector.currentNode().GetName() + " +Fiducial")
            self.intermediateNode = DeepLearningPreProcessModuleLogic().apply_fiducial_registration(self.intermediateNode, self.atlasFiducialNode, self.inputFiducialNode)
            self.update_fiducial_buttons()
        self.process_transform(function, corresponding_button=self.fiducialApplyButton)

    def click_fiducial_revert(self):
        slicer.mrmlScene.RemoveNode(self.intermediateNode)
        self.intermediateNode = None
        self.update_fiducial_buttons()
        self.update_slicer_view()

    def click_fiducial_overlay(self):
        self.update_slicer_view()

    def click_fiducial_harden(self):
        def function():
            output = DeepLearningPreProcessModuleLogic().harden_fiducial_registration(self.intermediateNode)
            self.intermediateNode = None
            self.update_fiducial_buttons()
            return output
        self.process_transform(function, set_moving_volume=True)

    def click_rigid_apply(self):
        def function():
            p = qt.QPalette()
            p.setColor(qt.QPalette.WindowText, qt.Qt.gray)
            self.rigidStatus.setPalette(p)
            self.rigidProgress.value = 0
            self.rigidProgress.visible = True
            self.rigidApplyButton.visible = False
            return DeepLearningPreProcessModuleLogic().apply_rigid_registration(atlas_node=self.atlasNode,
                                                                                moving_node=self.movingSelector.currentNode(),
                                                                                mask_node=self.maskNode,    # TODO add checkbox
                                                                                log_callback=self.update_rigid_progress)
        self.process_transform(function, corresponding_button=self.rigidApplyButton, set_moving_volume=True)

    # TODO remove
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
    def clear_all_markups_from_scene():
        for n in slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode"): slicer.mrmlScene.RemoveNode(n)

    @staticmethod
    def initialize_fiducial_set(atlas_fiducial_node, fiducial_placer, name):
        fiducial_set = []
        for i in range(0, atlas_fiducial_node.GetNumberOfFiducials()):
            f = {'label': atlas_fiducial_node.GetNthFiducialLabel(i), 'table': None, 'input_indices': [0, 0, 0], 'atlas_indices': [0, 0, 0]}
            atlas_fiducial_node.GetNthFiducialPosition(i, f['atlas_indices'])
            fiducial_set.append(f)
        inputFiducialNode = slicer.vtkMRMLMarkupsFiducialNode()
        inputFiducialNode.SetName(name + ' Input Fiducials')
        inputFiducialNode.SetLocked(True)  # TODO remove and implement dragging node
        slicer.mrmlScene.AddNode(inputFiducialNode)
        inputFiducialNode.GetDisplayNode().SetColor(0.1, 0.7, 0.1)
        fiducial_placer.setCurrentNode(inputFiducialNode)
        return inputFiducialNode, fiducial_set

    @staticmethod
    def load_atlas_and_fiducials_and_mask(side_indicator):
        framePath = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Atlases/"
        atlasNode = slicer.util.loadVolume(framePath + 'Atlas_' + side_indicator + '.mha', returnNode=True)[1]
        atlasNode.HideFromEditorsOn()
        atlasFiducialNode = slicer.util.loadMarkupsFiducialList(framePath + 'Fiducial_' + side_indicator + '.fcsv', returnNode=True)[1]
        atlasFiducialNode.SetName('Atlas_' + side_indicator + ' Fiducials')
        atlasFiducialNode.SetLocked(True)
        atlasFiducialNode.HideFromEditorsOn()
        maskNode = slicer.util.loadVolume(framePath + 'CochleaRegistrationMask_' + side_indicator + '.nrrd', returnNode=True)[1]
        return atlasNode, atlasFiducialNode, maskNode

    @staticmethod
    def get_um_spacing(node):
        return [int(s*1000) for s in node]

    @staticmethod
    def resample_image(image, spacing, interpolation):
        oldSpacing = [float("%.3f" % f) for f in image.GetSpacing()]
        oldSize = image.GetSize()
        newSize = [int(a * (b / c)) for a, b, c in zip(oldSize, oldSpacing, spacing)]
        resampler = sitk.ResampleImageFilter()
        resampler.SetInterpolator(interpolation)
        resampler.SetOutputDirection(image.GetDirection())
        resampler.SetOutputOrigin(image.GetOrigin())
        resampler.SetOutputSpacing(spacing)
        resampler.SetSize(newSize)
        resampledImage = resampler.Execute(image)
        return resampledImage

    @staticmethod
    def pull_node_resample_push(node, spacing_in_um, interpolation):
        image = sitku.PullVolumeFromSlicer(node.GetID())
        resampledImage = DeepLearningPreProcessModuleLogic().resample_image(image, spacing_in_um, interpolation)
        resampledNode = sitku.PushVolumeToSlicer(resampledImage, None, node.GetName() + " +Resampled" + str(spacing_in_um) + '', "vtkMRMLScalarVolumeNode")
        return resampledNode

    @staticmethod
    def apply_fiducial_registration(moving_node, atlas_fiducial_node, input_fiducial_node):
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
        for f in range(0, trimmed_atlas_fiducial_node.GetNumberOfFiducials()): trimmed_atlas_fiducial_node.SetNthFiducialVisibility(f, False)
        # process
        transform = slicer.vtkMRMLTransformNode()
        slicer.mrmlScene.AddNode(transform)
        output = slicer.cli.run(slicer.modules.fiducialregistration, None, wait_for_completion=True, parameters={
            'fixedLandmarks'   : trimmed_atlas_fiducial_node.GetID(),
            'movingLandmarks'  : input_fiducial_node.GetID(),
            'transformType'    : 'Rigid',
            "saveTransform"    : transform.GetID()
        })
        print(output)
        moving_node.ApplyTransform(transform.GetTransformToParent())
        # clean up
        # slicer.mrmlScene.RemoveNode(transform)
        slicer.mrmlScene.RemoveNode(trimmed_atlas_fiducial_node)
        return moving_node

    @staticmethod
    def harden_fiducial_registration(transformed_node):
        transformed_node.HardenTransform()
        return transformed_node

    @staticmethod
    def apply_rigid_registration(atlas_node, moving_node, mask_node, log_callback):
        # transform_node = slicer.vtkMRMLTransformNode()
        # slicer.mrmlScene.AddNode(transform_node)
        logic = Elastix.ElastixLogic()
        logic.logStandardOutput = True
        logic.logCallback = log_callback
        logic.registerVolumes(
            fixedVolumeNode=atlas_node,
            movingVolumeNode=moving_node,
            parameterFilenames=logic.getRegistrationPresets()[1][5],
            outputVolumeNode=moving_node,
            # outputTransformNode=transform_node,
            fixedVolumeMaskNode=mask_node,
            movingVolumeMaskNode=mask_node
        )
        # moving_node.ApplyTransform(transform_node.GetTransformToParent())
        moving_node.SetName(moving_node.GetName() + " +Rigid")
        return moving_node

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

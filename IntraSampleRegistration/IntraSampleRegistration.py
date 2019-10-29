import qt
import slicer
import DeepLearningPreProcessModule
import Elastix
from slicer.ScriptedLoadableModule import *


# Interface tools
class InterfaceTools:
    def __init__(self, parent):
        pass

    @staticmethod
    def build_volume_selector(on_click):
        s = slicer.qMRMLNodeComboBox()
        s.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        s.addEnabled = False
        s.renameEnabled = s.noneEnabled = True
        s.setMRMLScene(slicer.mrmlScene)
        s.connect("currentNodeChanged(bool)", on_click)
        return s

    @staticmethod
    def build_text_item():
        i = qt.QTableWidgetItem("")
        i.setTextAlignment(qt.Qt.AlignCenter)
        return i

    @staticmethod
    def build_button(title, on_click):
        b = qt.QPushButton(title)
        b.connect('clicked(bool)', on_click)
        return b


class IntraSampleRegistrationState:
    INPUT = 1
    EXECUTION = 2
    FINISHED = 3


class RegistrationType:
    CUSTOM_ELASTIX = 1
    CUSTOM_BRAINS = 2


class PairStatus:
    LOADING = 1
    READY = 2
    PENDING = 3
    EXECUTING = 4
    COMPLETE = 5
    FAILED = 6


class Pair:
    def __init__(self, on_click):
        self.fixed = InterfaceTools.build_volume_selector(on_click)
        self.moving = InterfaceTools.build_volume_selector(on_click)
        self.status = PairStatus.LOADING

    def disable(self):
        self.fixed.enabled = self.moving.enabled = False

    def enable(self):
        self.fixed.enabled = self.moving.enabled = True

    def StatusString(self):
        if self.status == PairStatus.LOADING:
            n = 1 if self.fixed.currentNode() is not None else 0
            n += 1 if self.moving.currentNode() is not None else 0
            return str(n) + "/2"
        elif self.status == PairStatus.READY: return "Ready"
        elif self.status == PairStatus.PENDING: return "Pending"
        elif self.status == PairStatus.EXECUTING: return "Executing"
        elif self.status == PairStatus.COMPLETE: return "Complete"
        elif self.status == PairStatus.FAILED: return "Failed"
        return "0"


class IntraSampleRegistration(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Intra-sample Batch Registration"
        self.parent.categories = ["Otolaryngology"]
        self.parent.dependencies = []
        self.parent.contributors = ["HML/SKA Auditory Biophysics Lab at The University of Western Ontario"]
        self.parent.helpText = "" + self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This module was originally developed by Evan Simpson in the HML/SKA Auditory Biophysics Lab (Western University)."


class IntraSampleRegistrationWidget(ScriptedLoadableModuleWidget):
    # Data members ------------
    state = IntraSampleRegistrationState.INPUT
    registrationSteps = []
    volumePairs = []

    # Registration logic nodes
    elastixLogic = Elastix.ElastixLogic()
    brainsCliLogic = None

    # UI members -------------- (in order of appearance)
    processTable = None
    processTools = None
    volumeTable = None
    volumePairTools = None
    addButton = None
    removeButton = None
    executeButton = None
    saveButton = None
    progressBox = None
    currentlyRunningLabel = None
    currentProgressLabel = None
    progressBar = None
    cancelButton = None
    finishButton = None

    # initialization ------------------------------------------------------------------------------
    def __init__(self, parent):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    # UI build ------------------------------------------------------------------------------
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.layout.addLayout(self.build_process_setup())
        self.layout.addLayout(self.build_volume_pair_table())
        self.layout.addWidget(self.build_volume_pair_tools())
        self.layout.addWidget(self.build_progress())
        self.click_add_volume_pair()

    def build_process_setup(self):
        self.processTable = qt.QTableWidget(0, 1)
        self.processTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.processTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.processTable.horizontalHeader().hide()
        self.processTable.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)
        self.processTable.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
        self.processTable.setMaximumHeight(70)

        self.processTools = qt.QFrame()
        box = qt.QHBoxLayout(self.processTools)
        box.addWidget(InterfaceTools.build_button('Add Custom Elastix', lambda: self.click_add_registration_step(RegistrationType.CUSTOM_ELASTIX)))
        box.addWidget(InterfaceTools.build_button('Add Custom BRAINS', lambda: self.click_add_registration_step(RegistrationType.CUSTOM_BRAINS)))
        b = InterfaceTools.build_button('Clear', self.click_clear_registration_step)
        b.setFixedWidth(60)
        box.addWidget(b)
        box.setContentsMargins(0, 0, 0, 0)

        layout = qt.QFormLayout()
        layout.addRow("Registration Steps:", self.processTable)
        layout.addWidget(self.processTools)
        layout.setMargin(10)
        return layout

    def build_volume_pair_table(self):
        self.volumeTable = qt.QTableWidget(0, 3)
        self.volumeTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.volumeTable.setHorizontalHeaderLabels(["Fixed Volume", "Moving Volume", "Status"])
        self.volumeTable.verticalHeader().setFixedWidth(30)
        self.volumeTable.verticalHeader().setSectionResizeMode(qt.QHeaderView.Fixed)
        self.volumeTable.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)
        self.volumeTable.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.Stretch)
        self.volumeTable.setColumnWidth(2, 70)
        self.volumeTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.volumeTable.connect('itemSelectionChanged()', self.update_selection)
        layout = qt.QVBoxLayout()
        layout.addWidget(self.volumeTable)
        layout.setMargin(10)
        return layout

    def build_volume_pair_tools(self):
        self.addButton = qt.QPushButton("Add")
        self.addButton.setFixedSize(90, 36)
        self.addButton.connect('clicked(bool)', self.click_add_volume_pair)
        self.removeButton = qt.QPushButton("Remove")
        self.removeButton.setFixedSize(90, 36)
        self.removeButton.enabled = False
        self.removeButton.connect('clicked(bool)', self.click_remove_volume_pair)
        self.executeButton = qt.QPushButton("Execute")
        self.executeButton.setFixedHeight(36)
        self.executeButton.enabled = False
        self.executeButton.connect('clicked(bool)', self.click_execute)
        self.saveButton = qt.QPushButton("Save Moved\nVolume")
        self.saveButton.setFixedSize(90, 36)
        self.saveButton.enabled = False
        self.saveButton.connect('clicked(bool)', self.click_save)
        # FRAME
        self.volumePairTools = qt.QFrame()
        layout = qt.QHBoxLayout(self.volumePairTools)
        layout.addWidget(self.addButton)
        layout.addWidget(self.removeButton)
        layout.addWidget(self.executeButton)
        layout.addWidget(self.saveButton)
        layout.setContentsMargins(10, 0, 10, 20)
        return self.volumePairTools

    def build_progress(self):
        self.currentProgressLabel = qt.QLabel("Status:")
        self.currentlyRunningLabel = qt.QLabel("Parameters: Elastix Rigid Registration")
        self.progressBar = qt.QProgressBar()
        self.progressBar.minimum = 0
        self.progressBar.maximum = 100
        self.progressBar.value = 0
        self.progressBar.setFixedHeight(36)
        self.cancelButton = qt.QPushButton("Cancel Execution")
        self.cancelButton.connect('clicked(bool)', self.click_cancel)
        self.cancelButton.setFixedHeight(36)
        self.finishButton = qt.QPushButton("Finish")
        self.finishButton.visible = False
        self.finishButton.connect('clicked(bool)', self.click_finish)
        self.finishButton.setFixedHeight(36)
        # FRAME
        self.progressBox = qt.QFrame()
        self.progressBox.hide()
        row = qt.QHBoxLayout()
        row.addWidget(self.progressBar)
        row.addWidget(self.cancelButton)
        row.addWidget(self.finishButton)
        layout = qt.QVBoxLayout(self.progressBox)
        layout.addWidget(self.currentlyRunningLabel)
        layout.addWidget(self.currentProgressLabel)
        layout.addLayout(row)
        layout.setContentsMargins(10, 0, 10, 20)
        return self.progressBox

    # main updation ------------------------------------------------------------------------------
    def update_all(self):
        self.update_process_table()
        self.update_process_tools()
        self.update_volume_pair_table()
        self.update_volume_pair_tools()

    def update_process_tools(self):
        if self.state == IntraSampleRegistrationState.INPUT:
            self.processTools.show()
        elif self.state == IntraSampleRegistrationState.EXECUTION:
            self.processTools.hide()

    def update_process_table(self):
        for i, pair in enumerate(self.registrationSteps):
            if self.processTable.item(i, 0) is None: self.processTable.setItem(i, 0, InterfaceTools.build_text_item())
            text = ''
            if self.registrationSteps[i] is RegistrationType.CUSTOM_ELASTIX: text = 'Custom Elastix Registration'
            elif self.registrationSteps[i] is RegistrationType.CUSTOM_BRAINS: text = 'Custom BRAINS Registration'
            self.processTable.item(i, 0).setText(text)

    def update_volume_pair_tools(self):
        if self.state == IntraSampleRegistrationState.INPUT:
            self.volumePairTools.show()
            self.progressBox.hide()
            toExecute = sum(pair.status == PairStatus.READY for pair in self.volumePairs)
            self.executeButton.enabled = toExecute > 0
            self.executeButton.setText("Execute (" + str(toExecute) + " pair(s), " + str(len(self.registrationSteps)) + ' registration(s) each)')
            self.executeButton.enabled = True if (toExecute > 0 and len(self.registrationSteps) > 0) else False
            selection = self.volumeTable.selectionModel().selectedRows()
            self.removeButton.enabled = True if len(selection) > 0 else False
            self.saveButton.enabled = True if len(selection) == 1 and self.volumePairs[selection[0].row()].status == PairStatus.COMPLETE else False   # TODO add multi save
        elif self.state == IntraSampleRegistrationState.EXECUTION:
            self.volumePairTools.hide()
            self.progressBox.show()
            self.cancelButton.visible = True
            self.finishButton.visible = False
        elif self.state == IntraSampleRegistrationState.FINISHED:
            self.cancelButton.visible = False
            self.finishButton.visible = True

    def update_volume_pair_table(self):
        for i, pair in enumerate(self.volumePairs):
            self.update_row_status(pair)
            self.update_row(pair, i)

    def update_row_status(self, pair):
        if self.state == IntraSampleRegistrationState.INPUT:
            f, m = pair.fixed.currentNode(), pair.moving.currentNode()
            if f is None or m is None: pair.status = PairStatus.LOADING
            elif pair.status is not PairStatus.COMPLETE: pair.status = PairStatus.READY

    def update_row(self, pair, i):
        self.volumeTable.setCellWidget(i, 0, pair.fixed)
        self.volumeTable.setCellWidget(i, 1, pair.moving)
        if self.volumeTable.item(i, 2) is None: self.volumeTable.setItem(i, 2, InterfaceTools.build_text_item())
        self.volumeTable.item(i, 2).setText(pair.StatusString())

    def update_selection(self):
        rows = self.volumeTable.selectionModel().selectedRows()
        if len(rows) == 1:
            pair = self.volumePairs[rows[0].row()]
            f = pair.fixed.currentNode().GetID() if pair.fixed.currentNode() is not None else None
            m = pair.moving.currentNode().GetID() if pair.moving.currentNode() is not None else None
            DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.update_slicer_view(f, m, 0.4)
        self.update_volume_pair_tools()

    def update_progress(self, text=None, current_registration_step=None, progress=None):
        if text is not None:
            print(text)
            self.currentProgressLabel.text = 'Status: ' + ((text[:60] + '..') if len(text) > 60 else text)
            if progress is None: progress = DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.process_rigid_progress(text)

        if progress is not None:
            self.progressBar.value = progress
            executed = len([p for p in self.volumePairs if p.status in [PairStatus.EXECUTING, PairStatus.COMPLETE]])
            total = len([p for p in self.volumePairs if p.status == PairStatus.PENDING]) + executed
            self.progressBar.setFormat(str(progress) + '% (' + str(executed) + ' of ' + str(total) + ')')

        if current_registration_step is not None and self.state is not IntraSampleRegistrationState.FINISHED:
            registration = None
            if current_registration_step is RegistrationType.CUSTOM_ELASTIX: registration = 'Elastix'
            elif current_registration_step is RegistrationType.CUSTOM_BRAINS: registration = 'BRAINS'
            self.currentlyRunningLabel.text = 'Executing ' + registration + '...'
        elif self.state is IntraSampleRegistrationState.FINISHED:
            self.currentlyRunningLabel.text = 'Executing complete...'

        self.update_all()
        slicer.app.processEvents()

    # button actions --------------------------------------
    def click_add_registration_step(self, process):
        self.registrationSteps.append(process)
        self.processTable.insertRow(self.processTable.rowCount)
        self.update_all()

    def click_clear_registration_step(self):
        del self.registrationSteps[:]
        self.processTable.clear()
        self.processTable.setRowCount(0)
        self.update_all()

    def click_add_volume_pair(self):
        self.volumePairs.append(Pair(on_click=self.update_all))
        self.volumeTable.insertRow(self.volumeTable.rowCount)
        self.update_all()

    def click_remove_volume_pair(self):
        for i in reversed(self.volumeTable.selectionModel().selectedRows()):
            del self.volumePairs[i.row()]
            self.volumeTable.removeRow(i.row())
        self.update_all()

    def click_execute(self):
        self.state = IntraSampleRegistrationState.EXECUTION
        readyPairs = []
        # prep ready pairs
        for pair in self.volumePairs:
            if pair.status == PairStatus.READY:
                readyPairs.append(pair)
                pair.status = PairStatus.PENDING
            pair.disable()
        self.update_all()
        # execute
        def on_complete():
            self.state = IntraSampleRegistrationState.FINISHED
            self.update_progress()
        IntraSampleRegistrationLogic().execute_batch(self.elastixLogic, readyPairs, self.registrationSteps, self.update_progress, on_complete)

    def click_cancel(self):
        DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.attempt_abort_rigid_registration(self.elastixLogic)
        if self.brainsCliLogic is not None: self.brainsCliLogic.Cancel()
        self.click_finish()

    def click_finish(self):
        self.state = IntraSampleRegistrationState.INPUT
        for pair in self.volumePairs: pair.enable()
        self.update_all()

    def click_save(self):
        for i in self.volumeTable.selectionModel().selectedRows():
            DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.open_save_node_dialog(self.volumePairs[i.row()].moving.currentNode())


class IntraSampleRegistrationLogic(ScriptedLoadableModuleLogic):
    @staticmethod
    def execute_batch(elastix, pairs, registration_steps, update_progress, finish):
        for pair in pairs:
            pair.status = PairStatus.EXECUTING
            outputNode = pair.moving.currentNode()
            for registration in registration_steps:
                update_progress(current_registration_step=registration)
                if registration is RegistrationType.CUSTOM_ELASTIX:
                    outputNode = DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.apply_elastix_rigid_registration(
                        elastix=elastix,
                        atlas_node=pair.fixed.currentNode(),
                        moving_node=outputNode,
                        mask_node=None,
                        log_callback=update_progress)
                elif registration is RegistrationType.CUSTOM_BRAINS:
                    outputNode = IntraSampleRegistrationLogic.apply_brains_rigid_registration(
                        pair=pair,
                        moving_node=outputNode,
                        log_callback=update_progress
                    )
                    update_progress(progress=100)
            pair.moving.setCurrentNode(outputNode)
            pair.status = PairStatus.COMPLETE
        finish()

    @staticmethod
    def apply_brains_rigid_registration(moving_node, pair, log_callback):
        transform_node = slicer.vtkMRMLTransformNode()
        transform_node.SetName(moving_node.GetName() + ' BRAINS transform')
        slicer.mrmlScene.AddNode(transform_node)
        # TODO use runSync
        slicer.cli.run(slicer.modules.brainsfit, None, {
            'fixedVolume': pair.fixed.currentNode().GetID(),
            'movingVolume': moving_node.GetID(),
            'outputTransform': transform_node.GetID(),
            'transformType': 'Rigid',
            'samplingPercentage'    : 1.0,
            'initialTransformMode'  : 'off',
            'maskProcessingMode'    : 'NOMASK',  # TODO double check Masking = NOMASK
            'costMetric'            : 'NC',
            'numberOfIterations'    : 1000,   # TODO check if theres a max param
            'minimumStepLength'	    : 0.0000001,
            'maximumStepLength'     : 0.001,
            'skewScale'             : 1.0,
            'reproportionScale'     : 1.0,
            'relaxationFactor'      : 0.5,
            'translationScale'      : 1.0  # aka transform scale
        }, wait_for_completion=True)
        print('TRANSFORM GENERATED: ' + str(transform_node))
        moving_node.ApplyTransform(transform_node.GetTransformToParent())
        moving_node.HardenTransform()
        moving_node.SetName(moving_node.GetName() + " +BRAINS")
        return moving_node


class IntraSampleRegistrationTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_IntraSampleRegistration1()

    def test_IntraSampleRegistration1(self):
        self.delayDisplay("Starting the test")

import os
import unittest
import vtk
import qt
import ctk
import slicer
import DeepLearningPreProcessModule
from slicer.ScriptedLoadableModule import *
from Utilities.InterfaceTools import InterfaceTools


class PairStatus:
    LOADING = 1
    READY = 2
    PENDING = 3
    EXECUTING = 4
    COMPLETE = 5
    FAILED = 6


# TODO move to interfaceTools
def build_volume_selector(on_click):
    s = slicer.qMRMLNodeComboBox()
    s.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    s.addEnabled = False
    s.renameEnabled = s.noneEnabled = True
    s.setMRMLScene(slicer.mrmlScene)
    s.connect("currentNodeChanged(bool)", on_click)
    return s


# TODO move to interfaceTools
def build_text_item():
    i = qt.QTableWidgetItem("")
    i.setTextAlignment(qt.Qt.AlignCenter)
    return i


class Pair:
    def __init__(self, on_click):
        self.fixed = build_volume_selector(on_click)
        self.moving = build_volume_selector(on_click)
        # self.statusText =
        # self.progress =
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
        self.parent.title = "Intra-sample Registration"
        self.parent.categories = ["Otolaryngology"]
        self.parent.dependencies = []
        self.parent.contributors = ["Luke Helpard (Western University) and Evan Simpson (Western University)"]
        self.parent.helpText = "" + self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This file was originally developed by Luke Helpard and Evan Simpson at The University of Western Ontario in the HML/SKA Auditory Biophysics Lab."


class IntraSampleRegistrationState:
    INPUT = 1
    EXECUTION = 2


class IntraSampleRegistrationWidget(ScriptedLoadableModuleWidget):
    # UI members -------------- (in order of appearance)
    table = None
    toolBox = None
    toolLayout = None
    addButton = None
    removeButton = None
    executeButton = None
    saveButton = None
    progressBox = None
    progressStatus = None
    progressBar = None
    cancelButton = None
    finishButton = None

    # Data members ------------
    state = IntraSampleRegistrationState.INPUT
    pairs = []

    # initialization ------------------------------------------------------------------------------
    def __init__(self, parent):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    # UI build ------------------------------------------------------------------------------
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.layout.addLayout(self.build_table())
        self.layout.addWidget(self.build_tools())
        self.layout.addWidget(self.build_progress())
        # self.layout.addStretch()
        self.click_add()

    def build_table(self):
        # label = qt.QLabel("")   # TODO
        # label.setWordWrap(True)

        self.table = qt.QTableWidget(0, 3)
        self.table.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(["Fixed Volume", "Moving Volume", "Status"])
        self.table.verticalHeader().setFixedWidth(20)
        self.table.verticalHeader().setSectionResizeMode(qt.QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.Stretch)
        self.table.setColumnWidth(2, 70)
        self.table.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.table.connect('itemSelectionChanged()', self.update_selection)
        layout = qt.QVBoxLayout()
        # layout.addWidget(label)
        layout.addWidget(self.table)
        layout.setMargin(10)
        return layout

    def build_tools(self):
        self.addButton = qt.QPushButton("Add")
        self.addButton.setFixedWidth(90)
        self.removeButton = qt.QPushButton("Remove")
        self.addButton.connect('clicked(bool)', self.click_add)
        self.removeButton.setFixedWidth(90)
        self.removeButton.enabled = False
        self.removeButton.connect('clicked(bool)', self.click_remove)
        self.executeButton = qt.QPushButton("Execute")
        self.executeButton.enabled = False
        self.executeButton.connect('clicked(bool)', self.click_execute)
        self.saveButton = qt.QPushButton("Save")
        self.saveButton.setFixedWidth(60)
        self.saveButton.enabled = False
        self.saveButton.connect('clicked(bool)', self.click_save)

        self.toolBox = qt.QFrame()
        layout = qt.QHBoxLayout(self.toolBox)
        layout.addWidget(self.addButton)
        layout.addWidget(self.removeButton)
        layout.addWidget(self.executeButton)
        layout.addWidget(self.saveButton)
        layout.setContentsMargins(10, 0, 10, 20)
        return self.toolBox

    def build_progress(self):
        self.progressStatus = qt.QLabel("Status:")

        self.progressBar = qt.QProgressBar()
        self.progressBar.minimum = 0
        self.progressBar.maximum = 100
        self.progressBar.value = 0

        self.cancelButton = qt.QPushButton("Cancel Execution")
        self.cancelButton.connect('clicked(bool)', self.click_cancel)

        # self.finishButton = qt.QPushButton("Finish")
        # self.finishButton.visible = False
        # self.finishButton.connect('clicked(bool)', self.click_finish)

        self.progressBox = qt.QFrame()
        self.progressBox.hide()
        row = qt.QHBoxLayout()
        row.addWidget(self.progressBar)
        row.addWidget(self.cancelButton)
        # row.addWidget(self.finishButton)
        layout = qt.QVBoxLayout(self.progressBox)
        layout.addWidget(qt.QLabel("Parameters: Elastix Rigid Registration"))
        layout.addWidget(self.progressStatus)
        layout.addLayout(row)
        layout.setContentsMargins(10, 0, 10, 20)
        return self.progressBox

    # main updation ------------------------------------------------------------------------------
    def update_all(self):
        self.update_table()
        self.update_tools()

    def update_tools(self):
        if self.state == IntraSampleRegistrationState.INPUT:
            self.toolBox.show()
            self.progressBox.hide()
            toExecute = sum(pair.status == PairStatus.READY for pair in self.pairs)
            self.executeButton.enabled = toExecute > 0
            self.executeButton.setText("Execute (" + str(toExecute) + ")")
            self.executeButton.enabled = True if toExecute > 0 else False
            self.removeButton.enabled = True if len(self.table.selectedRanges()) > 0 and self.table.selectedRanges()[0].rowCount() > 0 else False
        elif self.state == IntraSampleRegistrationState.EXECUTION:
            self.toolBox.hide()
            self.progressBox.show()
            # TODO move update progress to here?

    def update_table(self):
        for i, pair in enumerate(self.pairs):
            self.update_row_status(pair)
            self.update_row(pair, i)

    def update_row_status(self, pair):
        if self.state == IntraSampleRegistrationState.INPUT:
            if pair.moving.currentNode() is None or pair.fixed.currentNode() is None: pair.status = PairStatus.LOADING
            if pair.moving.currentNode() is not None and pair.fixed.currentNode() is not None: pair.status = PairStatus.READY

    def update_row(self, pair, i):
        self.table.setCellWidget(i, 0, pair.fixed)
        self.table.setCellWidget(i, 1, pair.moving)
        if self.table.item(i, 2) is None: self.table.setItem(i, 2, build_text_item())
        self.table.item(i, 2).setText(pair.StatusString())

    def update_selection(self):
        rows = self.table.selectionModel().selectedRows()
        if len(rows) == 1:
            pair = self.pairs[rows[0].row()]
            f = pair.fixed.currentNode().GetID() if pair.fixed.currentNode() is not None else None
            m = pair.moving.currentNode().GetID() if pair.moving.currentNode() is not None else None
            DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.update_slicer_view(f, m, 0.4)
        self.update_tools()

    def update_progress(self, text=None):
        if text is not None:
            print(text)
            self.progressStatus.text = 'Status: ' + ((text[:60] + '..') if len(text) > 60 else text)
            progress = DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.process_rigid_progress(text)
            if progress is not None:
                self.progressBar.value = progress
                executing = len([p for p in self.pairs if p.status == PairStatus.EXECUTING])
                total = len([p for p in self.pairs if p.status in [PairStatus.COMPLETE, PairStatus.PENDING]]) + executing
                self.progressBar.setFormat(str(progress) + '% (' + str(executing) + ' of ' + str(total) + ')')
                # if progress is 100:
                #     self.rigidProgress.visible = False
                #     p = qt.QPalette()
                #     p.setColor(qt.QPalette.WindowText, qt.Qt.green)
                #     self.rigidStatus.setPalette(p)
        self.update_all()
        slicer.app.processEvents()

    # button actions --------------------------------------
    def click_add(self):
        self.pairs.append(Pair(on_click=self.update_all))
        self.table.insertRow(self.table.rowCount)
        self.update_all()

    def click_remove(self):
        for i in reversed(self.table.selectionModel().selectedRows()):
            del self.pairs[i]
            self.table.removeRow(i)
        self.update_all()

    def click_execute(self):
        self.state = IntraSampleRegistrationState.EXECUTION
        readyPairs = []
        for pair in self.pairs:
            if pair.status == PairStatus.READY:
                readyPairs.append(pair)
                pair.status = PairStatus.PENDING
            pair.disable()
        self.update_all()
        IntraSampleRegistrationLogic().execute_batch(readyPairs, self.update_progress)

    def click_cancel(self):
        # TODO
        self.state = IntraSampleRegistrationState.INPUT
        for pair in self.pairs: pair.enable()
        self.update_all()

    def click_finish(self):
        # TODO
        self.state = IntraSampleRegistrationState.INPUT
        for pair in self.pairs: pair.enable()
        self.update_all()

    def click_save(self):
        pass


class IntraSampleRegistrationLogic(ScriptedLoadableModuleLogic):
    @staticmethod
    def execute_batch(pairs, progress_updater):
        for pair in pairs:
            pair.status = PairStatus.EXECUTING
            progress_updater()
            DeepLearningPreProcessModule.DeepLearningPreProcessModuleLogic.apply_rigid_registration(
                atlas_node=pair.fixed.currentNode(),
                moving_node=pair.moving.currentNode(),
                mask_node=None,
                log_callback=progress_updater
            )
            pair.status = PairStatus.COMPLETE
            progress_updater()


class IntraSampleRegistrationTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_IntraSampleRegistration1()

    def test_IntraSampleRegistration1(self):
        self.delayDisplay("Starting the test")

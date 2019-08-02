import os
import unittest
import vtk
import qt
import ctk
import slicer
from slicer.ScriptedLoadableModule import *
from Utilities.InterfaceTools import InterfaceTools


# noinspection PyClassHasNoInit
class PairStatus:
    INITIALIZING = 0
    INITIALIZED = 1
    READY = 2
    PENDING = 3
    EXECUTING = 4
    COMPLETE = 5
    FAILED = 6


class Pair:
    moving = None

    def __init__(self):
        self.moving = None
        self.fixed = None
        self.status = PairStatus.INITIALIZING

    def StatusString(self):
        s = "0"
        if self.status == PairStatus.INITIALIZED: return "-"
        elif self.status == PairStatus.READY: return "Ready"
        elif self.status == PairStatus.PENDING: return "Pending"
        elif self.status == PairStatus.EXECUTING: return "Executing"
        elif self.status == PairStatus.COMPLETE: return "Complete"
        elif self.status == PairStatus.FAILED: return "Failed"
        return s


class IntraSampleRegistration(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Intra-sample Registration"
        self.parent.categories = ["Otolaryngology"]
        self.parent.dependencies = []
        self.parent.contributors = ["Luke Helpard (Western University) and Evan Simpson (Western University)"]
        self.parent.helpText = "" + self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This file was originally developed by Luke Helpard and Evan Simpson at The University of Western Ontario in the HML/SKA Auditory Biophysics Lab."


class IntraSampleRegistrationWidget(ScriptedLoadableModuleWidget):
    # UI members -------------- (in order of appearance)
    table = None
    addButton = None
    removeButton = None
    executeButton = None
    saveButton = None
    progressBar = None

    # Data members ------------
    pairs = [Pair()]

    # initialization ------------------------------------------------------------------------------
    def __init__(self, parent):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    # UI build ------------------------------------------------------------------------------
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.layout.addLayout(self.build_table())
        self.layout.addLayout(self.build_tools())
        self.layout.addStretch()
        self.check_state()

    def build_table(self):
        self.table = qt.QTableWidget(1, 3)
        self.table.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(["Fixed Volume", "Moving Volume", "Status"])
        self.table.verticalHeader().setFixedWidth(20)
        self.table.verticalHeader().setSectionResizeMode(qt.QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.Stretch)
        self.table.setColumnWidth(2, 70)
        # self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.table.connect('itemSelectionChanged()', self.check_state)

        layout = qt.QVBoxLayout()
        layout.addWidget(qt.QLabel("Insert description here"))
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

        layout = qt.QHBoxLayout()
        layout.addWidget(self.addButton)
        layout.addWidget(self.removeButton)
        layout.addWidget(self.executeButton)
        layout.addWidget(self.saveButton)
        layout.setContentsMargins(10, 0, 10, 20)
        return layout

    # state checking ------------------------------------------------------------------------------
    def check_state(self):
        self.update_table()
        self.update_tools()

    def update_table(self):
        self.table.setRowCount(len(self.pairs))
        for p in self.pairs:
            if p.status == PairStatus.INITIALIZING: self.initialize_table_row(p)
            self.update_table_row(p)

    def update_tools(self):
        selection = self.table.selectedRanges()
        if len(selection) == 0:
            self.removeButton.enabled = self.saveButton.enabled = False
        elif selection[0].rowCount() > 0:
            self.removeButton.enabled = True

    def update_table_row(self, pair):
        i = self.pairs.index(pair)
        self.table.cellWidget(i, 0).setCurrentNode(pair.fixed)
        self.table.cellWidget(i, 1).setCurrentNode(pair.moving)
        # self.table.item(i, 2).setText(pair.StatusString())
        self.table.item(i, 2).setText(pair.status)

    def initialize_table_row(self, pair):
        i = self.pairs.index(pair)
        def selector():
            s = slicer.qMRMLNodeComboBox()
            s.nodeTypes = ["vtkMRMLScalarVolumeNode"]
            s.addEnabled = s.noneEnabled = False
            s.renameEnabled = True
            s.setMRMLScene(slicer.mrmlScene)
            # s.connect("currentNodeChanged(bool)", self.click_input_selector)
            return s
        self.table.setCellWidget(i, 0, selector())
        self.table.setCellWidget(i, 1, selector())
        item = qt.QTableWidgetItem(pair.StatusString())
        item.setTextAlignment(qt.Qt.AlignCenter)
        self.table.setItem(i, 2, item)
        # pair.status = PairStatus.INITIALIZED
        pair.status = i

    # button actions --------------------------------------
    def click_add(self):
        self.pairs.append(Pair())
        self.check_state()

    def click_remove(self):
        selection = self.table.selectedRanges()[0]
        del self.pairs[max(selection.topRow(), 0) : selection.bottomRow()+1]
        if len(self.pairs) == 0: self.pairs.append(Pair())
        self.check_state()

    def click_execute(self):
        pass

    def click_save(self):
        pass


class IntraSampleRegistrationLogic(ScriptedLoadableModuleLogic):
    pass


class IntraSampleRegistrationTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_IntraSampleRegistration1()

    def test_IntraSampleRegistration1(self):
        self.delayDisplay("Starting the test")

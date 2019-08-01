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
    INITIALIZING=0
    INITIALIZED=1
    READY=2
    PENDING=3
    EXECUTING=4
    COMPLETE=5
    FAILED=6

class Pair:
    moving = None

    def __init__(self):
        self.moving = None
        self.fixed = None
        self.status = PairStatus.INITIALIZING

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
    pairs = []

    # initialization ------------------------------------------------------------------------------
    def __init__(self, parent):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    # UI build ------------------------------------------------------------------------------
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.layout.addLayout(self.build_table())
        self.layout.addLayout(self.build_tools())
        self.layout.addStretch()

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

        layout = qt.QVBoxLayout()
        layout.addWidget(qt.QLabel("Insert description here"))
        layout.addWidget(self.table)
        layout.setMargin(10)
        return layout

    def build_tools(self):
        self.addButton = qt.QPushButton("Add")
        self.addButton.setFixedWidth(90)
        self.addButton.connect('clicked(bool)', self.click_add)
        self.removeButton = qt.QPushButton("Remove")
        self.removeButton.setFixedWidth(90)
        self.removeButton.connect('clicked(bool)', self.click_remove)
        self.executeButton = qt.QPushButton("Execute")
        self.executeButton.connect('clicked(bool)', self.click_execute)
        self.saveButton = qt.QPushButton("Save")
        self.saveButton.setFixedWidth(60)
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
        pass

    def append_pair(self):
        self.pairs.append(Pair())

    def update_table(self):
        for p in self.pairs:
            if p.status == PairStatus.INITIALIZING:
                pass

    def update_tools(self):
        pass

    # button actions --------------------------------------
    def click_add(self):
        pass

    def click_remove(self):
        pass

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

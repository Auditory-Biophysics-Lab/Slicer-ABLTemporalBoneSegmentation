import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging


class SkullThicknessMapping(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Skull Thickness Mapping"
        self.parent.categories = ["Otolaryngology"]
        self.parent.dependencies = []
        self.parent.contributors = ["Evan Simpson (Western University)"]
        self.parent.helpText = "" + self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This file was originally developed by Evan Simpson at The University of Western Ontario in the HML/SKA Auditory Biophysics Lab."


class SkullThicknessMappingWidget(ScriptedLoadableModuleWidget):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)


class SkullThicknessMappingLogic(ScriptedLoadableModuleLogic):
    pass


class SkullThicknessMappingTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_SkullThicknessMapping1()

    def test_SkullThicknessMapping1(self):
        pass

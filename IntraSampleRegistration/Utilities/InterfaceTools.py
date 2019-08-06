import ctk
import slicer


class InterfaceTools:
    def __init__(self, parent):
        pass

    @staticmethod
    def build_volume_selector():
        s = slicer.qMRMLNodeComboBox()
        s.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        s.addEnabled = s.noneEnabled = False
        s.renameEnabled = True
        s.setMRMLScene(slicer.mrmlScene)
        # s.connect("currentNodeChanged(bool)", self.data_changed)
        return s

    @staticmethod
    def build_dropdown(title, disabled=False):
        d = ctk.ctkCollapsibleButton()
        d.text = title
        d.enabled = not disabled
        d.collapsed = disabled
        return d

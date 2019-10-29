import inspect

import ctk
import slicer
import numpy
import time
import qt
import vtk
from slicer.ScriptedLoadableModule import *


# Interface tools
class InterfaceTools:
    def __init__(self, parent):
        pass

    @staticmethod
    def build_dropdown(title, disabled=False):
        d = ctk.ctkCollapsibleButton()
        d.text = title
        d.enabled = not disabled
        d.collapsed = disabled
        return d

    @staticmethod
    def build_group(title):
        g = qt.QGroupBox(title)
        return g

    @staticmethod
    def build_volume_selector(on_click=None):
        s = slicer.qMRMLNodeComboBox()
        s.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        s.noneEnabled = True
        s.addEnabled = False
        s.renameEnabled = True
        s.setMRMLScene(slicer.mrmlScene)
        if on_click is not None: s.connect("currentNodeChanged(bool)", on_click)
        return s

    @staticmethod
    def build_model_selector(on_click=None):
        s = slicer.qMRMLNodeComboBox()
        s.nodeTypes = ["vtkMRMLModelNode"]
        s.addEnabled = False
        s.renameEnabled = s.noneEnabled = False  # True
        s.setMRMLScene(slicer.mrmlScene)
        if on_click is not None: s.connect("currentNodeChanged(bool)", on_click)
        return s


class HitPoint:
    pid = None
    point = None
    normal = [0.0, 0.0, 0.0]

    def __init__(self, pid, point):
        self.pid = pid
        self.point = point

# class Facet:
#     normal = None
#     center = None
#
#     def normal_inward(self): return self.normal
#     def normal_outward(self): return [-v for v in self.normal]
#
#     def __init__(self, c, n):
#         self.normal = n
#         self.center = c
#
#     def __repr__(self):
#         return str(self)
#
#     def __str__(self):
#         # return "\n  [Facet]" + " n:" + str(self.n) + "\n          v1:" + str(self.v1) + "\n          v2:" + str(self.v2) + "\n          v3:" + str(self.v3) + '\n'
#         return "\n  [Facet]" + " n:" + str(self.normal) + "\n          c:" + str(self.center)
#
#
# class Polygon:
#     normal = None
#     center = None
#     points = None
#
#     def normal_inward(self): return self.normal
#     def normal_outward(self): return [-v for v in self.normal]
#
#     def __init__(self, center, normal, points):
#         self.center = center
#         self.normal = normal
#         self.points = points
#
#     def __repr__(self):
#         return str(self)
#
#     def __str__(self):
#         # return "\n  [Facet]" + " n:" + str(self.n) + "\n          v1:" + str(self.v1) + "\n          v2:" + str(self.v2) + "\n          v3:" + str(self.v3) + '\n'
#         return "\n  [Facet]" + " normal:" + str(self.normal) + "\n          center:" + str(self.center) + "\n          points:" + str(self.points)
#
#
# class Intersection:
#     voxel = None
#     value = None
#
#     def __init__(self, voxel=None, value=None):
#         self.voxel = voxel
#         self.value = value
#


class SkullThicknessMapping(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Skull Thickness Mapping"
        self.parent.categories = ["Otolaryngology"]
        self.parent.dependencies = []
        self.parent.contributors = ["Evan Simpson (Western University)"]
        self.parent.helpText = "" + self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "This module was originally developed by Evan Simpson at The University of Western Ontario in the HML/SKA Auditory Biophysics Lab."


class SkullThicknessMappingWidget(ScriptedLoadableModuleWidget):
    # Data members --------------
    # TODO rename things
    processing = False
    volumeSelector = None
    polyData = None
    topLayerPolyData = None
    hitPointList = None
    modelNode = None

    # UI members --------------
    statusLabel = None
    infoLabel = None
    executeButton = None
    progressBar = None
    resultSection = None
    displayThicknessSelector = None
    displayFirstAirCellSelector = None

    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        for s in [
            self.build_input_tools(),
            self.build_configuration_tools(),
            self.build_execution_tools(),
            self.build_result_tools()
        ]: self.layout.addWidget(s)
        self.layout.addStretch()
        slicer.app.layoutManager().setLayout(16)
        SkullThicknessMappingLogic.reset_view()
        # TODO REMOVE TESTING
        slicer.mrmlScene.Clear()
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Sample/Images/1601L.img"
        node = slicer.util.loadVolume(path, returnNode=True)[1]

    # interface build ------------------------------------------------------------------------------
    def build_input_tools(self):
        section = InterfaceTools.build_dropdown("Input Tools")

        self.volumeSelector = InterfaceTools.build_volume_selector(on_click=self.update_input_tools)
        path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Icons/fit.png'
        icon = qt.QPixmap(path).scaled(qt.QSize(16, 16), qt.Qt.KeepAspectRatio, qt.Qt.SmoothTransformation)
        fitAllButton = qt.QToolButton()
        fitAllButton.setIcon(qt.QIcon(icon))
        fitAllButton.setFixedSize(50, 24)
        fitAllButton.setToolTip("Reset 3D view.")
        fitAllButton.connect('clicked(bool)', SkullThicknessMappingLogic.reset_view)
        box = qt.QHBoxLayout()
        box.addWidget(self.volumeSelector)
        box.addWidget(fitAllButton)
        self.infoLabel = qt.QLabel()
        self.infoLabel.setVisible(False)

        layout = qt.QFormLayout(section)
        layout.addRow("Input Volume: ", box)
        layout.addWidget(self.infoLabel)
        layout.setMargin(10)
        return section

    def build_configuration_tools(self):
        section = InterfaceTools.build_dropdown("Advanced Configuration Tools")

        layout = qt.QFormLayout(section)
        layout.setMargin(10)
        return section

    def build_execution_tools(self):
        section = InterfaceTools.build_group('Execution')

        self.executeButton = qt.QPushButton("Execute")
        self.executeButton.connect('clicked(bool)', self.process)
        self.progressBar = qt.QProgressBar()
        self.progressBar.minimum = 0
        self.progressBar.maximum = 100
        self.progressBar.value = 0
        self.progressBar.visible = False
        self.statusLabel = qt.QLabel("Status: ")
        self.statusLabel.visible = False

        layout = qt.QVBoxLayout(section)
        layout.addWidget(self.executeButton)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.statusLabel)
        layout.setMargin(10)
        return section

    def build_result_tools(self):
        self.resultSection = qt.QGroupBox('Results')
        self.resultSection.setVisible(False)

        self.displayThicknessSelector = qt.QRadioButton("Thickness")
        self.displayThicknessSelector.setChecked(True)
        self.displayFirstAirCellSelector = qt.QRadioButton("Distance To First Air-cell")

        box = qt.QVBoxLayout(self.resultSection)
        box.addWidget(self.displayThicknessSelector)
        box.addWidget(self.displayFirstAirCellSelector)
        box.setMargin(10)

        layout = qt.QFormLayout(self.resultSection)
        layout.addRow("Display: ", box)
        layout.setMargin(10)
        return self.resultSection

    # interface update ------------------------------------------------------------------------------
    def update_input_tools(self):
        if self.volumeSelector.currentNode() is not None:
            self.infoLabel.visible = True
            self.infoLabel.text = 'Dimensions: ' + str(self.volumeSelector.currentNode().GetImageData().GetDimensions())
        else:
            self.infoLabel.visible = False
            self.infoLabel.text = ''

    def update_status(self, text=None, progress=None):
        if self.processing:
            self.progressBar.visible = self.statusLabel.visible = True
            self.executeButton.visible = False
        else:
            self.progressBar.visible = False
            self.progressBar.value = 0
            self.executeButton.visible = True

        if progress is not None:
            self.progressBar.value = progress

        if text is not None:
            print(text)
            self.statusLabel.text = "Status: " + text
        slicer.app.processEvents()

    def process(self):
        self.processing = True
        # TODO REMOVE testing
        testingMethod = None
        if testingMethod == 1:
            slicer.mrmlScene.Clear()
            path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Sample/Images/1601L.img"
            node = slicer.util.loadVolume(path, returnNode=True)[1]
            self.volumeSelector.setCurrentNode(node)
        elif testingMethod == 2:
            slicer.mrmlScene.Clear()
            path = slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Resources/Sample/Shapes/sphere.obj"
            node = slicer.util.loadModel(path, returnNode=True)[1]
            self.polyData = node.GetPolyData()
            self.topLayerPolyData, self.hitPointList = SkullThicknessMappingLogic.rainfall_quad_cast(self.polyData, [500, 500, 500], self.update_status)
            self.modelNode = SkullThicknessMappingLogic.build_model(self.topLayerPolyData, self.update_status)
            SkullThicknessMappingLogic.ray_cast_color_thickness(self.polyData, self.topLayerPolyData, self.hitPointList, self.modelNode, [500, 500, 500], self.update_status)
        # TODO add param names
        if self.volumeSelector.currentNode() is not None and testingMethod is not 2:
            self.update_status(progress=0)
            SkullThicknessMappingLogic.reset_view()
            image = self.volumeSelector.currentNode()
            self.polyData = SkullThicknessMappingLogic.process_segmentation(image, self.update_status)
            self.topLayerPolyData, self.hitPointList = SkullThicknessMappingLogic.rainfall_quad_cast(self.polyData, image.GetImageData().GetDimensions(), self.update_status)
            self.modelNode = SkullThicknessMappingLogic.build_model(self.topLayerPolyData, self.update_status)
            SkullThicknessMappingLogic.ray_cast_color_thickness(self.polyData, self.topLayerPolyData, self.hitPointList, self.modelNode, image.GetImageData().GetDimensions(), self.update_status)
            self.update_status(progress=100)
        self.processing = False


class SkullThicknessMappingLogic(ScriptedLoadableModuleLogic):
    @staticmethod
    def sample_folder():
        return slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Sample/'

    @staticmethod
    def reset_view():
        m = slicer.app.layoutManager()
        w = m.threeDWidget(0)
        w.threeDView().lookFromViewAxis(2)
        c = w.threeDController()
        for i in xrange(12): c.zoomIn()

    @staticmethod
    def build_model(polydata, status):
        status(text="Rendering top layer...")
        modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        modelNode.SetAndObservePolyData(polydata)
        modelNode.CreateDefaultDisplayNodes()
        modelDisplayNode = modelNode.GetModelDisplayNode()
        modelDisplayNode.SetFrontfaceCulling(0)
        modelDisplayNode.SetBackfaceCulling(0)
        status(text="Top layer rendered...")
        return modelNode

    @staticmethod
    def ray_cast_color_thickness(poly_data, top_layer_poly_data, hit_point_list, model_node, dimensions, status):
        status(text="Building intersection object tree...")
        bspTree = vtk.vtkModifiedBSPTree()
        bspTree.SetDataSet(poly_data)
        bspTree.BuildLocator()

        status(text="Calculating thickness and rendering top layer color..."); startTime = time.time()
        colours = vtk.vtkUnsignedCharArray()
        colours.SetName('Thickness')
        # colours.SetNumberOfComponents(3)
        pointsOfIntersection, cellsOfIntersection = vtk.vtkPoints(), vtk.vtkIdList()
        for hitPoint in hit_point_list:
            stretchFactor = dimensions[0]
            start = [hitPoint.point[0] + hitPoint.normal[0]*stretchFactor, hitPoint.point[1] + hitPoint.normal[1]*stretchFactor, hitPoint.point[2] + hitPoint.normal[2]*stretchFactor]
            end = [hitPoint.point[0] - hitPoint.normal[0]*stretchFactor, hitPoint.point[1] - hitPoint.normal[1]*stretchFactor, hitPoint.point[2] - hitPoint.normal[2]*stretchFactor]
            # slicer.modules.markups.logic().AddFiducial(start[0], start[1], start[2])
            # slicer.modules.markups.logic().AddFiducial(end[0], end[1], end[2])
            # slicer.modules.markups.logic().AddFiducial(hitPoint.point[0], hitPoint.point[1], hitPoint.point[2])
            res = bspTree.IntersectWithLine(start, end, 0, pointsOfIntersection, cellsOfIntersection)
            if pointsOfIntersection.GetNumberOfPoints() < 2: continue
            p1, p2 = pointsOfIntersection.GetPoint(0), pointsOfIntersection.GetPoint(pointsOfIntersection.GetNumberOfPoints()-1)
            # p1, p2 = pointsOfIntersection.GetPoint(0), pointsOfIntersection.GetPoint(1)

            thickness = numpy.linalg.norm(numpy.array((p1[0], p1[1], p1[2])) - numpy.array((p2[0], p2[1], p2[2])))
            # thickness = numpy.abs(p1[0] - p2[1])
            # thickness = numpy.random.randint(0, 255)
            thickness = thickness*20
            # print('Point ' + str(i) + '(' + str(pointsOfIntersection.GetNumberOfPoints()) + ' hits) thickness: ' + str(thickness))
            colours.InsertTuple1(hitPoint.pid, thickness)

        top_layer_poly_data.GetPointData().SetScalars(colours)
        top_layer_poly_data.Modified()

        displayNode = model_node.GetDisplayNode()
        displayNode.SetActiveScalarName('Thickness')
        displayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeFileHotToColdRainbow.txt')
        displayNode.ScalarVisibilityOn()
        # displayNode.AutoScalarRangeOn()
        displayNode.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
        status(text="Finished thickness calculation in " + str("%.1f" % (time.time() - startTime)) + "s...")
        # TODO display on slice views

    @staticmethod
    def process_segmentation(image, status):
        # Fix Volume Orientation
        status(text="Rotating views to volume plane...")
        manager = slicer.app.layoutManager()
        for name in manager.sliceViewNames():
            widget = manager.sliceWidget(name)
            node = widget.mrmlSliceNode()
            node.RotateToVolumePlane(image)

        # Create segmentation
        status(text="Creating segmentation...")
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentationNode.CreateDefaultDisplayNodes()
        segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(image)
        segmentId = segmentationNode.GetSegmentation().AddEmptySegment("Bone")
        segmentationNode.GetSegmentation().GetSegment(segmentId).SetColor([0.9, 0.8, 0.7])

        # Create segment editor to get access to effects
        status(text="Starting segmentation editor...")
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        segmentEditorWidget.setSegmentationNode(segmentationNode)
        segmentEditorWidget.setMasterVolumeNode(image)

        # Thresholding
        status(text="Processing threshold segmentation...")
        segmentEditorWidget.setActiveEffectByName("Threshold")
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter("MinimumThreshold", "800")  # 1460 #1160 # 223
        effect.setParameter("MaximumThreshold", "3071")
        effect.self().onApply()

        # Smoothing
        status(text="Processing smoothing segmentation...")
        segmentEditorWidget.setActiveEffectByName("Smoothing")
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter("SmoothingMethod", "MORPHOLOGICAL_OPENING")
        effect.setParameter("KernelSizeMm", 0.5)
        effect.self().onApply()

        # Islands
        status(text="Processing island segmentation...")
        segmentEditorWidget.setActiveEffectByName("Islands")
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter("Operation", "KEEP_LARGEST_ISLAND")
        effect.setParameter("MinimumSize", 1000)
        effect.self().onApply()

        # Crop
        # status("Cropping segmentation...")
        # segmentEditorWidget.setActiveEffectByName("Scissors")
        # effect = segmentEditorWidget.activeEffect()
        # effect.setParameter("MinimumThreshold", "223")
        # effect.setParameter("MaximumThreshold", "3071")
        # effect.self().onApply()

        # Clean up
        status(text="Cleaning up...")
        segmentEditorWidget.setActiveEffectByName(None)
        slicer.mrmlScene.RemoveNode(segmentEditorNode)

        # Make segmentation results visible in 3D and set focal
        status(text="Rendering...")
        segmentationNode.CreateClosedSurfaceRepresentation()

        # Make sure surface mesh cells are consistently oriented
        status(text="Retrieving surface mesh...")
        polyData = segmentationNode.GetClosedSurfaceRepresentation(segmentId)
        return polyData


        # TODO remove (testing ray cast)
        status(text="Building intersection object tree...")
        # obbTree = vtk.vtkCellLocator()
        obbTree = vtk.vtkModifiedBSPTree()
        # obbTree = vtk.vtkOBBTree()     # 6 minutes for 1/4 of rays
        obbTree.SetDataSet(surfaceMesh)
        obbTree.BuildLocator()

        # TODO remove (testing ray cast)
        # status("Generating ray-casting...")
        # sourcePoint = [-100.0, 0.0, 0.0]
        # targetPoint = [100.0, 0.0, 0.0]
        # pointsOfIntersection = vtk.vtkPoints()
        # cellsOfIntersection = vtk.vtkIdList()
        # res = obbTree.IntersectWithLine(sourcePoint, targetPoint, pointsOfIntersection, cellsOfIntersection)
        # pointIds = vtk.vtkIdList()
        # surfaceMesh.GetCellPoints(cellsOfIntersection.GetId(0), pointIds)
        # pointList = [surfaceMesh.GetPoint(pointIds.GetId(i)) for i in xrange(pointIds.GetNumberOfIds())]
        # topLayerPoints = vtk.vtkPoints()
        # topLayerPolys = vtk.vtkCellArray()
        # cell = vtk.vtkTriangle()
        # ids = cell.GetPointIds()
        # for i, point in enumerate(pointList): ids.SetId(i, topLayerPoints.InsertNextPoint(point))
        # topLayerPolys.InsertNextCell(cell)

        # TODO remove (testing cell lookup)
        # cells = surfaceMesh.GetPolys()
        # points = surfaceMesh.GetPoints()
        # poly = vtk.vtkTriangle()
        # pointIds = vtk.vtkIdList()
        # cells.GetCell(cellsOfIntersection.GetId(0), pointIds)
        # # print(ids[0] + ' ' + ids[1] + ' ' + ids[2])
        # for i in xrange(pointIds.GetNumberOfIds()): print(points.GetId(i))
        # status("Finished attempt with resultant: " + str(pointsOfIntersection.GetNumberOfPoints()))

        # TODO remove (testing ray cast)
        # Generate 'rainfall' ray trajectories
        status(text="Generating rainfall ray trajectories...")
        r, a, s = image.GetImageData().GetDimensions()
        # rayEndTrajectories = [{'from': [-r, -a/2.0+(ai/2.0), -s/2.0+(si/2.0)], 'to': [r, -a/2.0+(ai/2.0), -s/2.0+(si/2.0)]} for ai in xrange(a*2) for si in xrange(s*2)]
        rayEndTrajectories = [{'from': [-r, -a/2.0+ai, -s/2.0+si], 'to': [r, -a/2.0+ai, -s/2.0+si]} for ai in xrange(a) for si in xrange(s)]
        # Cast rays
        status(text="Casting " + str(len(rayEndTrajectories)) + " rays..."); startTime = time.time()
        topLayerPoints, topLayerCells = vtk.vtkPoints(), vtk.vtkCellArray()
        pointsOfIntersection, cellsOfIntersection, topCellPointIds = vtk.vtkPoints(), vtk.vtkIdList(), vtk.vtkIdList()
        for trajectory in rayEndTrajectories:
            res = obbTree.IntersectWithLine(trajectory['from'], trajectory['to'], 0, pointsOfIntersection, cellsOfIntersection)  # change potentially
            if res == 0 or res != 0 and not -50 <= pointsOfIntersection.GetPoint(0)[0] < 0 : continue
            # topLayerPoints.InsertNextPoint(pointsOfIntersection.GetPoint(0))
            surfaceMesh.GetCellPoints(cellsOfIntersection.GetId(0), topCellPointIds)
            newCell = vtk.vtkTriangle()
            newCellPointIds = newCell.GetPointIds()
            for i in xrange(topCellPointIds.GetNumberOfIds()):
                cellPointId = topCellPointIds.GetId(i)
                point = surfaceMesh.GetPoint(cellPointId)
                topLayerPointId = topLayerPoints.InsertNextPoint(point)
                newCellPointIds.SetId(i, topLayerPointId)
            topLayerCells.InsertNextCell(newCell)


        # TODO REMOVE TESTING
        # for ids in xrange(0, topLayerPoints.GetNumberOfPoints(), 4):
        #     cell = vtk.vtkPolygon()
        #     cellIds = cell.GetPointIds()
        #     for i in xrange(4): cellIds.InsertId(i, ids + i)
        #     topLayerCells.InsertNextCell(cell)
        #     if topLayerCells.GetNumberOfCells() > 10: break

        # TODO remove (testing ray cast)
        # Render the top layer
        status(text="Done rain-fall ray-cast in " + str("%.1f" % (time.time() - startTime)) + ", rendering top-layer " + str(topLayerCells.GetNumberOfCells()) + " polygons ...")
        topLayerPolyData = vtk.vtkPolyData()
        topLayerPolyData.SetPoints(topLayerPoints)
        topLayerPolyData.SetPolys(topLayerCells)
        topLayerPolyData.Modified()
        segmentationNode.AddSegmentFromClosedSurfaceRepresentation(topLayerPolyData, "Rainfall cast", [0.34, 0.1, 0.95])
        status(text="Top layer rendered...")
        return

        # TODO remove (testing ray cast)
        # converting back
        status(text="Testing modification...")
        polyData = normals.GetOutput()  # contains points, point data normals, cells, polygons, bounds
        print('OLD----------\n' + str(polyData))
        polygons = SkullThicknessMappingLogic.polydata_to_polygons(polyData, status)
        # TODO modify
        newPolyData = SkullThicknessMappingLogic.write_polygons_to_polydata(polygons, status)
        # newPolyData = vtk.vtkPolyData()
        # newPolyData.SetPoints(polyData.GetPoints())
        # newPolyData.SetPolys(polyData.GetPolys())
        # newPolyData.Modified()
        print('NEW----------\n' + str(newPolyData))
        status(text="Modification passed...")

        # return

        # polys = polyData.GetPolys()
        # points = polyData.GetPoints()
        # normals = polyData.GetPointData().GetNormals()
        # print("---------------polyData:" + str(polyData))
        # print("---------------possible centers: \n" + str(points))
        # print("---------------possible normals: \n" + str(normals))

        # testing
        # new = vtk.vtkCellArray()
        # polys = polyData.GetPolys()
        # polys.InitTraversal()
        # for i in range(1, 1000):
        #     polyData.DeleteCell(i)
        # polyData.RemoveDeletedCells()
        #     npts = 3
        #     pts = [0, 0, 0]
        #     polys.GetNextCell(npts, pts)
        #     new.insertNextCell(npts, pts)
        # polyData.SetPolys(new)

        # cellArray.InitTraversal()
        # for i in range(0, polyData.GetNumberOfPolys()):
        #     pts = [0, 0, 0, 0]
        #     cellArray.GetNextCell(pts)
        #     print(pts)
        # for poly in polyData.GetPolys(): print(poly)

        # Points = vtk.vtkPoints()
        # Triangles = vtk.vtkCellArray()
        # Triangle = vtk.vtkTriangle()
        # id = Points.InsertNextPoint(1.0, 0.0, 0.0)
        # id = Points.InsertNextPoint(0.0, 0.0, 0.0)
        # id = Points.InsertNextPoint(0.0, 1.0, 0.0)
        # id = Points.InsertNextPoint(2.0, 2.0, 0.0)
        # id = Points.InsertNextPoint(0.0, 0.0, 0.0)
        # id = Points.InsertNextPoint(0.0, 0.0, 2.0)
        # Triangle.GetPointIds().SetId(0, 0)
        # Triangle.GetPointIds().SetId(1, 1)
        # Triangle.GetPointIds().SetId(2, 2)
        # Triangles.InsertNextCell(Triangle)
        # Triangle2 = vtk.vtkTriangle()
        # Triangle2.GetPointIds().SetId(0, 3)
        # Triangle2.GetPointIds().SetId(1, 4)
        # Triangle2.GetPointIds().SetId(2, 5)
        # Triangles.InsertNextCell(Triangle2)
        # newPolyData = vtk.vtkPolyData()
        # newPolyData.SetPoints(Points)
        # newPolyData.SetPolys(Triangles)
        # newPolyData.Modified()

        # newPolyData = vtk.vtkPolyData()
        # polys = polyData.GetPolys()
        # points = polyData.GetPoints()
        # # newPolyData.SetCells(cells)
        # newPolyData.SetPoints(points)
        # newPolyData.SetPolys(polys)
        # newPolyData.Modified()

        status(text="Rendering modification...")
        segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segId = segNode.AddSegmentFromClosedSurfaceRepresentation(newPolyData, "test", [0.34, 0.1, 0.95])
        # seg = segNode.GetSegmentation().GetSegment(segId)
        status(text="Rendering modification passed...")

        # clean up
        # TODO move to upper clean
        slicer.mrmlScene.RemoveNode(segmentationNode)

        # # generate labelmap
        # status("Generating labelmap...")
        # labelmap = slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segmentationNode)

        # Write to STL file
        # writer = vtk.vtkSTLWriter()
        # writer.SetInputData(surfaceMesh)
        # writer.SetFileName("d:/something.stl")
        # writer.Update()

    # @staticmethod
    # def polydata_to_polygons(polydata, status):
    #     status("Forming " + str(polydata.GetNumberOfPolys()) + " polygons..."); startTime = time.time()
    #     # print(polydata.DeleteCell)
    #     # print(polydata.RemoveDeletedCells)
    #     polygons = []
    #     points = polydata.GetPoints()
    #     polys = polydata.GetPolys()
    #     polys.InitTraversal()
    #     ids = vtk.vtkIdList()
    #     while polys.GetNextCell(ids) != 0:
    #         polygon = Polygon(points=[points.GetPoint(ids.GetId(i)) for i in xrange(ids.GetNumberOfIds())], center=[0, 0, 0], normal=[0, 0, 0])
    #         vtk.vtkTriangle.TriangleCenter(polygon.points[0], polygon.points[1], polygon.points[2], polygon.center)
    #         vtk.vtkTriangle.ComputeNormal(polygon.points[0], polygon.points[1], polygon.points[2], polygon.normal)
    #         # TODO add only if center is above x
    #         polygons.append(polygon)
    #     status("Finished " + str(len(polygons)) + " polygons in " + str("%.1f" % (time.time() - startTime)) + " seconds...")
    #     return polygons
    #
    # @staticmethod
    # def write_polygons_to_polydata(polygons, status):
    #     status("Reconstructing polydata from " + str(len(polygons)) + " polygons..."); startTime = time.time()
    #     points = vtk.vtkPoints()
    #     cells = vtk.vtkCellArray()
    #     for polygon in polygons:
    #         cell = vtk.vtkTriangle()
    #         ids = cell.GetPointIds()
    #         for i, point in enumerate(polygon.points): ids.SetId(i, points.InsertNextPoint(point))
    #         cells.InsertNextCell(cell)
    #     polydata = vtk.vtkPolyData()
    #     polydata.SetPoints(points)
    #     polydata.SetPolys(cells)
    #     polydata.Modified()
    #     status("Finished polydata in " + str("%.1f" % (time.time() - startTime)) + " seconds...")
    #     return polydata

    @staticmethod
    def rainfall_ray_cast_testing(polydata, dimensions, status):
        # Build inspection tree
        status("Building intersection object tree...")
        bspTree = vtk.vtkModifiedBSPTree()
        bspTree.SetDataSet(polydata)
        bspTree.BuildLocator()

        # Generate 'rainfall' ray trajectories
        status("Generating rainfall ray trajectories...")
        r, a, s = dimensions
        rayEndTrajectories = [{'from': [-r, -a / 2.0 + ai, -s / 2.0 + si], 'to': [r, -a / 2.0 + ai, -s / 2.0 + si]} for ai in xrange(a) for si in xrange(s)]
        # rayEndTrajectories = [{'from': [-r, -a/2.0+(ai/2.0), -s/2.0+(si/2.0)], 'to': [r, -a/2.0+(ai/2.0), -s/2.0+(si/2.0)]} for ai in xrange(a*2) for si in xrange(s*2)]

        # Cast rays
        status("Casting " + str(len(rayEndTrajectories)) + " rays..."); startTime = time.time()
        topLayerPoints, topLayerCells = vtk.vtkPoints(), vtk.vtkCellArray()
        pointsOfIntersection, cellsOfIntersection, topCellPointIds = vtk.vtkPoints(), vtk.vtkIdList(), vtk.vtkIdList()
        for trajectory in rayEndTrajectories:
            res = bspTree.IntersectWithLine(trajectory['from'], trajectory['to'], 0, pointsOfIntersection, cellsOfIntersection)  # change potentially
            if res == 0 or res != 0 and not -50 <= pointsOfIntersection.GetPoint(0)[0] < 0: continue
            polydata.GetCellPoints(cellsOfIntersection.GetId(0), topCellPointIds)
            newCell = vtk.vtkTriangle()
            newCellPointIds = newCell.GetPointIds()
            for i in xrange(topCellPointIds.GetNumberOfIds()):
                cellPointId = topCellPointIds.GetId(i)
                point = polydata.GetPoint(cellPointId)
                topLayerPointId = topLayerPoints.InsertNextPoint(point)
                newCellPointIds.SetId(i, topLayerPointId)
            topLayerCells.InsertNextCell(newCell)
        status("Done rain-fall ray-cast in " + str("%.1f" % (time.time() - startTime)) + ", rendering top-layer " + str(topLayerCells.GetNumberOfCells()) + " polygons ...")

        topLayerPolyData = vtk.vtkPolyData()
        topLayerPolyData.SetPoints(topLayerPoints)
        topLayerPolyData.SetPolys(topLayerCells)
        topLayerPolyData.Modified()
        return topLayerPolyData

    @staticmethod
    def rainfall_quad_cast(polydata, dimensions, status):
        # set precision
        r, a, s, precision = dimensions[0], dimensions[1], dimensions[2], 1.0
        preciseA, preciseS = int(dimensions[1]/precision), int(dimensions[2]/precision)

        # build search tree
        status(text="Building intersection object tree...")
        bspTree = vtk.vtkModifiedBSPTree()
        bspTree.SetDataSet(polydata)
        bspTree.BuildLocator()

        # cast rays
        status(text="Casting " + str(preciseA*preciseS) + " rays downward..."); startTime = time.time()
        points, temporaryHitPoint = vtk.vtkPoints(), [0.0, 0.0, 0.0]
        hitPointMatrix = [[None for ai in xrange(preciseA)] for si in reversed(xrange(preciseS))]
        for si in reversed(xrange(preciseS)):
            for ai in xrange(preciseA):
                res = bspTree.IntersectWithLine([-r, -a/2.0 + ai*precision, -s/2.0 + si*precision], [r, -a/2.0 + ai*precision, -s/2.0 + si*precision], 0, vtk.reference(0), temporaryHitPoint, [0.0, 0.0, 0.0], vtk.reference(0), vtk.reference(0))
                if res != 0 and -50 <= temporaryHitPoint[0] < 20:
                    temporaryHitPoint[0] -= 0.3  # raised to improve visibility
                    hitPointMatrix[si][ai] = HitPoint(points.InsertNextPoint(temporaryHitPoint), temporaryHitPoint[:])

        # form cells
        cells = vtk.vtkCellArray()
        for i in xrange(len(hitPointMatrix)-1):
            for j in xrange(len(hitPointMatrix[i])-1):
                hitPoints = [hitPointMatrix[i][j], hitPointMatrix[i+1][j], hitPointMatrix[i+1][j+1], hitPointMatrix[i][j+1]]
                if None in hitPoints: continue
                rawNormal = numpy.linalg.solve(numpy.array([hitPoints[0].point, hitPoints[1].point, hitPoints[2].point]), [1, 1, 1])
                hitPointMatrix[i][j].normal = rawNormal / numpy.sqrt(numpy.sum(rawNormal**2))
                v1, v2 = numpy.array(hitPointMatrix[i][j].normal), numpy.array([-1.0, 0.0, 0.0])     # TODO make direction configurable
                degrees = numpy.degrees(numpy.math.atan2(len(numpy.cross(v1, v2)), numpy.dot(v1, v2)))
                if degrees < 80: cells.InsertNextCell(4, [p.pid for p in hitPoints])
        status(text="Finished ray-casting in " + str("%.1f" % (time.time() - startTime)) + "s, found " + str(cells.GetNumberOfCells()) + " cells...")

        # build polydata
        topLayerPolyData = vtk.vtkPolyData()
        topLayerPolyData.SetPoints(points)
        topLayerPolyData.SetPolys(cells)
        topLayerPolyData.Modified()
        return topLayerPolyData, [p for r in hitPointMatrix for p in r if p is not None]

    @staticmethod
    def rainfall_ray_cast(polydata, dimensions, status):
        status(text="Building intersection object tree...")
        bspTree = vtk.vtkModifiedBSPTree()
        bspTree.SetDataSet(polydata)
        bspTree.BuildLocator()

        precision = 1.0
        status(text="Casting " + str(dimensions[1]*precision*dimensions[2]*precision) + " rays downward..."); startTime = time.time()
        r, a, s = dimensions
        topCellIds = vtk.vtkIdList()
        for ai in xrange(int(a*precision)):
            for si in xrange(int(s*precision)):
                start, end = [-r, -a/2.0 + ai/precision, -s/2.0 + si/precision], [r, -a/2.0 + ai/precision, -s/2.0 + si/precision]
                hitPoint, cellId = [0.0, 0.0, 0.0], vtk.reference(0)
                res = bspTree.IntersectWithLine(start, end, 0, vtk.reference(0), hitPoint, [0.0, 0.0, 0.0], vtk.reference(0), cellId)
                if res == 0 or res != 0 and not -50 <= hitPoint[0] < -10: continue
                topCellIds.InsertUniqueId(cellId)
        status(text="Finished ray-casting in " + str("%.1f" % (time.time() - startTime)) + "s, found " + str(topCellIds.GetNumberOfIds()) + " cells...")
        return topCellIds

    @staticmethod
    def inflate_cellIds(cell_ids, polydata, status):
        status(text="Building triangle filter...")
        triangleFilter = vtk.vtkTriangleFilter()
        triangleFilter.SetInputData(polydata)
        triangleFilter.Update()
        output = triangleFilter.GetOutput()

        status(text="Filling in polygons...")
        temporaryCellPointIds, temporaryIdList, temporaryNeighbourCellIdList = vtk.vtkIdList(), vtk.vtkIdList(), vtk.vtkIdList()
        for cellId in xrange(cell_ids.GetNumberOfIds()):
            polydata.GetCellPoints(cell_ids.GetId(cellId), temporaryCellPointIds)
            temporaryNeighbourCellIdList.Reset()
            for pointId in xrange(temporaryCellPointIds.GetNumberOfIds()):
                temporaryIdList.Reset()
                temporaryIdList.InsertNextId(temporaryCellPointIds.GetId(pointId))
                output.GetCellNeighbors(cell_ids.GetId(cellId), temporaryIdList, temporaryNeighbourCellIdList)
                for neighbourCellId in xrange(temporaryNeighbourCellIdList.GetNumberOfIds()):
                    cell_ids.InsertUniqueId(temporaryNeighbourCellIdList.GetId(neighbourCellId))
        return cell_ids

    @staticmethod
    def collect_and_build_polydata_from_cellIds_and_polydata(cell_ids, polydata, status):
        status(text="Building subset polydata from " + str(cell_ids.GetNumberOfIds()) + " polygons...")
        topLayerPoints, topLayerCells = vtk.vtkPoints(), vtk.vtkCellArray()
        temporaryCellPointIds = vtk.vtkIdList()
        for cellId in xrange(cell_ids.GetNumberOfIds()):
            polydata.GetCellPoints(cell_ids.GetId(cellId), temporaryCellPointIds)
            newCell = vtk.vtkTriangle()
            for i in xrange(temporaryCellPointIds.GetNumberOfIds()):
                point = polydata.GetPoint(temporaryCellPointIds.GetId(i))
                newCell.GetPointIds().SetId(i, topLayerPoints.InsertNextPoint(point))
            topLayerCells.InsertNextCell(newCell)

        # build polydata
        subsetPolyData = vtk.vtkPolyData()
        subsetPolyData.SetPoints(topLayerPoints)
        subsetPolyData.SetPolys(topLayerCells)
        subsetPolyData.Modified()
        return subsetPolyData

    @staticmethod
    def add_polydata_to_segmentation_node(polydata, segmentation_node, status):
        status(text="Rendering top layer polydata with " + str(polydata.GetPolys().GetNumberOfCells()) +" polygons..."); startTime = time.time()
        segmentation_node.AddSegmentFromClosedSurfaceRepresentation(polydata, "Rainfall cast", [0.34, 0.1, 0.95])
        status(text="Top layer rendered in " + str("%.1f" % (time.time() - startTime)) + "s...")


    # TODO remove
    # @staticmethod
    # def raw_polydata_to_facets(data, status):
    #     status(text="Calculating centers and normals from polygons...")
    #     startTime = time.time()
    #     facets = []
    #     rawPoints = data.GetPoints().GetData()
    #     rawPolys = data.GetPolys().GetData()
    #     connections = [int(rawPolys.GetTuple(i)) for i in xrange(rawPolys.GetNumberOfTuples())]
    #     for connection in itertools.izip_longest(*[iter(connections)] * 4):
    #         vertices = [[rawPoints.GetValue(i * 3), rawPoints.GetValue(i * 3 + 1), rawPoints.GetValue(i * 3 + 2)] for i in connection[1:4]]
    #         facet = Facet(c=[0, 0, 0], n=[0, 0, 0])
    #         vtk.vtkTriangle.TriangleCenter(vertices[0], vertices[1], vertices[2], facet.center)
    #         vtk.vtkTriangle.ComputeNormal(vertices[0], vertices[1], vertices[2], facet.normal)
    #         facets.append(facet)
    #     status(text="Finished " + str(len(facets)) + " polygons in " + str("%.1f" % (time.time() - startTime)) + " seconds...")
    #     return facets

    # @staticmethod
    # def process(image_node, rest_node, outer_node, status):
    #     status(text="Initializing parameters, image, and models...")
    #     parameters = {
    #       'n_dura_voxel': 20,
    #       'thresh_bone': 600,
    #       'thresh_aircell': 150,
    #       'thresh_dura': -300,
    #       'n_outward_bone_check': 5
    #     }
    #     uniD = 10
    #
    #     data = {
    #       'image': image_node,    # SkullThicknessMappingLogic.sample_folder() + 'Images/' + sample_name + '.hdr',
    #       'outer_stl': rest_node,    # SkullThicknessMappingLogic.read_stl(SkullThicknessMappingLogic.sample_folder() + 'STL/' + sample_name + '_outer.stl', status),
    #       'rest_stl': outer_node     # SkullThicknessMappingLogic.read_stl(SkullThicknessMappingLogic.sample_folder() + 'STL/' + sample_name + '_rest.stl')
    #     }
    #     # get file names for image, outer, and rest of ear
    #     # read stl files for outer and rest of ear
    #
    #     SkullThicknessMappingLogic.calculate_distance(data, parameters, status)
    #     # calculate thickness data VIA cal_dist.py
    #     # plot output
    #     # return output

    # @staticmethod
    # def amanatidesWooAlgorithm(origin, normal, parameters):
    #     result = Intersection()
    #     flag, tMin = SkullThicknessMappingLogic.rayBoxIntersection(origin, normal, parameters['minimum'], parameters['maximum'])
    #     if flag == 0: print('[!] The ray does not intersect the grid'); return None, None
    #
    #     if tMin < 0: tMin = 0
    #     start = origin + numpy.floor(tMin, normal)
    #     boxSize = parameters['maximum'] - parameters['minimum']
    #     x = numpy.floor(numpy.dot(((start[0] - parameters['minimum'][0]) / boxSize[0]), parameters['dimensions'][0])) + 1
    #     y = numpy.floor(numpy.dot(((start[1] - parameters['minimum'][1]) / boxSize[1]), parameters['dimensions'][1])) + 1
    #     z = numpy.floor(numpy.dot(((start[2] - parameters['minimum'][2]) / boxSize[2]), parameters['dimensions'][2])) + 1
    #     if x == (parameters['dimensions'][0] + 1): x = x - 1
    #     if y == (parameters['dimensions'][1] + 1): y = y - 1
    #     if z == (parameters['dimensions'][2] + 1): z = z - 1
    #     if normal[0] >= 0:
    #         tVoxelX = x / parameters['dimensions'][0]
    #         stepX = 1
    #     else:
    #         tVoxelX = (x - 1) / parameters['dimensions'][0]
    #         stepX = - 1
    #     if normal[1] >= 0:
    #         tVoxelY = y / parameters['dimensions'][1]
    #         stepY = 1
    #     else:
    #         tVoxelY = (y - 1) / parameters['dimensions'][1]
    #         stepY = - 1
    #     if normal[2] >= 0:
    #         tVoxelZ = z / parameters['dimensions'][2]
    #         stepZ = 1
    #     else:
    #         tVoxelZ = (z - 1) / parameters['dimensions'][2]
    #         stepZ = - 1
    #
    #     voxelMaxX = parameters['minimum'][0] + numpy.dot(tVoxelX, boxSize[0])
    #     voxelMaxY = parameters['minimum'][1] + numpy.dot(tVoxelY, boxSize[1])
    #     voxelMaxZ = parameters['minimum'][2] + numpy.dot(tVoxelZ, boxSize[2])
    #     tMaxX = tMin + (voxelMaxX - start[0]) / normal[0]
    #     tMaxY = tMin + (voxelMaxY - start[1]) / normal[1]
    #     tMaxZ = tMin + (voxelMaxZ - start[2]) / normal[2]
    #     voxelSizeX = boxSize[0] / parameters['dimensions'][0]
    #     voxelSizeY = boxSize[1] / parameters['dimensions'][1]
    #     voxelSizeZ = boxSize[2] / parameters['dimensions'][2]
    #     tDeltaX = voxelSizeX / abs(normal[0])
    #     tDeltaY = voxelSizeY / abs(normal[1])
    #     tDeltaZ = voxelSizeZ / abs(normal[2])
    #     i, t_flag = 1, 1
    #     while (x <= parameters['dimensions'][0]) and (x >= 1) and (y <= parameters['dimensions'][1]) and (y >= 1) and (z <= parameters['dimensions'][2]) and (z >= 1) and t_flag:
    #         result.voxel = [x, y, z]
    #         result.value = parameters['dimensions'] # ???????? image(y, x, z)
    #         # t1 = [(x - 1) / parameters['dimensions],[0 (y - 1) / parameters['dimensions'][1], (z - 1) / parameters['dimensions'][2]]
    #         # t2 = [x / parameters['dimensions],[0 y / parameters['dimensions'][1], z / parameters['dimensions'][2]]
    #         # vMin = (grid_3d_min_bound + numpy.multiply(t1, boxSize))
    #         # vMax = (grid_3d_min_bound + numpy.multiply(t2, boxSize))
    #         i = i + 1
    #         # check if voxel [x,y,z] contains any intersection with the ray
    #         #   if ( intersection ) break
    #         if tMaxX < tMaxY:
    #             if tMaxX < tMaxZ:
    #                 x = x + stepX
    #                 tMaxX = tMaxX + tDeltaX
    #             else:
    #                 z = z + stepZ
    #                 tMaxZ = tMaxZ + tDeltaZ
    #         else:
    #             if tMaxY < tMaxZ:
    #                 y = y + stepY
    #                 tMaxY = tMaxY + tDeltaY
    #             else:
    #                 z = z + stepZ
    #                 tMaxZ = tMaxZ + tDeltaZ
    #     return result

    # @staticmethod
    # def rayBoxIntersection(origin=None, direction=None, v_min=None, v_max=None):
    #     #  Ray/box intersection using the Smits' algorithm
    #     # Input:
    #     #    origin.
    #     #    direction.
    #     #    box = (v_min,v_max)
    #     # Output:
    #     #    flag: (0) Reject, [0] Intersect.
    #     #    tMin: distance from the ray origin.
    #     # Author:
    #     #    Jesus Mena
    #
    #     if direction[0] >= 0:
    #         tMin = (v_min[0] - origin[0]) / direction[0]
    #         tMax = (v_max[0] - origin[0]) / direction[0]
    #     else:
    #         tMin = (v_max[0] - origin[0]) / direction[0]
    #         tMax = (v_min[0] - origin[0]) / direction[0]
    #     if direction[1] >= 0:
    #         tyMin = (v_min[1] - origin[1]) / direction[1]
    #         tyMax = (v_max[1] - origin[1]) / direction[1]
    #     else:
    #         tyMin = (v_max[1] - origin[1]) / direction[1]
    #         tyMax = (v_min[1] - origin[1]) / direction[1]
    #     if (tMin > tyMax) or (tyMin > tMax):
    #         flag = 0
    #         tMin = - 1
    #         return flag, tMin
    #
    #     if tyMin > tMin: tMin = numpy.copy(tyMin)
    #     if tyMax < tMax: tMax = numpy.copy(tyMax)
    #     if direction[2] >= 0:
    #         tzmin = (v_min[2] - origin[2]) / direction[2]
    #         tzmax = (v_max[2] - origin[2]) / direction[2]
    #     else:
    #         tzmin = (v_max[2] - origin[2]) / direction[2]
    #         tzmax = (v_min[2] - origin[2]) / direction[2]
    #
    #     if (tMin > tzmax) or (tzmin > tMax):
    #         flag = 0
    #         tMin = - 1
    #         return flag, tMin
    #     if tzmin > tMin: tMin = numpy.copy(tzmin)
    #     if tzmax < tMax: tMax = numpy.copy(tzmax)
    #
    #     # if( (tMin < t1) && (tMax > t0) )
    #     flag = 1
    #     #    flag = 0;
    #     #    tMin = -1;
    #     # end;
    #     return flag, tMin

    # @staticmethod
    # def calculate_distance(data, parameters, status):
    #     # TODO ---------- remove
    #     n_dura_voxel = parameters['n_dura_voxel']
    #     thresh_aircell = parameters['thresh_aircell']
    #     thresh_dura = parameters['thresh_dura']
    #     thresh_bone = parameters['thresh_bone']
    #     n_outward_bone_check = parameters['n_outward_bone_check']
    #
    #     # ----- x,y,z mesh grid of dimension ranges
    #     status(text="Generating dimension resolution matrix from image...")
    #     dimensions = [float(d) for d in data['image'].GetImageData().GetDimensions()]
    #     spacing = [float(s) for s in data['image'].GetSpacing()]
    #     arange = [numpy.arange(0, numpy.dot((dimensions[i] - 1), s) + s, s) for i, s in enumerate(spacing)]
    #     xMesh, yMesh, zMesh = numpy.meshgrid(arange[0], arange[1], arange[2])
    #
    #     # ----- get triangles from outer stl file
    #     status(text="Calculating centers and normals from outer model..."); startTime = time.time()
    #     facets = []
    #     outerPoints = data['outer_stl'].GetPolyData().GetPoints().GetData()
    #     outerPolyData = data['outer_stl'].GetPolyData().GetPolys().GetData()
    #     connections = [int(outerPolyData.GetTuple(i)) for i in xrange(outerPolyData.GetNumberOfTuples())]
    #     for connection in itertools.izip_longest(*[iter(connections)] * 4):
    #         vertices = [[outerPoints.GetValue(i*3), outerPoints.GetValue(i*3+1), outerPoints.GetValue(i*3+2)] for i in connection[1:4]]
    #         facet = Facet(c=[0, 0, 0], n=[0, 0, 0])
    #         vtk.vtkTriangle.TriangleCenter(vertices[0], vertices[1], vertices[2], facet.center)
    #         vtk.vtkTriangle.ComputeNormal(vertices[0], vertices[1], vertices[2], facet.normal)
    #         facets.append(facet)
    #     status(text="Finished " + str(len(facets)) + " facets in " + str("%.1f"%(time.time()-startTime)) + " seconds...")
    #
    #     # ----- calculate
    #     status(text="Calculating thickness..."); startTime = time.time()
    #     for facet in facets:
    #         parameters = {'dimensions': dimensions, 'minimum' : [0, 0, 0], 'maximum' : [(dimensions[i]-1)*s for i, s in enumerate(spacing)]}
    #         outwardsIntersection = SkullThicknessMappingLogic.amanatidesWooAlgorithm(facet.center, facet.normal_outward(), parameters)
    #         # TODO in each direction get the voxel values in n_outward_bone_check length, then get max, then check if thats in threshold
    #         # if max(g_outside(arange(1, n_outward_bone_check))) >= thresh_bone:
    #         # if max(outwardsIntersection.value(arange(1, parameters['n_outward_bone_check']))) >= parameters['thresh_bone']:
    #         #   new_origin_voxel = find(g_outside >= thresh_bone, 1, 'last')
    #         #   origin = concat([mesh_x(1, iv_outside(new_origin_voxel, 1), 1), mesh_y(iv_outside(new_origin_voxel, 2), 1, 1), mesh_z(1, 1, iv_outside(new_origin_voxel, 3))])
    #         # TODO implement intersection class
    #         inwardsIntersection = SkullThicknessMappingLogic.amanatidesWooAlgorithm(facet.center, facet.normal_inward(), parameters)
    #     status(text="Finished calculating thickness in " + str("%.1f"%(time.time()-startTime)) + " seconds...")


    #     c = data['outer_stl'].centers
    #     n = data['outer_stl'].normals
    #     n_patches = size(c, 1)
    #     patches = arange(1, n_patches)
    #     for i in patches.reshape(-1):
    #         fprintf(1, '%i %s %i\\n', i, '/', n_patches)
    #         # thickness calculation
    #         origin = c(i, arange())
    #         data(i).center = copy(origin)
    #         direction_inward = - n(i, arange())
    #         direction_outward = n(i, arange())
    #         grid3D_nx = size(image, 1)
    #         grid3D_ny = size(image, 2)
    #         grid3D_nz = size(image, 3)
    #         grid3D_minBound = concat([0, 0, 0])
    #         grid3D_maxBound = concat([dot((size(image, 1) - 1), res_x), dot((size(image, 2) - 1), res_y), dot((size(image, 3) - 1), res_z)])
    #         iv_outside, g_outside = amanatidesWooAlgorithm(origin, direction_outward, image, grid3D_nx, grid3D_ny, grid3D_nz, grid3D_minBound, grid3D_maxBound, nargout=2)


    #         if max(g_outside(arange(1, n_outward_bone_check))) >= thresh_bone:
    #             new_origin_voxel = find(g_outside >= thresh_bone, 1, 'last')
    #             origin = concat([mesh_x(1, iv_outside(new_origin_voxel, 1), 1), mesh_y(iv_outside(new_origin_voxel, 2), 1, 1), mesh_z(1, 1, iv_outside(new_origin_voxel, 3))])
    #         iv_inside, g_inside = amanatidesWooAlgorithm(origin, direction_inward, image, grid3D_nx, grid3D_ny, grid3D_nz, grid3D_minBound, grid3D_maxBound, nargout=2)


    #         n_first_bone = 1
    #         while not isempty(g_inside) and g_inside(1) <= thresh_bone:
    #             n_first_bone = n_first_bone + 1
    #             g_inside = removerows(g_inside, 1)
    #             iv_inside = removerows(iv_inside, 1)
    #             origin = concat([mesh_x(1, iv_inside(1, 1), 1), mesh_y(iv_inside(1, 2), 1, 1), mesh_z(1, 1, iv_inside(1, 3))])
    #
    #         data(i).p = copy(g_inside)
    #         data(i).iv = copy(iv_inside)
    #         data(i).origin = copy(origin)
    #         # First aircell and thickness to first aircell
    #         aircell_ind = find(g_inside <= thresh_aircell, 1, 'first')
    #         first_aircell_voxel = iv_inside(aircell_ind, arange())
    #         first_dark_position = concat([mesh_x(1, first_aircell_voxel(1), 1), mesh_y(first_aircell_voxel(2), 1, 1), mesh_z(1, 1, first_aircell_voxel(3))])
    #         d_aircell = sqrt(sumsqr(origin - first_dark_position))
    #         data(i).first_aircell = copy(first_dark_position)
    #         data(i).th_aircell = copy(d_aircell)
    #         dura_list = find(g_inside <= thresh_dura)
    #         dura_diff = diff(dura_list)
    #         dura_movsum = movsum(dura_diff, concat([0, n_dura_voxel - 1]))
    #         dura_ind = find(dura_movsum <= n_dura_voxel, 1, 'first')
    #         dura_voxel = iv_inside(dura_list(dura_ind), arange())
    #         dura_voxel_position = concat([mesh_x(1, dura_voxel(1), 1), mesh_y(dura_voxel(2), 1, 1), mesh_z(1, 1, dura_voxel(3))])
    #         d_dura = sqrt(sumsqr(origin - dura_voxel_position))
    #         data(i).first_dura = copy(dura_voxel_position)
    #         data(i).th_dura = copy(d_dura)
    #     #     dura_ind = find(g_inside<=thresh_dura);
    #     #     k =ones(n_dura_voxel,1)/n_dura_voxel;
    #     #     dura_diff =diff(dura_ind);
    #     #     dura_diff_conv =ceil(conv(dura_diff,k));
    #     #     dura_voxel_list = find(dura_diff_conv == 1,1,'first');
    #     #     dura_voxel_ind =dura_ind(dura_voxel_list-n_dura_voxel+1);
    #     #     dura_voxel = iv_inside(dura_voxel_ind,:);
    #     #     dura_voxel_position = [mesh_x(1,dura_voxel(1),1),mesh_y(dura_voxel(2),1,1),mesh_z(1,1,dura_voxel(3))];
    #     #
    #     #     [mins,locs] = findpeaks(-g_inside);
    #     #     mins = -mins;
    #     #     l_temp = find(mins<thresh_aircell,1,'first');
    #     #     ind_min = locs(l_temp);
    #     #     first_dark_index = ind_min-1;
    #     #     data(i).lasts = n_first_bone+first_dark_index;
    #     #     first_dark_voxel = iv_inside(first_dark_index,:);
    #     #     first_dark_position = [mesh_x(1,first_dark_voxel(1),1),mesh_y(first_dark_voxel(2),1,1),mesh_z(1,1,first_dark_voxel(3))];
    #     #     data(i).first_aircell = first_dark_position;
    #     #     d = sqrt(sumsqr(origin-first_dark_position));
    #     #     d_dura = sqrt(sumsqr(origin-dura_voxel_position));
    #     #     if (d>max(res(3)))
    #     #         flag = 0;
    #     #     end
    #     #     data(i).th_aircell = d;
    #     #     data(i).first_dura = dura_voxel_position;
    #     #     data(i).th_dura = d_dura;
    #     #
    #     # fprintf(1,'#i\n',i);
    #     # fprintf(1,'#s\n','Done!');
    #     return data





    # @staticmethod
    # def read_stl(file_name, updater):
    #     print("@@@ --- Start: " + file_name)
    #     data = []
    #     pool = multiprocessing.Pool(8)
    #     with open(file_name, mode='r') as file:
    #         file.read(1)
    #         startTime = time.time()
    #         # def process7(lines):
    #             # print(lines)
    #             # slicer.app.processEvents()
    #         # results = pool.map(process7, file, 7)
    #
    #         # for lines in itertools.izip_longest(*[iter(file)] * 7, fillvalue=None):
    #         #     if len(lines) != 7: continue
    #         #     data.append(Facet(
    #         #         n=lines[1],  # [float(s) for s in re.findall(r"[-+]?\d*\.\d+|\d+", lines[1])],
    #         #         v1=lines[3],  # [float(s) for s in re.findall(r"[-+]?\d*\.\d+|\d+", lines[3])],
    #         #         v2=lines[4],  # [float(s) for s in re.findall(r"[-+]?\d*\.\d+|\d+", lines[4])],
    #         #         v3=lines[5]  # [float(s) for s in re.findall(r"[-+]?\d*\.\d+|\d+", lines[5])]
    #         #     ))
    #         #     t = time.time()-startTime
    #         #     updater("Status: " + str(len(data)) + " facets, after " + str(t))
    #         #     slicer.app.processEvents()
    #         #     if t > 60: return
    #             # break
    #     # print("Initialized " + str(len(data)) + " facets")
    #
    #     # # open file--------------
    #     # fileOpen = fopen(file_name, 'r')
    #     # format = '%*s %*s %f32 %f32 %f32 \\n %*s %*s \\n %*s %f32 %f32 %f32 \\n %*s %f32 %f32 %f32 \\n %*s %f32 %f32 %f32 \\n %*s \\n %*s \\n'
    #     # C = textscan(fileOpen, format, 'HeaderLines', 1)
    #     # fclose(fileOpen)
    #     #
    #     # ravel = []
    #     # output = []
    #     #
    #     # # extract vertices
    #     # v1 = cell2mat(C(numpy.arange(4, 6)))
    #     # v2 = cell2mat(C(numpy.arange(7, 9)))
    #     # v3 = cell2mat(C(numpy.arange(10, 12)))
    #     # v_temp = numpy.concat([v1, v2, v3])
    #     # vertices_all = numpy.zeros(3, numel(v_temp) / 3)
    #     # ravel[vertices_all] = numpy.ravel(v_temp)
    #     # vertices_all = vertices_all
    #     # fnum = length(vertices_all) / 3
    #     #
    #     # # gets points and triangle indexes given vertex and facet number
    #     # c = size(vertices_all, 1)
    #     # # triangles with vertex id data
    #     # conn = numpy.zeros(3, fnum)
    #     # ravel[conn] = numpy.arange(1, c)
    #     # # now we have to keep unique points fro vertex
    #     # p, i, j = numpy.unique(vertices_all, 'rows', nargout=3)
    #     #
    #     # ravel[conn] = j(numpy.ravel(conn))
    #     # output[conn] = numpy.copy(conn)
    #     # # ijk-to-RAS TF
    #     # tf = numpy.concat([[- 1, 0, 0], [0, - 1, 0], [0, 0, 1]])
    #     # output[p] = numpy.copy((numpy.dot(tf, p)))
    #     # vertices_all = (numpy.dot(tf, vertices_all))
    #     # output[centers] = numpy.copy((vertices_all(numpy.arange(1, end(), 3), numpy.arange()) + vertices_all(numpy.arange(2, end(), 3),numpy.arange()) + vertices_all(numpy.arange(3, end(), 3), numpy.arange())) / 3)
    #     # output.[tri] = numpy.copy(triangulation(output.conn, output.p))
    #     # output.[normals] = numpy.copy(faceNormal(output.tri))
    #     # return output

class SkullThicknessMappingTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_SkullThicknessMapping1()

    def test_SkullThicknessMapping1(self):
        pass

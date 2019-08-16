import inspect

import slicer
import numpy
import itertools
import re
import multiprocessing
import time
import qt
import vtk
from slicer.ScriptedLoadableModule import *


# Interface tools
class InterfaceTools:
    def __init__(self, parent):
        pass

    @staticmethod
    def build_volume_selector(on_click=None):
        s = slicer.qMRMLNodeComboBox()
        s.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        s.addEnabled = False
        s.renameEnabled = s.noneEnabled = False  # True
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


class Facet:
    normal = None
    center = None

    def normal_inward(self): return self.normal
    def normal_outward(self): return [-v for v in self.normal]

    def __init__(self, c, n):
        self.normal = n
        self.center = c

    def __repr__(self):
        return str(self)

    def __str__(self):
        # return "\n  [Facet]" + " n:" + str(self.n) + "\n          v1:" + str(self.v1) + "\n          v2:" + str(self.v2) + "\n          v3:" + str(self.v3) + '\n'
        return "\n  [Facet]" + " n:" + str(self.normal) + "\n          c:" + str(self.center)

class Intersection:
    voxel = None
    value = None

    def __init__(self, voxel, value):
        self.voxel = voxel
        self.value = value


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
    label = None
    volume = None
    outer = None
    rest = None

    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.layout.addLayout(self.build_interface())
        self.layout.addStretch()

    def build_interface(self):
        self.label = qt.QLabel("Status: ")
        self.volume = InterfaceTools.build_volume_selector()
        self.outer = InterfaceTools.build_model_selector()
        self.rest = InterfaceTools.build_model_selector()
        button = qt.QPushButton("Go")
        button.connect('clicked(bool)', self.process)
        layout = qt.QVBoxLayout()
        layout.addWidget(self.volume)
        layout.addWidget(self.outer)
        layout.addWidget(self.rest)
        layout.addWidget(self.label)
        layout.addWidget(button)
        layout.setMargin(10)
        return layout

    def update_status(self, text):
        self.label.text = "Status: " + text
        slicer.app.processEvents()

    def process(self):
        if self.volume.currentNode() is None: return
        SkullThicknessMappingLogic.process(self.volume.currentNode(), self.rest.currentNode(), self.outer.currentNode(), self.update_status)


class SkullThicknessMappingLogic(ScriptedLoadableModuleLogic):
    @staticmethod
    def sample_folder():
        return slicer.os.path.dirname(slicer.os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/Resources/Sample/'

    @staticmethod
    def process(image_node, rest_node, outer_node, status):
        status("Initializing parameters, image, and models...")
        parameters = {
          'n_dura_voxel': 20,
          'thresh_bone': 600,
          'thresh_aircell': 150,
          'thresh_dura': -300,
          'n_outward_bone_check': 5
        }
        uniD = 10

        data = {
          'image': image_node,    # SkullThicknessMappingLogic.sample_folder() + 'Images/' + sample_name + '.hdr',
          'outer_stl': rest_node,    # SkullThicknessMappingLogic.read_stl(SkullThicknessMappingLogic.sample_folder() + 'STL/' + sample_name + '_outer.stl', status),
          'rest_stl': outer_node     # SkullThicknessMappingLogic.read_stl(SkullThicknessMappingLogic.sample_folder() + 'STL/' + sample_name + '_rest.stl')
        }
        # get file names for image, outer, and rest of ear
        # read stl files for outer and rest of ear

        SkullThicknessMappingLogic.calculate_distance(data, parameters, status)
        # calculate thickness data VIA cal_dist.py
        # plot output
        # return output

    @staticmethod
    # def amanatidesWooAlgorithm(center, normal, parameters):
    def amanatidesWooAlgorithm(origin=None, direction=None, image=None, grid_3d_nx=None, grid_3d_ny=None, grid_3d_nz=None, grid_3d_min_bound=None, grid_3d_max_bound=None):
        result = Intersection()
        flag, tMin = SkullThicknessMappingLogic.rayBoxIntersection(origin, direction, grid_3d_min_bound, grid_3d_max_bound, nargout=2)
        if flag == 0:
            print('[!] The ray does not intersect the grid')
            return None, None

        if tMin < 0: tMin = 0
        start = origin + numpy.floor(tMin, direction)
        boxSize = grid_3d_max_bound - grid_3d_min_bound
        x = numpy.floor(numpy.dot(((start(1) - grid_3d_min_bound(1)) / boxSize(1)), grid_3d_nx)) + 1
        y = numpy.floor(numpy.dot(((start(2) - grid_3d_min_bound(2)) / boxSize(2)), grid_3d_ny)) + 1
        z = numpy.floor(numpy.dot(((start(3) - grid_3d_min_bound(3)) / boxSize(3)), grid_3d_nz)) + 1
        if x == (grid_3d_nx + 1): x = x - 1
        if y == (grid_3d_ny + 1): y = y - 1
        if z == (grid_3d_nz + 1): z = z - 1
        if direction(1) >= 0:
            tVoxelX = x / grid_3d_nx
            stepX = 1
        else:
            tVoxelX = (x - 1) / grid_3d_nx
            stepX = - 1
        if direction(2) >= 0:
            tVoxelY = y / grid_3d_ny
            stepY = 1
        else:
            tVoxelY = (y - 1) / grid_3d_ny
            stepY = - 1
        if direction(3) >= 0:
            tVoxelZ = z / grid_3d_nz
            stepZ = 1
        else:
            tVoxelZ = (z - 1) / grid_3d_nz
            stepZ = - 1

        voxelMaxX = grid_3d_min_bound(1) + numpy.dot(tVoxelX, boxSize(1))
        voxelMaxY = grid_3d_min_bound(2) + numpy.dot(tVoxelY, boxSize(2))
        voxelMaxZ = grid_3d_min_bound(3) + numpy.dot(tVoxelZ, boxSize(3))
        tMaxX = tMin + (voxelMaxX - start(1)) / direction(1)
        tMaxY = tMin + (voxelMaxY - start(2)) / direction(2)
        tMaxZ = tMin + (voxelMaxZ - start(3)) / direction(3)
        voxelSizeX = boxSize(1) / grid_3d_nx
        voxelSizeY = boxSize(2) / grid_3d_ny
        voxelSizeZ = boxSize(3) / grid_3d_nz
        tDeltaX = voxelSizeX / abs(direction(1))
        tDeltaY = voxelSizeY / abs(direction(2))
        tDeltaZ = voxelSizeZ / abs(direction(3))
        i, t_flag = 1, 1
        while (x <= grid_3d_nx) and (x >= 1) and (y <= grid_3d_ny) and (y >= 1) and (z <= grid_3d_nz) and (z >= 1) and t_flag:
            result.voxel = [x, y, z]
            result.value = image(x, y, z) # ???????? image(y, x, z)
            # t1 = [(x - 1) / grid_3d_nx, (y - 1) / grid_3d_ny, (z - 1) / grid_3d_nz]
            # t2 = [x / grid_3d_nx, y / grid_3d_ny, z / grid_3d_nz]
            # vMin = (grid_3d_min_bound + numpy.multiply(t1, boxSize))
            # vMax = (grid_3d_min_bound + numpy.multiply(t2, boxSize))
            i = i + 1
            # check if voxel [x,y,z] contains any intersection with the ray
            #   if ( intersection ) break
            if tMaxX < tMaxY:
                if tMaxX < tMaxZ:
                    x = x + stepX
                    tMaxX = tMaxX + tDeltaX
                else:
                    z = z + stepZ
                    tMaxZ = tMaxZ + tDeltaZ
            else:
                if tMaxY < tMaxZ:
                    y = y + stepY
                    tMaxY = tMaxY + tDeltaY
                else:
                    z = z + stepZ
                    tMaxZ = tMaxZ + tDeltaZ
        return result

    @staticmethod
    def rayBoxIntersection(origin=None, direction=None, v_min=None, v_max=None):
        #  Ray/box intersection using the Smits' algorithm
        # Input:
        #    origin.
        #    direction.
        #    box = (v_min,v_max)
        # Output:
        #    flag: (0) Reject, (1) Intersect.
        #    tMin: distance from the ray origin.
        # Author:
        #    Jesus Mena

        if direction(1) >= 0:
            tMin = (v_min(1) - origin(1)) / direction(1)
            tMax = (v_max(1) - origin(1)) / direction(1)
        else:
            tMin = (v_max(1) - origin(1)) / direction(1)
            tMax = (v_min(1) - origin(1)) / direction(1)
        if direction(2) >= 0:
            tyMin = (v_min(2) - origin(2)) / direction(2)
            tyMax = (v_max(2) - origin(2)) / direction(2)
        else:
            tyMin = (v_max(2) - origin(2)) / direction(2)
            tyMax = (v_min(2) - origin(2)) / direction(2)
        if (tMin > tyMax) or (tyMin > tMax):
            flag = 0
            tMin = - 1
            return flag, tMin

        if tyMin > tMin: tMin = numpy.copy(tyMin)
        if tyMax < tMax: tMax = numpy.copy(tyMax)
        if direction(3) >= 0:
            tzmin = (v_min(3) - origin(3)) / direction(3)
            tzmax = (v_max(3) - origin(3)) / direction(3)
        else:
            tzmin = (v_max(3) - origin(3)) / direction(3)
            tzmax = (v_min(3) - origin(3)) / direction(3)

        if (tMin > tzmax) or (tzmin > tMax):
            flag = 0
            tMin = - 1
            return flag, tMin
        if tzmin > tMin: tMin = numpy.copy(tzmin)
        if tzmax < tMax: tMax = numpy.copy(tzmax)

        # if( (tMin < t1) && (tMax > t0) )
        flag = 1
        #    flag = 0;
        #    tMin = -1;
        # end;
        return flag, tMin

    @staticmethod
    def calculate_distance(data, parameters, status):
        # TODO ---------- remove
        n_dura_voxel = parameters['n_dura_voxel']
        thresh_aircell = parameters['thresh_aircell']
        thresh_dura = parameters['thresh_dura']
        thresh_bone = parameters['thresh_bone']
        n_outward_bone_check = parameters['n_outward_bone_check']

        # ----- x,y,z mesh grid of dimension ranges
        status("Generating dimension resolution matrix from image...")
        dimensions = [float(d) for d in data['image'].GetImageData().GetDimensions()]
        spacing = [float(s) for s in data['image'].GetSpacing()]
        arange = [numpy.arange(0, numpy.dot((dimensions[i] - 1), s) + s, s) for i, s in enumerate(spacing)]
        xMesh, yMesh, zMesh = numpy.meshgrid(arange[0], arange[1], arange[2])

        # ----- get triangles from outer stl file
        status("Calculating centers and normals from outer model..."); startTime = time.time()
        facets = []
        outerPoints = data['outer_stl'].GetPolyData().GetPoints().GetData()
        outerPolyData = data['outer_stl'].GetPolyData().GetPolys().GetData()
        connections = [int(outerPolyData.GetTuple1(i)) for i in xrange(outerPolyData.GetNumberOfTuples())]
        for connection in itertools.izip_longest(*[iter(connections)] * 4):
            vertices = [[outerPoints.GetValue(i*3), outerPoints.GetValue(i*3+1), outerPoints.GetValue(i*3+2)] for i in connection[1:4]]
            facet = Facet(c=[0, 0, 0], n=[0, 0, 0])
            vtk.vtkTriangle.TriangleCenter(vertices[0], vertices[1], vertices[2], facet.center)
            vtk.vtkTriangle.ComputeNormal(vertices[0], vertices[1], vertices[2], facet.normal)
            facets.append(facet)
        status("Finished " + str(len(facets)) + " facets in " + str("%.1f"%(time.time()-startTime)) + " seconds...")

        # ----- calculate
        status("Calculating thickness..."); startTime = time.time()
        for facet in facets:
            parameters = {'dimensions': dimensions, 'minimum' : [0, 0, 0], 'maximum' : [(dimensions[i]-1)*s for i, s in enumerate(spacing)]}
            outwardsIntersection = SkullThicknessMappingLogic.amanatidesWooAlgorithm(facet.center, facet.normal_outward(), parameters)
            # TODO in each direction get the voxel values in n_outward_bone_check length, then get max, then check if thats in threshold
            # if max(outwardsIntersection.value(arange(1, parameters['n_outward_bone_check']))) >= parameters['thresh_bone']:
            #   new_origin_voxel = find(g_outside >= thresh_bone, 1, 'last')
            #   origin = concat([mesh_x(1, iv_outside(new_origin_voxel, 1), 1), mesh_y(iv_outside(new_origin_voxel, 2), 1, 1), mesh_z(1, 1, iv_outside(new_origin_voxel, 3))])
            # TODO implement intersection class
            inwardsIntersection = SkullThicknessMappingLogic.amanatidesWooAlgorithm(facet.center, facet.normal_inward(), parameters)



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

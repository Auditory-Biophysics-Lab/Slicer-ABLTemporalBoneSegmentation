import slicer
import numpy
from slicer.ScriptedLoadableModule import *


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
    @staticmethod
    def process(files):
        pass
        # for each
        # get file names for image, outer, and rest of ear
        # read stl files for outer and rest of ear
        # calculate thickness data VIA cal_dist.py
        # plot output
        # return output


class SkullThicknessMappingAlgorithms:
    @staticmethod
    def amanatidesWooAlgorithm(origin=None, direction=None, image=None, grid_3d_nx=None, grid_3d_ny=None,
                               grid_3d_nz=None, grid_3d_min_bound=None, grid_3d_max_bound=None):
        # A fast and simple voxel traversal algorithm through a 3D space partition(grid)
        # Proposed by J.Amanatides and A.Woo(1987)
        # Input:    origin, direction, grid3d (grid dimensions nx, ny, nz, minBound, maxBound)
        # Author:   Jesus Mena

        flag, tMin = SkullThicknessMappingAlgorithms.rayBoxIntersection(origin, direction, grid_3d_min_bound,
                                                                        grid_3d_max_bound, nargout=2)
        if flag == 0:
            print('[!] The ray does not intersect the grid')
        else:
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
            while (x <= grid_3d_nx) and (x >= 1) and (y <= grid_3d_ny) and (y >= 1) and (z <= grid_3d_nz) and (
                    z >= 1) and t_flag:
                intersection_voxel = [x, y, z]
                voxel_value = image(y, x, z)
                t1 = [(x - 1) / grid_3d_nx, (y - 1) / grid_3d_ny, (z - 1) / grid_3d_nz]
                t2 = [x / grid_3d_nx, y / grid_3d_ny, z / grid_3d_nz]
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
        return intersection_voxel, voxel_value

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

    # @staticmethod
    # def read_stl(file_name=None):
        # # open file
        # fileOpen = fopen(file_name, 'r')
        # format = '%*s %*s %f32 %f32 %f32 \\n %*s %*s \\n %*s %f32 %f32 %f32 \\n %*s %f32 %f32 %f32 \\n %*s %f32 %f32 %f32 \\n %*s \\n %*s \\n'
        # C = textscan(fileOpen, format, 'HeaderLines', 1)
        # fclose(fileOpen)
        #
        # ravel = []
        # output = []
        #
        # # extract vertices
        # v1 = cell2mat(C(numpy.arange(4, 6)))
        # v2 = cell2mat(C(numpy.arange(7, 9)))
        # v3 = cell2mat(C(numpy.arange(10, 12)))
        # v_temp = numpy.concat([v1, v2, v3]).T
        # vertices_all = numpy.zeros(3, numel(v_temp) / 3)
        # ravel[vertices_all] = numpy.ravel(v_temp)
        # vertices_all = vertices_all.T
        # fnum = length(vertices_all) / 3
        #
        # # gets points and triangle indexes given vertex and facet number
        # c = size(vertices_all, 1)
        # # triangles with vertex id data
        # conn = numpy.zeros(3, fnum)
        # ravel[conn] = numpy.arange(1, c)
        # # now we have to keep unique points fro vertex
        # p, i, j = numpy.unique(vertices_all, 'rows', nargout=3)
        #
        # ravel[conn] = j(numpy.ravel(conn))
        # output[conn] = numpy.copy(conn.T)
        # # ijk-to-RAS TF
        # tf = numpy.concat([[- 1, 0, 0], [0, - 1, 0], [0, 0, 1]])
        # output[p] = numpy.copy((numpy.dot(tf, p.T)).T)
        # vertices_all = (numpy.dot(tf, vertices_all.T)).T
        # output[centers] = numpy.copy((vertices_all(numpy.arange(1, end(), 3), numpy.arange()) + vertices_all(numpy.arange(2, end(), 3),numpy.arange()) + vertices_all(numpy.arange(3, end(), 3), numpy.arange())) / 3)
        # output.[tri] = numpy.copy(triangulation(output.conn, output.p))
        # output.[normals] = numpy.copy(faceNormal(output.tri))
        # return output


class SkullThicknessMappingTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_SkullThicknessMapping1()

    def test_SkullThicknessMapping1(self):
        pass

#!/usr/bin/env python

from __future__ import print_function
import argparse
import sys
import slicer
import vtk

if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description="A test Python CLI")
    # parser.add_argument('--inputvalue1', metavar='N1', help="Input value 1", required=True, nargs='?', type=int)
    # parser.add_argument('--inputvalue2', metavar='N2', help="Input value 2", required=True, nargs='?', type=int)
    # parser.add_argument('--operationtype', choices=['Addition', 'Multiplication', 'Fail'], default='Addition')
    # parser.add_argument('outputfile', metavar='<outputfile>', help="Output file", nargs='?')
    # args = parser.parse_args()
    # operation = args.operationtype
    # print(args.outputfile)
    # if args.outputfile is None: raise Exception("Please specify exactly 1 output file name")
    # result = 0
    # if operation == 'Addition': result = args.inputvalue1 + args.inputvalue2
    # elif operation == 'Multiplication': result = args.inputvalue1 * args.inputvalue2
    # else: raise Exception("Unknown OperationType!")
    # with open(args.outputfile, "w") as output_f: output_f.write(str(result))

    #  create slicer interface
    # Slicer = __import__("Slicer")
    # slicer = Slicer.slicer
    for n in slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsFiducialNode"): slicer.mrmlScene.RemoveNode(n)
    #  calculate, then populate back

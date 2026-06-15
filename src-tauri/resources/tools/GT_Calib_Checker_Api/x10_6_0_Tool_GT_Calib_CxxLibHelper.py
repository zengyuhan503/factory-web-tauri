import os
import numpy as np
import random
import math as math
import time
import ctypes


class CxxCircleFeatureOne(ctypes.Structure):
    _fields_ = [
                ("iRow",ctypes.c_int),	#定义一个和.h文件一样的结构体
                ("iCol",ctypes.c_int),
                ("fPixCoordX",ctypes.c_float),
                ("fPixCoordY",ctypes.c_float),
                ("bRing",ctypes.c_bool)
                ] 
    
    #定义默认值
    def __init__(self, iRow = -1, iCol = -1, fPixCoordX = -1.0, fPixCoordY = -1.0, bRing = False):
        super(CxxCircleFeatureOne, self).__init__(iRow, iCol, fPixCoordX, fPixCoordY, bRing)
    
    def copyFromThis(self):
        return CxxCircleFeatureOne(self.iRow , self.iCol, self.fPixCoordX, self.fPixCoordY, self.bRing)



class CTCalibCxxLibHelper:


    def __init__(self, cxxLibPath):
        self.cxxLibPath = cxxLibPath
        self.cxxLib = None
        self.isInited = False

        self.sizeInAB = (ctypes.c_int * 2)()
        self.sizeInAB[0] = 10000
        self.sizeInAB[1] = 10000
        
        self.boardAPointsTmp = (CxxCircleFeatureOne * self.sizeInAB[0])()
        self.boardBPointsTmp = (CxxCircleFeatureOne * self.sizeInAB[1])()

    def init(self):

        #LoadLibrary可能是个很耗时的操作,单独拆出来
        self.cxxLib = ctypes.cdll.LoadLibrary(self.cxxLibPath)

        self.cxxLib.check_init.restype = ctypes.c_int

        self.cxxLib.check_deinit.restype = ctypes.c_int

        self.cxxLib.check_detect_circle2.restype = ctypes.c_int
        self.cxxLib.check_detect_circle2.argtypes = [
            ctypes.c_char_p,  # imgPath
            ctypes.c_int,     # cameraType
            ctypes.c_bool,    # isLeft
            ctypes.POINTER(CxxCircleFeatureOne),   #boardAPoints
            ctypes.POINTER(CxxCircleFeatureOne),   #boardBPoints
            ctypes.POINTER(ctypes.c_int),       #sizeInAB
            ctypes.POINTER(ctypes.c_int)        #sizeOutAB
        ]

        result = self.cxxLib.check_init()
        print(f"cxxLib.check_init:  result={result}")
        
        if(result != 0):
            self.isInited = False
            return False
        
        self.isInited = True
        return True
    
    def deinit(self):
        if(self.cxxLib is None):
            return True
        
        #需要清理boardAPointsTmp和boardBPointsTmp内存吗

        result = self.cxxLib.check_deinit()
        
        self.isInited = False        

        return result
        

    def detectFeatures(self, imgPath, cameraType, isLeft):

        if((self.cxxLib is None) or self.isInited == False):
            print("CTCalibCxxLibHelper, detectFeatures, lib is not valid")
            return [False, None]

        sizeOutAB = (ctypes.c_int * 2)()
        sizeOutAB[0] = -1
        sizeOutAB[1] = -1

        boardAPoints_ptr = self.boardAPointsTmp
        boardBPoints_ptr = self.boardBPointsTmp
        sizeInAB_ptr = self.sizeInAB
        sizeOutAB_ptr = sizeOutAB        

        # Call the function
        result = self.cxxLib.check_detect_circle2(
            imgPath.encode(),
            ctypes.c_int(cameraType),
            ctypes.c_bool(isLeft),
            boardAPoints_ptr,
            boardBPoints_ptr,
            sizeInAB_ptr,
            sizeOutAB_ptr
        )        

        # Print the result
        print(f"cxxLib.check_detect_circle2:  result={result}")

        if(result != 0):
            print("CTCalibCxxLibHelper, detectFeatures, fail 1")
            return [False, None]
        
        retSizeOutA = sizeOutAB_ptr[0]
        retSizeOutB = sizeOutAB_ptr[1]

        if(retSizeOutA <= 0):
            retBoardA = []
        else:
            retBoardA = [boardAPoints_ptr[idx].copyFromThis() for idx in range(retSizeOutA)]

        if(retSizeOutB <= 0):
            retBoardB = []
        else:
            retBoardB = [boardBPoints_ptr[idx].copyFromThis() for idx in range(retSizeOutB)]    

        return [True, [retBoardA, retBoardB]]
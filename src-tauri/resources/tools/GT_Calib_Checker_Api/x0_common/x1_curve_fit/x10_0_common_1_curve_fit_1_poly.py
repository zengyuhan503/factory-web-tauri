'''
Author: leven
LastEditors: leven
Description: 工具-拟合曲线-多项式拟合
                
'''
import sys
import getopt
import os
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R
import time
from datetime import datetime
import math
from matplotlib import pyplot as plt 
from decimal import Decimal, getcontext
from scipy.linalg import solve
from x0_common.x0_base.x10_0_common_0_base_numpy import  npFloat2Decemal, npDecemal2Float

class CurveFitForPoly:
    
    mPolyOrder = 10     #多项式阶数
    mResultOk = False   #拟合结果是否可用
    mCurveParams = np.array([[Decimal(0),Decimal(0)]])   #曲线参数
    mSample = np.array([[0,0]]) #distor数据采样值n*2大小数据: ref --> rel

    # mPredictY = np.array([[Decimal(0),Decimal(0)]])
    
    def __init__(self, polyOrder = 10):
        self.mPolyOrder = polyOrder
        self.mResultOk = False
    
    def fitCurve(self, sampleData):
        self.mResultOk = False
        self.mCurveParams = np.array([[Decimal(0),Decimal(0)]])
        self.mSample = np.array([[0,0]])
        print("sampleData shape=", sampleData.shape)
        if(sampleData.ndim != 2 or sampleData.shape[0] <=  self.mPolyOrder or sampleData.shape[1] != 2):
            print("sampleData size err")
            return False
        self.mSample = sampleData

        # 设置decimal的精度
        # getcontext().prec = 10

        #正式开始拟合参数
        mAtA_all = np.zeros((self.mPolyOrder + 1, self.mPolyOrder + 1), dtype=np.float64)
        mAtb_all = np.zeros((self.mPolyOrder + 1, 1), dtype=np.float64)
        mAtA_all_decimal = npFloat2Decemal(mAtA_all)
        mAtb_all_decimal = npFloat2Decemal(mAtb_all)
        for rI in range(sampleData.shape[0]):
            a = sampleData[rI,0]
            b = sampleData[rI,1]

            a_decimal = Decimal(a)
            b_decimal = Decimal(b)

            # mA = np.array([a**ord for ord in range(self.mPolyOrder + 1)], dtype=np.float64, ndmin=2)
            # mA_decimal1 = npFloat2Decemal(mA)
            if(a != 0):
                mA_decimal2 = np.array([a_decimal**ord for ord in range(self.mPolyOrder + 1)], ndmin=2)
            else:   #专门针对0时处理
                mA_decimal2 = np.array([Decimal(0) for ord in range(self.mPolyOrder + 1)], ndmin=2)
                mA_decimal2[0,0] = Decimal(1.0)                
            # print("mA_decimal2-mA_decimal1=\n", (mA_decimal2-mA_decimal1))
            # print("a=", a, ", a_decimal=", a_decimal, ", b=", b, ", mA=", mA)
            # # print("a=", a, ", b=", b, ", d_mA=", (mA_decimal2 - mA_decimal1))

            mA = mA_decimal2.reshape((1,-1))
            mAt = mA.reshape((-1,1))
            mAtA = np.matmul(mAt, mA)
            mAtb = mAt * b_decimal

            mAtA_all_decimal = mAtA_all_decimal + mAtA
            mAtb_all_decimal = mAtb_all_decimal + mAtb
        
        if(False):
            mAtA_all_inv = np.linalg.inv(mAtA_all_decimal)                  #decimal矩阵不支持求逆
            result = np.matmul(mAtA_all_inv, mAtb_all_decimal)
        elif(False):
            # result = solve(mAtA_all_decimal, mAtb_all_decimal)            #decimal矩阵不支持
            result = np.linalg.solve(mAtA_all_decimal, mAtb_all_decimal)    #decimal矩阵不支持
        else:
            # mAtA_all = npDecemal2Float(mAtA_all_decimal)
            # mAtA_all_inv = np.linalg.inv(mAtA_all)
            # mAtA_all_decimal_inv = npFloat2Decemal(mAtA_all_inv)
            # result = np.matmul(mAtA_all_decimal_inv, mAtb_all_decimal)
            mAtA_all = npDecemal2Float(mAtA_all_decimal)
            mAtb_all = npDecemal2Float(mAtb_all_decimal)
            result = solve(mAtA_all, mAtb_all)                              #还是要用QR分解或者SVD分解等方法来解,不要直接解            

        print("result shape=", result.shape, ", result=\n", result.transpose())

        self.mResultOk = True
        self.mCurveParams = npFloat2Decemal(result)

        return True

    def fitCurve2(self, sampleData):
        # sampleData = sampleData2[range(15),:]
        # sampleData = sampleData2
        # if(True):
        #     mX = np.array([x for x in range(30)], dtype=float, ndmin=1)
        #     mY = 1 + 1 * mX
        #     sampleData = np.zeros((mX.shape[0], 2), dtype=float)
        #     sampleData[:,0] = mX
        #     sampleData[:,1] = mY


        self.mResultOk = False
        self.mCurveParams = np.array([[Decimal(0),Decimal(0)]])
        self.mSample = np.array([[0,0]])
        print("sampleData shape=", sampleData.shape)
        if(sampleData.ndim != 2 or sampleData.shape[0] <=  self.mPolyOrder or sampleData.shape[1] != 2):
            print("sampleData size err")
            return False
        self.mSample = sampleData

        #正式开始拟合参数
        mA_all = np.zeros((sampleData.shape[0], self.mPolyOrder + 1), dtype=float)
        mb_all = np.zeros((sampleData.shape[0], 1), dtype=float)
        for rI in range(sampleData.shape[0]):
            a = sampleData[rI,0]
            b = sampleData[rI,1]
            mA = np.array([a**ord for ord in range(self.mPolyOrder + 1)], dtype=float, ndmin=1)
            # print("a=", a, ", b=", b, ", mA=", mA)
            mA_all[rI,:] = mA
            mb_all[rI,0] = b
        
        mAt_all = mA_all.transpose()
        mAtA_all = np.matmul(mAt_all, mA_all)
        mAtb_all = np.matmul(mAt_all, mb_all)        
        mAtA_all_inv = np.linalg.inv(mAtA_all)
        result = np.matmul(mAtA_all_inv, mAtb_all)
        result = solve(mAtA_all, mAtb_all)
        # print("mA_all=\n", mA_all)
        # print("mb_all=\n", mb_all)
        # print("mAtA_all=\n", mAtA_all)
        # print("mAtb_all=\n", mAtb_all)
        # print("mAtA_all_inv=\n", mAtA_all_inv)
        print("result shape=", result.shape, ", result=\n", result.transpose())
        
        self.mResultOk = True
        self.mCurveParams = npFloat2Decemal(result)
        return True

    '''
    description: 输入一个一维列表,作预测输出
    param {*} fromX 列表输入,只取其第0列的值
    param {*} predictY 输出结果,是一个list,只有单个元素,predictY[0]内缓存实际输出结果
    return {*} True有效, False无效
    '''
    def predict(self, fromX, predictY):
        if(not isinstance(predictY, list)):
            return False
        if(len(predictY) == 0):
            predictY.append(None)
        
        if(self.mResultOk != True):
            return False

        if(fromX.ndim < 1 or fromX.shape[0] <=  0):
            print("fromX size err")
            return False
        
        predictTmp = np.zeros((fromX.shape[0], 1), dtype=np.float64)
        # self.mPredictY = npFloat2Decemal(predictTmp)
        predictY[0] = npFloat2Decemal(predictTmp)

        for rI in range(fromX.shape[0]):
            a = fromX[rI,0]
            a_decimal = Decimal(a)
            # mA = np.array([a**ord for ord in range(self.mPolyOrder + 1)], dtype=np.float64, ndmin=2)
            if(a != 0):
                mA_decimal2 = np.array([a_decimal**ord for ord in range(self.mPolyOrder + 1)], ndmin=2)
            else:
                mA_decimal2 = np.array([Decimal(0) for ord in range(self.mPolyOrder + 1)], ndmin=2)
                mA_decimal2[0,0] = Decimal(1.0)
            mA = mA_decimal2.reshape((1,-1))
            mb = np.matmul(mA, self.mCurveParams)
            # print("a=", a, ", mA shape=", mA.shape, ", mb shape=", mb.shape, ", mb=", mb[0,0])
            # self.mPredictY[rI,0] = float(mb[0,0])
            predictY[0][rI,0] = float(mb[0,0])
        # print("self.mPredictY shape=", self.mPredictY.shape)
        print("predictY shape=", predictY[0].shape)
        return True
   
    '''
    description: 单个值预测
    param {*} fromX 输入单值
    param {*} predictY  输出结果,是一个list,只有单个元素,predictY[0]内缓存实际输出结果
    return {*} True有效, False无效
    '''
    def predictSingle(self, fromX, predictY):
        if(not isinstance(predictY, list)):
            return False
        if(len(predictY) == 0):
            predictY.append(None)
        
        if(self.mResultOk != True):
            return False
        a = fromX
        a_decimal = Decimal(a)
        if(a != 0):
            mA_decimal2 = np.array([a_decimal**ord for ord in range(self.mPolyOrder + 1)], ndmin=2)
        else:
            mA_decimal2 = np.array([Decimal(0) for ord in range(self.mPolyOrder + 1)], ndmin=2)
            mA_decimal2[0,0] = Decimal(1.0)
        mA = mA_decimal2.reshape((1,-1))
        mb = np.matmul(mA, self.mCurveParams)
        predictY[0] = float(mb[0,0])
        
        return True


'''
Author: leven
LastEditors: leven
Description: numpy相关工具函数
'''
import numpy as np
from decimal import Decimal, getcontext

def npFloat2Decemal(fromIn):
    # print("fromIn type=", fromIn.dtype)
    toOut = np.array([[Decimal(x) for x in row] for row in fromIn])
    return toOut

def npDecemal2Float(fromIn):
    toOut = np.array([[float(x) for x in row] for row in fromIn])
    return toOut
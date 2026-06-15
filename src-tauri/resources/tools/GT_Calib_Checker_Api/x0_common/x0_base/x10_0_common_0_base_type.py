'''
Author: leven
LastEditors: leven
Description: python基本类型工具
'''
import numpy as np

def tupleToInt(fromIn):
    if(len(fromIn) == 0):
        return ()
    return (int(num) for num in fromIn)

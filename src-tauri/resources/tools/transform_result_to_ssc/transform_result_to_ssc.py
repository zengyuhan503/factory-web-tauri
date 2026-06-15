#!/usr/bin/python
# -*- coding: utf-8 -*-
# python 3.x

import time
import os
import numpy as np
import json
import sys
from collections import OrderedDict

os.chdir(os.path.split(os.path.realpath(__file__))[0])

IMU_CALIBRAT_RESULT_FILE_PATH = sys.argv[1] + "/hmd_imu/imu0/Ferraris/imu0_2000-01-01_01-01.json"
CALIBRAT_RESULT_PATH = sys.argv[1] + "/hmd_camera/calibrat_result"
RETURN_STATUS_OK = "status:ok"
RETURN_STATUS_ERROR = "status:error"

icm4x6xx_1_platform_accel_fac_cal = '{"icm4x6xx_1_platform.accel.fac_cal":{"owner":"icm4x6xx","corr_mat":{"type":"grp","ver":"1","data":""},"bias":{"type":"grp","ver":"1","data":""}}}'
icm4x6xx_1_platform_accel_fac_cal_bias = '{"icm4x6xx_1_platform.accel.fac_cal.bias":{"owner":"icm4x6xx","x":{"type":"flt","ver":"1","data":"1.187634"},"y":{"type":"flt","ver":"1","data":"0.280837"},"z":{"type":"flt","ver":"1","data":"-0.174565"}}}'
icm4x6xx_1_platform_accel_fac_cal_corr_mat = '{"icm4x6xx_1_platform.accel.fac_cal.corr_mat":{"owner":"icm4x6xx","0_0":{"type":"flt","ver":"1","data":"1.000000"},"0_1":{"type":"flt","ver":"1","data":"0.000000"},"0_2":{"type":"flt","ver":"1","data":"0.000000"},"1_0":{"type":"flt","ver":"1","data":"0.000000"},"1_1":{"type":"flt","ver":"1","data":"1.000000"},"1_2":{"type":"flt","ver":"1","data":"0.000000"},"2_0":{"type":"flt","ver":"1","data":"0.000000"},"2_1":{"type":"flt","ver":"1","data":"0.000000"},"2_2":{"type":"flt","ver":"1","data":"1.000000"}}}'
icm4x6xx_1_platform_gyro_fac_cal = '{"icm4x6xx_1_platform.gyro.fac_cal":{"owner":"icm4x6xx","corr_mat":{"type":"grp","ver":"1","data":""},"bias":{"type":"grp","ver":"1","data":""}}}'
icm4x6xx_1_platform_gyro_fac_cal_bias = '{"icm4x6xx_1_platform.gyro.fac_cal.bias":{"owner":"icm4x6xx","x":{"type":"flt","ver":"1","data":"-0.011831"},"y":{"type":"flt","ver":"1","data":"0.010258"},"z":{"type":"flt","ver":"1","data":"-0.005846"}}}'
icm4x6xx_1_platform_gyro_fac_cal_corr_mat = '{"icm4x6xx_1_platform.gyro.fac_cal.corr_mat":{"owner":"icm4x6xx","0_0":{"type":"flt","ver":"1","data":"1.000000"},"0_1":{"type":"flt","ver":"1","data":"0.000000"},"0_2":{"type":"flt","ver":"1","data":"0.000000"},"1_0":{"type":"flt","ver":"1","data":"0.000000"},"1_1":{"type":"flt","ver":"1","data":"1.000000"},"1_2":{"type":"flt","ver":"1","data":"0.000000"},"2_0":{"type":"flt","ver":"1","data":"0.000000"},"2_1":{"type":"flt","ver":"1","data":"0.000000"},"2_2":{"type":"flt","ver":"1","data":"1.000000"}}}'

DEBUG_PRINT = False

def saveAccelCalibratToSscJson(imu_calibrat_data_in):
    K_a = imu_calibrat_data_in["K_a"]
    R_a = imu_calibrat_data_in["R_a"]
    accel_bias = imu_calibrat_data_in["b_a"]

    np_K_a = np.array(K_a)
    np_R_a = np.array(R_a)
    accel_corr_mat = np.matmul(np.linalg.inv(np_R_a), np_K_a)

    #for icm4x6xx_1_platform.accel.fac_cal
    key_values = json.loads(icm4x6xx_1_platform_accel_fac_cal, object_pairs_hook=OrderedDict)
    print(key_values)
    with open(CALIBRAT_RESULT_PATH + "/icm4x6xx_1_platform.accel.fac_cal", "w", encoding="utf-8") as file:
        json.dump(key_values, file, ensure_ascii=False)

    #for icm4x6xx_1_platform.accel.fac_cal.bias
    key_values = json.loads(icm4x6xx_1_platform_accel_fac_cal_bias, object_pairs_hook=OrderedDict)
    print(key_values)
    key_values["icm4x6xx_1_platform.accel.fac_cal.bias"]["x"]["data"] = format(accel_bias[0],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.bias"]["y"]["data"] = format(accel_bias[1],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.bias"]["z"]["data"] = format(accel_bias[2],"0.6f")
    print(key_values)
    with open(CALIBRAT_RESULT_PATH + "/icm4x6xx_1_platform.accel.fac_cal.bias", "w", encoding="utf-8") as file:
        json.dump(key_values, file, ensure_ascii=False)

    #for icm4x6xx_1_platform.accel.fac_cal.corr_mat
    key_values = json.loads(icm4x6xx_1_platform_accel_fac_cal_corr_mat, object_pairs_hook=OrderedDict)
    print(key_values)
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["0_0"]["data"] = format(accel_corr_mat[0][0],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["0_1"]["data"] = format(accel_corr_mat[0][1],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["0_2"]["data"] = format(accel_corr_mat[0][2],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["1_0"]["data"] = format(accel_corr_mat[1][0],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["1_1"]["data"] = format(accel_corr_mat[1][1],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["1_2"]["data"] = format(accel_corr_mat[1][2],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["2_0"]["data"] = format(accel_corr_mat[2][0],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["2_1"]["data"] = format(accel_corr_mat[2][1],"0.6f")
    key_values["icm4x6xx_1_platform.accel.fac_cal.corr_mat"]["2_2"]["data"] = format(accel_corr_mat[2][2],"0.6f")
    print(key_values)
    with open(CALIBRAT_RESULT_PATH + "/icm4x6xx_1_platform.accel.fac_cal.corr_mat", "w", encoding="utf-8") as file:
        json.dump(key_values, file, ensure_ascii=False)

def savegyroCalibratToSscJson(imu_calibrat_data_in):
    K_g = imu_calibrat_data_in["K_g"]
    R_g = imu_calibrat_data_in["R_g"]
    gyro_bias = imu_calibrat_data_in["b_g"]

    np_K_g = np.array(K_g)
    np_R_g = np.array(R_g)
    gyro_corr_mat = np.matmul(np.linalg.inv(np_R_g), np_K_g)

    #for icm4x6xx_1_platform.gyro.fac_cal
    key_values = json.loads(icm4x6xx_1_platform_gyro_fac_cal, object_pairs_hook=OrderedDict)
    print(key_values)
    with open(CALIBRAT_RESULT_PATH + "/icm4x6xx_1_platform.gyro.fac_cal", "w", encoding="utf-8") as file:
        json.dump(key_values, file, ensure_ascii=False)

    #for icm4x6xx_1_platform.gyro.fac_cal.bias
    key_values = json.loads(icm4x6xx_1_platform_gyro_fac_cal_bias, object_pairs_hook=OrderedDict)
    print(key_values)
    key_values["icm4x6xx_1_platform.gyro.fac_cal.bias"]["x"]["data"] = format(gyro_bias[0],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.bias"]["y"]["data"] = format(gyro_bias[1],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.bias"]["z"]["data"] = format(gyro_bias[2],"0.6f")
    print(key_values)
    with open(CALIBRAT_RESULT_PATH + "/icm4x6xx_1_platform.gyro.fac_cal.bias", "w", encoding="utf-8") as file:
        json.dump(key_values, file, ensure_ascii=False)

    #for icm4x6xx_1_platform.gyro.fac_cal.corr_mat
    key_values = json.loads(icm4x6xx_1_platform_gyro_fac_cal_corr_mat, object_pairs_hook=OrderedDict)
    print(key_values)
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["0_0"]["data"] = format(gyro_corr_mat[0][0],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["0_1"]["data"] = format(gyro_corr_mat[0][1],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["0_2"]["data"] = format(gyro_corr_mat[0][2],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["1_0"]["data"] = format(gyro_corr_mat[1][0],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["1_1"]["data"] = format(gyro_corr_mat[1][1],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["1_2"]["data"] = format(gyro_corr_mat[1][2],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["2_0"]["data"] = format(gyro_corr_mat[2][0],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["2_1"]["data"] = format(gyro_corr_mat[2][1],"0.6f")
    key_values["icm4x6xx_1_platform.gyro.fac_cal.corr_mat"]["2_2"]["data"] = format(gyro_corr_mat[2][2],"0.6f")
    print(key_values)
    with open(CALIBRAT_RESULT_PATH + "/icm4x6xx_1_platform.gyro.fac_cal.corr_mat", "w", encoding="utf-8") as file:
        json.dump(key_values, file, ensure_ascii=False)


def loadsFerrarisImuCalibratJsonFlie():
    if not os.path.exists(IMU_CALIBRAT_RESULT_FILE_PATH):
        sys.exit(RETURN_STATUS_ERROR)
    with open(IMU_CALIBRAT_RESULT_FILE_PATH , "r") as file:
        loads_dict = json.load(file)
    return(loads_dict)



imu_calibrate_data = loadsFerrarisImuCalibratJsonFlie()

saveAccelCalibratToSscJson(imu_calibrate_data)

savegyroCalibratToSscJson(imu_calibrate_data)

sys.exit(RETURN_STATUS_OK)
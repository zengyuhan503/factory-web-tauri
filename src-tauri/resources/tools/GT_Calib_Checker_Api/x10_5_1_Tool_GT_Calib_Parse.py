'''
Author: leven
LastEditors: leven
Description: 解析GT的n个标定文件,并作统计分析
'''

import numpy as np
import matplotlib.pyplot as plt
import sys
import getopt
import os
import numpy as np
# import pandas as pd
from scipy.spatial.transform import Rotation as R
import time
from datetime import datetime
import math
from matplotlib import pyplot as plt 
# import x10_2_ToolDistorCurve as tdc 
# from x0_common.x1_curve_fit import x10_0_common_1_curve_fit_1_poly as CurveFitPoly
import copy
import shutil

import os
import zipfile
import os
import glob
import zipfile
import shutil
import xml.etree.ElementTree as ET

target_xml_subdir = "calibDetails"
target_xml_file = "device_calibration.xml"

class TrackCamera:

    def __init__(self, cid = -1):
        self.id = cid
        self.size = np.zeros((2), dtype=float)
        self.principal_point = np.zeros((2), dtype=float)
        self.focal_length = np.zeros((2), dtype=float)
        self.model = ""
        self.radial_distortion = np.zeros((6), dtype=float)
        self.distortion_limit = 0
        self.undistortion_limit = 0

        self.translation = np.zeros((3), dtype=float)
        self.rowMajorRotationMat = np.zeros((3*3), dtype=float)

        self.delta = 0
        self.nativeSensorSize = np.zeros((2), dtype=float)
        self.crop = np.zeros((4), dtype=float)
        self.binning = np.zeros((2), dtype=float)

        self.VignettingCorrection_model = ""
        self.VignettingCorrection_center = np.zeros((2), dtype=float)
        self.VignettingCorrection_normalizer = 0
        self.VignettingCorrection_coeffs = np.zeros((3), dtype=float)


class RGBCamera:

    def __init__(self, cid = -1):
        self.id = cid      
        self.size = np.zeros((2), dtype=float)
        self.principal_point = np.zeros((2), dtype=float)
        self.focal_length = np.zeros((2), dtype=float)
        self.model = ""
        self.radial_distortion = np.zeros((6), dtype=float)
        self.distortion_limit = 0
        self.undistortion_limit = 0

        self.translation = np.zeros((3), dtype=float)
        self.rowMajorRotationMat = np.zeros((3*3), dtype=float)

        self.isRollingShutter = ""
        self.linetime = 0

        self.delta = 0
        self.nativeSensorSize = np.zeros((2), dtype=float)
        self.crop = np.zeros((4), dtype=float)
        self.binning = np.zeros((2), dtype=float)

        self.VignettingCorrection_model = ""
        self.VignettingCorrection_center = np.zeros((2), dtype=float)
        self.VignettingCorrection_normalizer = 0
        self.VignettingCorrection_coeffs = np.zeros((3), dtype=float)

class ImuInfo:
    
    def __init__(self):
        
        self.ombc = np.zeros((3), dtype=float)
        self.tbc = np.zeros((3), dtype=float)
        self.aBias = np.zeros((3), dtype=float)
        self.wBias = np.zeros((3), dtype=float)
        self.ka = np.zeros((3), dtype=float)
        self.kg = np.zeros((3), dtype=float)
        self.na = np.zeros((3), dtype=float)
        self.ng = np.zeros((3), dtype=float)
        self.ombg = np.zeros((3), dtype=float)
        self.accelDelta = 0
        self.delta = 0
        self.movingAccelNoise = 0
        self.movingGyroNoise = 0
        

class GTCalibInfo:

    def __init__(self):

        self.tag = "unkown"
        self.trackingA = TrackCamera(0)
        self.trackingB = TrackCamera(1)
        self.ctrl_trackingA = TrackCamera(2)
        self.ctrl_trackingB = TrackCamera(3)
        self.rgb_left = RGBCamera(4)
        self.rgb_right = RGBCamera(5)
        self.imu_info = ImuInfo()

'''
description: 将输入字符串解析到一维的numpy数组中
return {*}
'''
def decodeStr2NpArray1D(inStrArray, outNpArray):
    if len(inStrArray) == 0:
        print("inStrArray=", inStrArray, "outNpArray=", outNpArray)
        return False
    numArray = inStrArray.split()
    if(len(numArray) == 0 or len(numArray) != len(outNpArray)):
        print("inStrArray=", inStrArray, "outNpArray=", outNpArray)
        return False
    for idx in range(len(numArray)):
        outNpArray[idx] = float(numArray[idx])
    return True


'''
description: 解析xml标定文件到结构对象
param {*} xml_dir
param {*} calibInfo
return {*}
'''
def parse_calib_xml(xml_dir, calibInfo):

    file_path = xml_dir + "/" + target_xml_subdir + "/" + target_xml_file
    if(not os.path.exists(file_path)):
        print("posePath is invalid:", file_path)
        return False
    
    # 解析XML文件
    tree = ET.parse(file_path)
    root = tree.getroot()
    # 获取DeviceConfiguration元素的deviceUID属性值
    device_uid = root.attrib['deviceUID']
    # print(f"Device UID: {device_uid}")


    # 遍历每个Camera元素
    for camera in root.iter('Camera'):
        cam_name = camera.get('cam_name')
        name = camera.get('name')
        id = camera.get('id')
        id_int = int(id)
        # print(f"Camera: cam_name={cam_name}, name={name}, id={id}")

        if id_int == 0:
            curCameraInfo = calibInfo.trackingA
        elif id_int == 1:
            curCameraInfo = calibInfo.trackingB
        elif id_int == 2:
            curCameraInfo = calibInfo.ctrl_trackingA
        elif id_int == 3:
            curCameraInfo = calibInfo.ctrl_trackingB
        elif id_int == 4:
            curCameraInfo = calibInfo.rgb_left
        elif id_int == 5:
            curCameraInfo = calibInfo.rgb_right
        else:
            print("camera id err:", id_int)
            return False

        # 获取Calibration子元素的属性(共同)
        calibration = camera.find('Calibration')
        if (decodeStr2NpArray1D(calibration.get('size'), curCameraInfo.size) == False):
            return False        
        if (decodeStr2NpArray1D(calibration.get('principal_point'), curCameraInfo.principal_point) == False):
            return False
        if (decodeStr2NpArray1D(calibration.get('focal_length'), curCameraInfo.focal_length) == False):
            return False
        curCameraInfo.model = calibration.get('model')
        if (decodeStr2NpArray1D(calibration.get('radial_distortion'), curCameraInfo.radial_distortion) == False):
            return False
        curCameraInfo.distortion_limit = float(calibration.get('distortion_limit'))
        curCameraInfo.undistortion_limit = float(calibration.get('undistortion_limit'))

        # 获取Rig子元素的属性(共同)
        rig = camera.find('Rig')
        if (decodeStr2NpArray1D(rig.get('translation'), curCameraInfo.translation) == False):
            return False        
        if (decodeStr2NpArray1D(rig.get('rowMajorRotationMat'), curCameraInfo.rowMajorRotationMat) == False):
            return False

        # 获取TimeAlignment子元素的属性(共同)
        timeAlignment = camera.find('TimeAlignment')
        curCameraInfo.delta = float(timeAlignment.get('delta'))

        # 获取TimeAlignment子元素的属性(共同)
        vignettingCorrection = camera.find('VignettingCorrection')
        curCameraInfo.VignettingCorrection_model = vignettingCorrection.get("model")
        if (decodeStr2NpArray1D(vignettingCorrection.get('center'), curCameraInfo.VignettingCorrection_center) == False):
            return False
        curCameraInfo.VignettingCorrection_normalizer = float(vignettingCorrection.get("normalizer"))
        if (decodeStr2NpArray1D(vignettingCorrection.get('coeffs'), curCameraInfo.VignettingCorrection_coeffs) == False):
            return False
        
        if id_int in [0,1,4,5]:
            # 获取CaptureDetails子元素的属性(只有0,1,4,5有)
            captureDetails = camera.find('CaptureDetails')
            curCameraInfo.nativeSensorSize[0] = float(captureDetails.get("nativeSensorWidth"))
            curCameraInfo.nativeSensorSize[1] = float(captureDetails.get("nativeSensorHeight"))

            curCameraInfo.crop[0] = float(captureDetails.get("cropL"))
            curCameraInfo.crop[1] = float(captureDetails.get("cropR"))
            curCameraInfo.crop[2] = float(captureDetails.get("cropT"))
            curCameraInfo.crop[3] = float(captureDetails.get("cropB"))
            
            curCameraInfo.binning[0] = float(captureDetails.get("binningH"))
            curCameraInfo.binning[1] = float(captureDetails.get("binningV"))

        if id_int in [4,5]:
            # 获取RollingShutter子元素的属性(只有4,5有)
            rollingShutter = camera.find('RollingShutter')
            curCameraInfo.isRollingShutter = rollingShutter.get("isRollingShutter")
            curCameraInfo.linetime = float(rollingShutter.get("linetime"))


        curImuInfo = calibInfo.imu_info
        sFConfig = root.find("SFConfig")
        stateinit = sFConfig.find("Stateinit")
        if (decodeStr2NpArray1D(stateinit.get('ombc'), curImuInfo.ombc) == False):
            return False        
        if (decodeStr2NpArray1D(stateinit.get('tbc'), curImuInfo.tbc) == False):
            return False   
        if (decodeStr2NpArray1D(stateinit.get('aBias'), curImuInfo.aBias) == False):
            return False   
        if (decodeStr2NpArray1D(stateinit.get('wBias'), curImuInfo.wBias) == False):
            return False   
        if (decodeStr2NpArray1D(stateinit.get('ka'), curImuInfo.ka) == False):
            return False   
        if (decodeStr2NpArray1D(stateinit.get('kg'), curImuInfo.kg) == False):
            return False   
        if (decodeStr2NpArray1D(stateinit.get('na'), curImuInfo.na) == False):
            return False   
        if (decodeStr2NpArray1D(stateinit.get('ng'), curImuInfo.ng) == False):
            return False   
        if (decodeStr2NpArray1D(stateinit.get('ombg'), curImuInfo.ombg) == False):
            return False   
        curImuInfo.accelDelta = float(stateinit.get("accelDelta"))
        curImuInfo.delta = float(stateinit.get("delta"))
        
        iMUNoise = sFConfig.find("IMUNoise")
        curImuInfo.movingAccelNoise = float(iMUNoise.get("movingAccelNoise"))
        curImuInfo.movingGyroNoise = float(iMUNoise.get("movingGyroNoise"))

    return True


#统计相机标定的主点坐标差异
# x横坐标是标定文件序号
# y1: 是两个tracking相机主点均值
# y2: 是两个tracking相机主点方差
# y3: 是两个ctrl-tracking相机主点均值
# y4: 是两个ctrl-tracking相机主点方差
# y5: 是两个rgb相机主点均值
# y6: 是两个rgb相机主点方差
# def showPrincipalPoint(calibInfoAll):

#     print("="*150)
#     print("统计相机标定的主点坐标差异")
#     print("="*150)

#     size = len(calibInfoAll)
#     x = np.array(range(size))
#     y1 = np.zeros((size,2), dtype=float)
#     y2 = np.zeros((size,2), dtype=float)
#     y3 = np.zeros((size,2), dtype=float)
#     y4 = np.zeros((size,2), dtype=float)
#     y5 = np.zeros((size,2), dtype=float)
#     y6 = np.zeros((size,2), dtype=float)

#     for idx in range(size):
#         curCalibInfo = calibInfoAll[idx]
#         y1[idx] = (curCalibInfo.trackingA.principal_point + curCalibInfo.trackingB.principal_point)*0.5    
#         y2[idx] = (0.5*((curCalibInfo.trackingA.principal_point-y1[idx])**2 + (curCalibInfo.trackingB.principal_point-y1[idx])**2))**0.5
#         y3[idx] = (curCalibInfo.ctrl_trackingA.principal_point + curCalibInfo.ctrl_trackingB.principal_point)*0.5
#         y4[idx] = (0.5*((curCalibInfo.ctrl_trackingA.principal_point-y3[idx])**2 + (curCalibInfo.ctrl_trackingB.principal_point-y3[idx])**2))**0.5
#         y5[idx] = (curCalibInfo.rgb_left.principal_point + curCalibInfo.rgb_right.principal_point)*0.5
#         y6[idx] = (0.5*((curCalibInfo.rgb_left.principal_point-y5[idx])**2 + (curCalibInfo.rgb_right.principal_point-y5[idx])**2))**0.5

#     plt.title("principal_point-mean")
#     plt.xlabel("device")
#     plt.ylabel("coordinate-mean")
#     plt.plot(x, y1[:,0], label = "tracking-x")
#     plt.plot(x, y3[:,0], label = "ctrl-tracking-x")
#     # plt.plot(x, y5[:,0], label = "rgb-x")
#     plt.legend()
#     plt.show()

#     plt.title("principal_point-mean")
#     plt.xlabel("device")
#     plt.ylabel("coordinate-mean")
#     plt.plot(x, y1[:,1], label = "tracking-y")
#     plt.plot(x, y3[:,1], label = "ctrl-tracking-y")
#     # plt.plot(x, y5[:,1], label = "rgb-y")
#     plt.legend()
#     plt.show()


#     plt.title("principal_point-rmse")
#     plt.xlabel("device")
#     plt.ylabel("coordinate-rmse")
#     plt.plot(x, y2[:,0], label = "tracking-x")
#     plt.plot(x, y4[:,0], label = "ctrl-tracking-x")
#     plt.plot(x, y6[:,0], label = "rgb-x")
#     plt.legend()
#     plt.show()

#     plt.title("principal_point-rmse")
#     plt.xlabel("device")
#     plt.ylabel("coordinate-rmse")
#     plt.plot(x, y2[:,1], label = "tracking-y")
#     plt.plot(x, y4[:,1], label = "ctrl-tracking-y")
#     plt.plot(x, y6[:,1], label = "rgb-y")
#     plt.legend()
#     plt.show()
def showPrincipalPoint(calibInfoAll):

    print("="*150)
    # print("统计相机标定的主点坐标差异")
    print("make statistics on differences about the camera calibrated principal points")
    print("="*150)

    size = len(calibInfoAll)
    x = np.array(range(size))
    y1 = np.zeros((size,2), dtype=float)
    y2 = np.zeros((size,2), dtype=float)
    y3 = np.zeros((size,2), dtype=float)
    y4 = np.zeros((size,2), dtype=float)
    y5 = np.zeros((size,2), dtype=float)
    y6 = np.zeros((size,2), dtype=float)

    for idx in range(size):
        curCalibInfo = calibInfoAll[idx]
        y1[idx] = (curCalibInfo.trackingA.principal_point + curCalibInfo.trackingB.principal_point)*0.5    
        y2[idx] = (0.5*((curCalibInfo.trackingA.principal_point-y1[idx])**2 + (curCalibInfo.trackingB.principal_point-y1[idx])**2))**0.5
        y3[idx] = (curCalibInfo.ctrl_trackingA.principal_point + curCalibInfo.ctrl_trackingB.principal_point)*0.5
        y4[idx] = (0.5*((curCalibInfo.ctrl_trackingA.principal_point-y3[idx])**2 + (curCalibInfo.ctrl_trackingB.principal_point-y3[idx])**2))**0.5
        y5[idx] = (curCalibInfo.rgb_left.principal_point + curCalibInfo.rgb_right.principal_point)*0.5
        y6[idx] = (0.5*((curCalibInfo.rgb_left.principal_point-y5[idx])**2 + (curCalibInfo.rgb_right.principal_point-y5[idx])**2))**0.5

    plt.title("principal_point-coordinate_mean")
    plt.xlabel("device")
    plt.ylabel("coordinate-mean")
    plt.plot(x, y1[:,0], label = "tracking-x", color='r')
    plt.plot(x, y1[:,1], label = "tracking-y", color='r', linestyle='--')
    plt.plot(x, y3[:,0], label = "ctrl-tracking-x", color='g')
    plt.plot(x, y3[:,1], label = "ctrl-tracking-y", color='g', linestyle='--')
    plt.plot(x, y5[:,0], label = "rgb-x", color='b')
    plt.plot(x, y5[:,1], label = "rgb-y", color='b', linestyle='--')
    plt.legend()
    plt.show()

    plt.title("principal_point-coordinate_rmse")
    plt.xlabel("device")
    plt.ylabel("coordinate-rmse")
    plt.plot(x, y2[:,0], label = "tracking-x", color='r')
    plt.plot(x, y2[:,1], label = "tracking-y", color='r', linestyle='--')    
    plt.plot(x, y4[:,0], label = "ctrl-tracking-x", color='g')
    plt.plot(x, y4[:,1], label = "ctrl-tracking-y", color='g', linestyle='--')
    plt.plot(x, y6[:,0], label = "rgb-x", color='b')
    plt.plot(x, y6[:,1], label = "rgb-y", color='b', linestyle='--')
    plt.legend()
    plt.show()


#统计相机标定的焦距坐标差异
# x横坐标是标定文件序号
# y1: 是两个tracking相机焦距均值
# y2: 是两个tracking相机焦距方差
# y3: 是两个ctrl-tracking相机焦距均值
# y4: 是两个ctrl-tracking相机焦距方差
# y5: 是两个rgb相机焦距均值
# y6: 是两个rgb相机焦距方差
def showFocalLength(calibInfoAll):

    print("="*150)
    # print("统计相机标定的焦距坐标差异")
    print("make statistics on differences about the camera calibrated focus points")
    print("="*150)

    size = len(calibInfoAll)
    x = np.array(range(size))
    y1 = np.zeros((size,2), dtype=float)
    y2 = np.zeros((size,2), dtype=float)
    y3 = np.zeros((size,2), dtype=float)
    y4 = np.zeros((size,2), dtype=float)
    y5 = np.zeros((size,2), dtype=float)
    y6 = np.zeros((size,2), dtype=float)

    for idx in range(size):
        curCalibInfo = calibInfoAll[idx]
        y1[idx] = (curCalibInfo.trackingA.focal_length + curCalibInfo.trackingB.focal_length)*0.5    
        y2[idx] = (0.5*((curCalibInfo.trackingA.focal_length-y1[idx])**2 + (curCalibInfo.trackingB.focal_length-y1[idx])**2))**0.5
        y3[idx] = (curCalibInfo.ctrl_trackingA.focal_length + curCalibInfo.ctrl_trackingB.focal_length)*0.5
        y4[idx] = (0.5*((curCalibInfo.ctrl_trackingA.focal_length-y3[idx])**2 + (curCalibInfo.ctrl_trackingB.focal_length-y3[idx])**2))**0.5
        y5[idx] = (curCalibInfo.rgb_left.focal_length + curCalibInfo.rgb_right.focal_length)*0.5
        y6[idx] = (0.5*((curCalibInfo.rgb_left.focal_length-y5[idx])**2 + (curCalibInfo.rgb_right.focal_length-y5[idx])**2))**0.5

    plt.title("focal_length-coordinate_mean")
    plt.xlabel("device")
    plt.ylabel("coordinate-mean")
    plt.plot(x, y1[:,0], label = "tracking-x", color='r')
    plt.plot(x, y1[:,1], label = "tracking-y", color='r', linestyle='--')
    plt.plot(x, y3[:,0], label = "ctrl-tracking-x", color='g')
    plt.plot(x, y3[:,1], label = "ctrl-tracking-y", color='g', linestyle='--')
    plt.plot(x, y5[:,0], label = "rgb-x", color='b')
    plt.plot(x, y5[:,1], label = "rgb-y", color='b', linestyle='--')
    plt.legend()
    plt.show()

    plt.title("focal_length-coordinate_rmse")
    plt.xlabel("device")
    plt.ylabel("coordinate-rmse")
    plt.plot(x, y2[:,0], label = "tracking-x", color='r')
    plt.plot(x, y2[:,1], label = "tracking-y", color='r', linestyle='--')    
    plt.plot(x, y4[:,0], label = "ctrl-tracking-x", color='g')
    plt.plot(x, y4[:,1], label = "ctrl-tracking-y", color='g', linestyle='--')
    plt.plot(x, y6[:,0], label = "rgb-x", color='b')
    plt.plot(x, y6[:,1], label = "rgb-y", color='b', linestyle='--')
    plt.legend()
    plt.show()


#统计相机标定的晕影坐标差异
# x横坐标是标定文件序号
# y1: 是两个tracking相机晕影均值
# y2: 是两个tracking相机晕影方差
# y3: 是两个ctrl-tracking相机晕影均值
# y4: 是两个ctrl-tracking相机晕影方差
# y5: 是两个rgb相机晕影均值
# y6: 是两个rgb相机晕影方差
def showVignetting(calibInfoAll):

    print("="*150)
    # print("统计相机标定的晕影坐标差异")
    print("make statistics on differences about the camera calibrated vignetting points")
    print("="*150)

    size = len(calibInfoAll)
    x = np.array(range(size))
    y1 = np.zeros((size,2), dtype=float)
    y2 = np.zeros((size,2), dtype=float)
    y3 = np.zeros((size,2), dtype=float)
    y4 = np.zeros((size,2), dtype=float)
    y5 = np.zeros((size,2), dtype=float)
    y6 = np.zeros((size,2), dtype=float)

    for idx in range(size):
        curCalibInfo = calibInfoAll[idx]
        y1[idx] = (curCalibInfo.trackingA.VignettingCorrection_center + curCalibInfo.trackingB.VignettingCorrection_center)*0.5    
        y2[idx] = (0.5*((curCalibInfo.trackingA.VignettingCorrection_center-y1[idx])**2 + (curCalibInfo.trackingB.VignettingCorrection_center-y1[idx])**2))**0.5
        y3[idx] = (curCalibInfo.ctrl_trackingA.VignettingCorrection_center + curCalibInfo.ctrl_trackingB.VignettingCorrection_center)*0.5
        y4[idx] = (0.5*((curCalibInfo.ctrl_trackingA.VignettingCorrection_center-y3[idx])**2 + (curCalibInfo.ctrl_trackingB.VignettingCorrection_center-y3[idx])**2))**0.5
        y5[idx] = (curCalibInfo.rgb_left.VignettingCorrection_center + curCalibInfo.rgb_right.VignettingCorrection_center)*0.5
        y6[idx] = (0.5*((curCalibInfo.rgb_left.VignettingCorrection_center-y5[idx])**2 + (curCalibInfo.rgb_right.VignettingCorrection_center-y5[idx])**2))**0.5

    plt.title("VignettingCorrection_center-coordinate_mean")
    plt.xlabel("device")
    plt.ylabel("coordinate-mean")
    plt.plot(x, y1[:,0], label = "tracking-x", color='r')
    plt.plot(x, y1[:,1], label = "tracking-y", color='r', linestyle='--')
    plt.plot(x, y3[:,0], label = "ctrl-tracking-x", color='g')
    plt.plot(x, y3[:,1], label = "ctrl-tracking-y", color='g', linestyle='--')
    plt.plot(x, y5[:,0], label = "rgb-x", color='b')
    plt.plot(x, y5[:,1], label = "rgb-y", color='b', linestyle='--')
    plt.legend()
    plt.show()

    plt.title("VignettingCorrection_center-coordinate_rmse")
    plt.xlabel("device")
    plt.ylabel("coordinate-rmse")
    plt.plot(x, y2[:,0], label = "tracking-x", color='r')
    plt.plot(x, y2[:,1], label = "tracking-y", color='r', linestyle='--')    
    plt.plot(x, y4[:,0], label = "ctrl-tracking-x", color='g')
    plt.plot(x, y4[:,1], label = "ctrl-tracking-y", color='g', linestyle='--')
    plt.plot(x, y6[:,0], label = "rgb-x", color='b')
    plt.plot(x, y6[:,1], label = "rgb-y", color='b', linestyle='--')
    plt.legend()
    plt.show()


def traverse_xml_files(directory):
    contents = os.listdir(directory)

    calibInfoAll = []   #缓存所有解析出来的标定数据

    for item in contents:
        item_path = os.path.join(directory, item)
        if not os.path.isdir(item_path):
            continue
        
        calibInfo = GTCalibInfo()
        calibInfo.tag = item
        xml_file = item_path + "/" + target_xml_subdir + "/" + target_xml_file
        print("prepare to process file:", xml_file)
        if (parse_calib_xml(item_path, calibInfo) == False):
            print("fail!")
            continue
        print("success:", calibInfo.tag)
        calibInfoAll.append(calibInfo)

    print("="*150)
    print("valid calib size:", len(calibInfoAll))
    
    for idx in range(len(calibInfoAll)):
        print("x={}, tag={}".format(idx, calibInfoAll[idx].tag))

    showPrincipalPoint(calibInfoAll)
    showFocalLength(calibInfoAll)

    showVignetting(calibInfoAll)


def traverse_zip_files(directory, output_directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.zip'):
                file_path = os.path.join(root, file)
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    # 在这里可以对zip文件进行操作，比如解压缩或读取文件内容
                    print(f"process zip file：{file_path}")
                    # zip_ref.extractall(output_directory)
                    # 获取zip文件的基本名称（不包含路径和扩展名）
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    # 创建输出目录，名称与zip文件相同
                    output_path = os.path.join(output_directory, base_name)
                    os.makedirs(output_path, exist_ok=True)
                    # 解压缩zip文件到输出目录
                    zip_ref.extractall(output_path)
                    # # 例如，打印zip文件中的文件列表
                    # for name in zip_ref.namelist():
                    #     print(name)

if __name__ == '__main__':

    # 指定目录路径
    directory_path = '/path/to/directory'
    directory_out = '/path/to/directory'

    if(len(sys.argv) > 1):
        mArgv = sys.argv[1:]
        try:
            opts, args = getopt.getopt(mArgv, "f:o:", ["file=", "out_dir="])
        except:
            print("read sys.argv fail!")
        for opt, arg in opts:
            if(opt in ['-f', '--file']):
                directory_path = arg
            if(opt in ['-o', '--out_dir']):
                directory_out = arg    

    # if(not os.path.exists(directory_path)):
    #     print("posePath is invalid:", directory_path)
    #     raise SystemExit
    if(not os.path.exists(directory_out)):
        print("posePath is invalid:", directory_out)
        raise SystemExit

    # 调用函数遍历指定目录下的所有zip文件并解压到指定目录下
    # traverse_zip_files(directory_path, directory_out)

    traverse_xml_files(directory_out)
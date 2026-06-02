#!/usr/bin/python
# -*- coding: utf-8 -*-
# python 3.x

import time
import os
import sys
import subprocess

from runCalibration import run_calib
from captureData import generate_meta_info
from addVirtualRgbConfig import insertRgbConfig

os.chdir(os.path.split(os.path.realpath(__file__))[0])

calibApp = "../tools/qvr_calib/XRCalib"
targetConfig = "../tools/qvr_calib/config/Target-config.xml"

VQ910_CalibConfig_1 = "../tools/qvr_calib/config/Vq910_XRCalib-config.xml"
VQ910_Rgb_CalibConfig_2 = "../tools/qvr_calib/config/Vq910_XRCalib_Rgb-config.xml"
VQ920_CalibConfig_3 = "../tools/qvr_calib/config/Vq920_XRCalib-config.xml"
VQ920_Rgb_CalibConfig_4 = "../tools/qvr_calib/config/Vq920_XRCalib_Rgb-config.xml"
VQ920_Hand_CalibConfig_5 = "../tools/qvr_calib/config/Vq920_XRCalib_Hand-config.xml"
VQ920_Rgb_Hand_CalibConfig_6 = "../tools/qvr_calib/config/Vq920_XRCalib_Rgb_Hand-config.xml"
VQ930_CalibConfig_7 = "../tools/qvr_calib/config/Vq930_XRCalib-config.xml"
VQ930_Rgb_CalibConfig_8 = "../tools/qvr_calib/config/Vq930_XRCalib_Rgb-config.xml"
VQ930_Tof_CalibConfig_9 = "../tools/qvr_calib/config/Vq930_XRCalib_Tof-config.xml"
VQ930_Tof_Rgb_CalibConfig_10 = "../tools/qvr_calib/config/Vq930_XRCalib_Rgb_Tof-config.xml"

RETURN_STATUS_OK = "status:ok"
RETURN_STATUS_ERROR = "status:error"

DEBUG_PRINT = False
have_rgb = False
camera_layout_type = "0"

def getDeviceId():
    cpu_id = os.popen("adb shell cat /sys/devices/soc0/serial_number").readlines()
    device_id=cpu_id[0]
    return (device_id.split()[0])

def generate_meta(host_capture_dir):
    camera_folders = os.listdir(host_capture_dir)
    for cameraFolder in camera_folders:
        if 'Camera' in cameraFolder:
            generate_meta_info(os.path.join(host_capture_dir, cameraFolder))

def detect_MetaInfo_xml_orig(dir_path):
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            if filename == "MetaInfo.xml.orig":
                return True
    return False

# GT_Calib_Checker_Api 输入参数
#-f 执行功能:     携带值:[1:只check两个RGB相机光轴夹角][2:只check两个RGB相机图像的极线距离Err][3:同时check1和check2]
#-d 数据集路径:   携带值:["/xxx/qvrdataset"]
#-a check光轴夹角阈值:  携带值:[单位:角度]
#-e check图像的极线距离Err阈值:  携带值:[单位:像素]
#-l RGB左相机是否鱼眼模型   携带值:空
#-r RGB右相机是否鱼眼模型   携带值:空

# GT_Calib_Checker_Api 返回值
# 0:通过check
# 1:输入参数有误
# 2:check光轴夹角，执行有误
# 3:check光轴夹角，未通过check
# 4:check极线距离Err，执行有误
# 5:check极线距离Err，未通过check
def runGtCalibChecker(qvr_datasete_dir):
    calibDir = os.path.dirname(qvr_datasete_dir)
    GT_CALIB_CHECKER_CMD = "python3 ../tools/GT_Calib_Checker_Api/GT_Calib_Checker_Api.py " + "-a 3 -f 1 -d " + calibDir
    gt_check_result = 0

    if os.path.exists("../tools/GT_Calib_Checker_Api/GT_Calib_Checker_Api.py"):
        print(GT_CALIB_CHECKER_CMD)
        gt_check_result = os.system(GT_CALIB_CHECKER_CMD)
        gt_check_result = gt_check_result >> 8
        if gt_check_result > 0:
            print(str("RGB夹角检测不通过！ gt_check_result= ") + str(gt_check_result))
            exit(RETURN_STATUS_ERROR + " + RGB光轴夹角检测不通过！")
        else:
            print(str("RGB夹角检测通过！ gt_check_result= ") + str(gt_check_result))
    else:
        print(str("RGB夹角检测工具不存在 或者 无执行权限！"))
        exit(RETURN_STATUS_ERROR + " + RGB夹角检测工具不存在 或者 无执行权限！")

def runVerify_qvr_calibrate(qvr_datasete_dir):
    calibDir = os.path.dirname(qvr_datasete_dir)
    QVR_CHECKER_CMD = "source ../tools/verify_qvr_calibrate_result/verify_qvr_calibrate.sh " + calibDir
    qvr_check_result = 0

    if os.path.exists("../tools/verify_qvr_calibrate_result/verify_qvr_calibrate.sh"):
        print(QVR_CHECKER_CMD)
        result = subprocess.run(["bash", "../tools/verify_qvr_calibrate_result/verify_qvr_calibrate.sh", calibDir], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        qvr_check_result = result.returncode
        if qvr_check_result > 0:
            print(str("QVR校准结果验证不通过！ qvr_check_result= ") + str(qvr_check_result))
            exit(RETURN_STATUS_ERROR + " + QVR校准结果验证不通过！")
        else:
            print(str("QVR校准结果验证通过！ qvr_check_result= ") + str(qvr_check_result))
    else:
        print(str("QVR校准结果验证工具不存在!"))
        exit(RETURN_STATUS_ERROR + " + QVR校准结果验证工具不存在!")

if __name__ == '__main__':

    if len(sys.argv) == 4:
        have_rgb = sys.argv[2] == "1"
    else:
        print(str("参数传入错误"))
        sys.exit(RETURN_STATUS_ERROR + " + 参数传入错误")

    CALIBRAT_QVR_DATASET_PATH = sys.argv[1]
    camera_layout_type = sys.argv[3]

#    if not (os.path.exists(CALIBRAT_QVR_DATASET_PATH+"/Camera8/MetaInfo.xml") and os.path.exists(CALIBRAT_QVR_DATASET_PATH+"/Camera9/MetaInfo.xml")):
#        print(str("6dof摄像头MetaInfo不存在！"))
#        sys.exit(RETURN_STATUS_ERROR)
#
#    if have_rgb and (not (os.path.exists(CALIBRAT_QVR_DATASET_PATH+"/Camera4/MetaInfo.xml") and os.path.exists(CALIBRAT_QVR_DATASET_PATH+"/Camera5/MetaInfo.xml"))):
#        print(str("RGB摄像头MetaInfo不存在！"))
#        sys.exit(RETURN_STATUS_ERROR)

    SOC_serial = getDeviceId()
    qvr_dataset_path = CALIBRAT_QVR_DATASET_PATH
    calibDir = os.path.dirname(qvr_dataset_path)
    CALIBRAT_QVR_CALIB_FILE = calibDir + "/device_calibration.xml"
    CALIBRAT_QVR_CALIB_CALIBDETAILS_FILE = calibDir + "/calibDetails/device_calibration.xml"
    validateRobotArmTrajectory = True
    excludeID = False

    if detect_MetaInfo_xml_orig(qvr_dataset_path) == True :
        print("这个数据集已经被计算过，请重新抓取数据集！")
        exit(RETURN_STATUS_ERROR + " + 数据集过期")

    if not os.path.exists(calibApp):
        print("没有XRCalib，请拷贝XRCalib到：skycalib\\tools\\qvr_calib, 并修改为可执行权限")
        print("没有XRCalib，请拷贝XRCalib到：skycalib\\tools\\qvr_calib, 并修改为可执行权限")
        print("没有XRCalib，请拷贝XRCalib到：skycalib\\tools\\qvr_calib, 并修改为可执行权限")
        exit(RETURN_STATUS_ERROR + " + XRCalib工具不存在")

    generate_meta(qvr_dataset_path)

    if have_rgb:
        if camera_layout_type == "2":
            print(str("标定baseline 文件："), VQ910_Rgb_CalibConfig_2)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ910_Rgb_CalibConfig_2,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "4":
            print(str("标定baseline 文件："), VQ920_Rgb_CalibConfig_4)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ920_Rgb_CalibConfig_4,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "6":
            print(str("标定baseline 文件："), VQ920_Rgb_Hand_CalibConfig_6)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ920_Rgb_Hand_CalibConfig_6,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "8":
            print(str("标定baseline 文件："), VQ930_Rgb_CalibConfig_8)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ930_Rgb_CalibConfig_8,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "10":
            print(str("标定baseline 文件："), VQ930_Tof_Rgb_CalibConfig_10)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ930_Tof_Rgb_CalibConfig_10,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        else:
            print("RGB参数与摄像头布局参数不匹配！")
            exit(RETURN_STATUS_ERROR + " + 系统配置与摄像头不匹配")
    else:
        if camera_layout_type == "1":
            print(str("标定baseline 文件："), VQ910_CalibConfig_1)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ910_CalibConfig_1,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "3":
            print(str("标定baseline 文件："), VQ920_CalibConfig_3)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ920_CalibConfig_3,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "5":
            print(str("标定baseline 文件："), VQ920_Hand_CalibConfig_5)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ920_Hand_CalibConfig_5,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "7":
            print(str("标定baseline 文件："), VQ930_CalibConfig_7)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ930_CalibConfig_7,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        elif camera_layout_type == "9":
            print(str("标定baseline 文件："), VQ930_Tof_CalibConfig_9)
            run_calib(SOC_serial, calibDir, None, calibApp, VQ930_Tof_CalibConfig_9,
                  targetConfig, qvr_dataset_path, validateRobotArmTrajectory, excludeID)
        else:
            print("RGB参数与摄像头布局参数不匹配！")
            exit(RETURN_STATUS_ERROR + " + 系统配置与摄像头不匹配")

    if not os.path.exists(CALIBRAT_QVR_CALIB_FILE):
        print("QVR生成标定文件失败")
        exit(RETURN_STATUS_ERROR + " + 生成标定文件失败")
    else:
        runVerify_qvr_calibrate(qvr_dataset_path)

        if not have_rgb:
            if camera_layout_type < "7":
                rs = insertRgbConfig(CALIBRAT_QVR_CALIB_FILE)
                if not rs:
                    print("插入RGB摄像头配置失败1")
                    exit(RETURN_STATUS_ERROR + " + 插入RGB校准配置失败1")
                rs = insertRgbConfig(CALIBRAT_QVR_CALIB_CALIBDETAILS_FILE)
                if not rs:
                    print("插入RGB摄像头配置失败2")
                    exit(RETURN_STATUS_ERROR + " + 插入RGB校准配置失败2")
        elif camera_layout_type == "4" or camera_layout_type == "6":
            print("vq920 RGB 摄像头夹角检测")
            runGtCalibChecker(qvr_dataset_path)
        elif camera_layout_type == "8" or camera_layout_type == "10":
            print("vq930 RGB 摄像头夹角检测")
            #runGtCalibChecker(qvr_dataset_path)

    sys.exit(RETURN_STATUS_OK)

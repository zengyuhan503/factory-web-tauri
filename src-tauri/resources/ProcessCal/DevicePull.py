#!/usr/bin/python
# -*- coding: utf-8 -*-
# python 3.x

import os
import sys
import shutil
import datetime
import fnmatch

os.chdir(os.path.split(os.path.realpath(__file__))[0])

# 优先从环境变量读取结果目录（Rust 端传入），fallback 到脚本旁（开发模式兼容）
_result_dir = os.environ.get("SKYCALIB_RESULT_DIR")
if _result_dir:
    CALIBRAT_RESULT_PATH = _result_dir.rstrip("/") + "/"
else:
    CALIBRAT_RESULT_PATH = os.path.abspath(os.path.dirname(os.getcwd())) + "/CalibratResult/"
SLAM_YAML_TRANSFORM_TOOL_PATH = os.path.abspath(os.path.dirname(os.getcwd())) + "/tools/transform_result_to_slam/"
RETURN_STATUS_ERROR = "status:error"

def getDeviceId():
    cpu_id = os.popen("adb shell cat /sys/devices/soc0/serial_number").readlines()
    device_id=cpu_id[0]
    return (device_id.split()[0])

def isDataSetInSdcard():
    read_android_version = os.popen("adb shell getprop ro.build.version.release").readlines()
    android_version = read_android_version[0]
    if android_version.split()[0] != "12":
        print(str("device system version is: android14 or higher"))
        return True   #android 14 or other
    else:
        print(str("device system version is: android12"))
        return False    #android 12

def adbPullData(device_id_in):
    ADB_PULL_CMD = " "
    sataSetInSdcard = isDataSetInSdcard()
    if sataSetInSdcard:
        ADB_PULL_CMD = "adb pull /sdcard/qvrdataset/ " + CALIBRAT_RESULT_PATH + device_id_in
    else:
        ADB_PULL_CMD = "adb pull /data/local/tmp/qvrdataset/ " + CALIBRAT_RESULT_PATH + device_id_in
    print(ADB_PULL_CMD)
    os.system(ADB_PULL_CMD)

def getTheDeviceDataPath():
    print(str("等待设备插入..."))
    os.system("adb wait-for-device")
    device_id = getDeviceId()
    if os.path.exists(CALIBRAT_RESULT_PATH + device_id):
        shutil.rmtree(CALIBRAT_RESULT_PATH + device_id)
    os.makedirs(CALIBRAT_RESULT_PATH + device_id)
    adbPullData(device_id)

    if not os.path.exists(CALIBRAT_RESULT_PATH + device_id + "/qvrdataset"):
        print(str("QVR数据集不存在！"))
        sys.exit(RETURN_STATUS_ERROR + " + QVR数据集不存在")

    files_dir = os.listdir(CALIBRAT_RESULT_PATH + device_id + "/qvrdataset")
    if not files_dir:
        print(str("QVR数据集不存在！"))
        sys.exit(RETURN_STATUS_ERROR + " + 图片数据量不足")

    log_files = [file for file in files_dir if file.endswith('.log')]
    slam_dataset_path = CALIBRAT_RESULT_PATH + device_id + "/qvrdataset/" + log_files[0]
    print(slam_dataset_path)
    return slam_dataset_path


have_rgb = False
Camera_directory_num = 0

if len(sys.argv) == 3:
    have_rgb = sys.argv[1] == "1"
else:
    print(str("参数传入错误"))
    sys.exit(RETURN_STATUS_ERROR + " + 参数传入错误")

SLAM_DATASET_PATH = getTheDeviceDataPath()
CAM_IMU_ACCE_FLIE = SLAM_DATASET_PATH + "/Sensors/accelerometer_0.xml"
CAM_IMU_GYRO_FLIE = SLAM_DATASET_PATH + "/Sensors/gyroscope_0.xml"
TRACKING_CAM_PATH = SLAM_DATASET_PATH + "/Camera8"
CTRL_TRACKING_CAM_PATH = SLAM_DATASET_PATH + "/Camera9"
RGB_CAM1_PATH = SLAM_DATASET_PATH + "/Camera4"
RGB_CAM3_PATH = SLAM_DATASET_PATH + "/Camera5"

if not os.path.exists(CAM_IMU_ACCE_FLIE):
    print(str("IMU_ACCEL 数据不存在！"))
    sys.exit(RETURN_STATUS_ERROR + " + IMU ACCEL数据不存在")

if not os.path.exists(CAM_IMU_GYRO_FLIE):
    print(str("IMU_GYRO 数据不存在！"))
    sys.exit(RETURN_STATUS_ERROR + " + IMU GYRO数据不存在")

for f_name in os.listdir(SLAM_DATASET_PATH):
    if fnmatch.fnmatch(f_name, 'Camera*'):
        camera_data_path = SLAM_DATASET_PATH + '/' + f_name
        camera_data_files = os.listdir(camera_data_path)
        camera_data_num = len(camera_data_files)
        if(camera_data_num < 200):
            print(str("摄像头图片数据数量不够！"))
            sys.exit(RETURN_STATUS_ERROR + " + 图片数据量不足，请在半成品工位复测")
        Camera_directory_num = Camera_directory_num + 1

if have_rgb:
    if Camera_directory_num < 4:
        print(str("数据集中Camera文件夹数量不匹配！"))
        sys.exit(RETURN_STATUS_ERROR + " + Camera*文件夹数量不匹配")

#if os.path.exists(TRACKING_CAM_PATH) and os.path.exists(CTRL_TRACKING_CAM_PATH):
#    #检测文件夹中是否存在数据
#    tracking_files = os.listdir(TRACKING_CAM_PATH)
#    ctrl_tracking_files = os.listdir(CTRL_TRACKING_CAM_PATH)
#    tracking_num = len(tracking_files)
#    ctrl_tracking_num = len(ctrl_tracking_files)
#    if tracking_num < 100 or ctrl_tracking_num < 100:
#        print(str("6dof摄像头数据数量不够！"))
#        sys.exit(RETURN_STATUS_ERROR)
#else:
#    print(str("6dof摄像头数据文件夹不存在！"))
#    sys.exit(RETURN_STATUS_ERROR)

#if have_rgb:
#    if os.path.exists(RGB_CAM1_PATH) and os.path.exists(RGB_CAM3_PATH):
#        rgb_cam1_files = os.listdir(RGB_CAM1_PATH)
#        rgb_cam3_files = os.listdir(RGB_CAM3_PATH)
#        rgb_cam1_num = len(rgb_cam1_files)
#        rgb_cam3_num = len(rgb_cam3_files)
#        if rgb_cam1_num < 100 or rgb_cam3_num < 100:
#            print(str("RGB摄像头数据数量不够！"))
#            sys.exit(RETURN_STATUS_ERROR)
#    else:
#        print(str("RGB摄像头数据文件夹不存在！"))
#        sys.exit(RETURN_STATUS_ERROR)

RETURN_STATUS_OK = "status:ok,path:" + SLAM_DATASET_PATH

sys.exit(RETURN_STATUS_OK)
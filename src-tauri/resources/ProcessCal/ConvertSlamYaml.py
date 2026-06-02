#!/usr/bin/python
# -*- coding: utf-8 -*-
# python 3.x

import time
import os
import sys
import zipfile

os.chdir(os.path.split(os.path.realpath(__file__))[0])
SLAM_YAML_TRANSFORM_TOOL_PATH = os.path.abspath(os.path.dirname(os.getcwd())) + "/tools/transform_result_to_slam/"
SLAM_YAML_VERIFY_TOOL_PATH = os.path.abspath(os.path.dirname(os.getcwd())) + "/tools/"

RETURN_STATUS_OK = "status:ok"
RETURN_STATUS_ERROR = "status:error"
 
def make_zip(source_dir, output_filename):
    zipf = zipfile.ZipFile(output_filename, 'w')
    pre_len = len(os.path.dirname(source_dir))
    for parent, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            pathfile = os.path.join(parent, filename)
            arcname = pathfile[pre_len:].strip(os.path.sep)
            zipf.write(pathfile, arcname)
    zipf.close()

def copyLogs(logs_file_dir):
    SRC_FILE = logs_file_dir + "/Calib.log"
    DEST_FILE = logs_file_dir + "/calibDetails"

    if os.path.exists(SRC_FILE) and os.path.exists(DEST_FILE):
        COPY_CMD = "cp " + SRC_FILE+ " " + DEST_FILE
        print(COPY_CMD)
        os.system(COPY_CMD)

if __name__ == '__main__':

    slam_dataset_path = "init_patch"
    if len(sys.argv) ==2:
        slam_dataset_path = sys.argv[1]
    else:
        print(str("参数传入错误"))
        sys.exit(RETURN_STATUS_ERROR + " + 参数传入错误")

    # slam_dataset_path = r"/home/ethan/dataset/268867553/invision_slamdataset/dump"
    qvr_calib_file_dir = os.path.dirname(slam_dataset_path)
    
    calib_details_dir = qvr_calib_file_dir + "/calibDetails"
    device_calibration_file1 = qvr_calib_file_dir + "/calibDetails/device_calibration.xml"
    device_calibration_file2 = qvr_calib_file_dir + "/device_calibration.xml"

    if os.path.exists(calib_details_dir) and os.path.exists(device_calibration_file1) and os.path.exists(device_calibration_file2):
         copyLogs(qvr_calib_file_dir)
         make_zip(calib_details_dir, qvr_calib_file_dir + "/calibDetails.zip")
    else:
        print(str("标定文件未生成！"))
        exit(RETURN_STATUS_ERROR + " + 标定文件未生成")

    exit(RETURN_STATUS_OK)

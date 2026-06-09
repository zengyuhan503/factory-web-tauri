"""
/******************************************************************************
* Copyright (c) 2017 Qualcomm Technologies, Inc.
* All Rights Reserved
* Confidential and Proprietary - Qualcomm Technologies, Inc.
******************************************************************************/
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import subprocess
import shutil
import tempfile
import xml.etree.ElementTree as Et
from datetime import datetime

from adb import (adb_directory_exists, adb_root_remount, adb_get_serial,
                 adb_push, adb_pull, adb_non_empty_file)
from captureData import capture_data, find_xml_tag, find_calib_xml_root
from utils import Timer

RETURN_STATUS_OK = "status:ok"
RETURN_STATUS_ERROR = "status:error"

def ensure_executable(app_path):
    """确保可执行文件有执行权限；如系统目录无写权限无法 chmod，则复制到临时目录。"""
    if not os.path.exists(app_path):
        return app_path
    if os.access(app_path, os.X_OK):
        return app_path
    # 无执行权限，复制到临时目录后赋予权限
    tmp_dir = tempfile.mkdtemp(prefix="skyworthxr-calib-")
    tmp_path = os.path.join(tmp_dir, os.path.basename(app_path))
    shutil.copy2(app_path, tmp_path)
    os.chmod(tmp_path, 0o755)
    print('已将标定工具复制到临时目录: %s' % tmp_path)
    return tmp_path

def is_device_attached():
    adb_get_serial()


def get_qvr_root(roots=(
        '/etc/qvr', '/persist/qvr', '/vendor/etc/qvr', '/system/etc/qvr')):
    for root in roots:
        if adb_directory_exists(root):
            return root
    print('No qvrservice config directory found on device after checking',
          roots)
    exit(RETURN_STATUS_ERROR)


def update_calib_config(soc_serial, calib_config, local_calib_config, global_csv_dir,
                        calib_details_dir, validate_robot_arm_trajectory, exclude_id):
    xml_tree = Et.parse(calib_config)
    calib = find_calib_xml_root(xml_tree)
    calib_save = find_xml_tag(calib, 'Save')
    if not exclude_id:
        calib_save.set('deviceId', soc_serial)
    calib_save.set('debugSaveDir', os.path.realpath(calib_details_dir))
    if global_csv_dir:
        calib_save.set('calibrationCSVDir', os.path.realpath(global_csv_dir))
    else:
        if calib_save.get('calibrationCSVDir') is None:
            calib_save.set('calibrationCSVDir',
                           os.path.realpath(calib_details_dir))
    if not validate_robot_arm_trajectory:
        calib_validation = find_xml_tag(calib, 'Validation')
        calib_validation.set('validateRobotArmTrajectory', 'false')
    xml_tree.write(local_calib_config)


def run_calib(soc_serial, calib_dir, global_csv_dir, calib_app, calib_config,
              target_config, capture_dir, validate_robot_arm_trajectory, exclude_id):
    local_calib_config = os.path.join(calib_dir, 'Calib-config.xml')
    calib_details_dir = os.path.join(calib_dir, 'calibDetails')
    update_calib_config(soc_serial, calib_config, local_calib_config, global_csv_dir,
                        calib_details_dir, validate_robot_arm_trajectory, exclude_id)

    print('Running Calib')
    calib_app = ensure_executable(calib_app)
    command = [os.path.realpath(calib_app), '--calib_config',
               os.path.realpath(local_calib_config), '--calib_dataset',
               os.path.realpath(capture_dir)]
    if target_config is not None:
        local_target_config = os.path.join(calib_dir, 'Target-config.xml')
        shutil.copy(target_config, local_target_config)
        command += ['--target_config', os.path.realpath(local_target_config)]
    with open(os.path.join(calib_dir, 'Calib.log'), 'w') as logFile:
        result = subprocess.Popen(command, stdout=logFile,
                                  stderr=subprocess.STDOUT, cwd=calib_dir)
        result.wait()

    if result.returncode:
        print('Calibration failed')
        failure_log_string = " "
        failure_log = os.path.join(calib_details_dir, 'failureReport.log')

        if os.path.exists(failure_log):
            with open(failure_log, 'r') as f:
                failure_log_string = str(f.read())
                print(failure_log_string)

        if "baseline outside allowed range" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 摄像头Baseline超过范围")
        elif "Insufficient coverage" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 摄像头存在遮挡")
        elif "Failed to process dataset" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 数据集错误, 需要重新采集数据")
        elif "targets detected in camera rgb-left is too low" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 6号摄像头(rgb-left)图片不清晰或者无图像")
        elif "targets detected in camera rgb-right is too low" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 5号摄像头(rgb-right)图片不清晰或者无图像")
        elif "targets detected in camera trackingA is too low" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 4号摄像头(trackingA)图片不清晰或者无图像")
        elif "targets detected in camera trackingB is too low" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 3号摄像头(trackingB)图片不清晰或者无图像")
        elif "targets detected in camera ctrl-trackingA is too low" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 2号摄像头(ctrl-trackingA)图片不清晰或者无图像")
        elif "targets detected in camera ctrl-trackingB is too low" in failure_log_string :
            exit(RETURN_STATUS_ERROR + " + 1号摄像头(ctrl-trackingB)图片不清晰或者无图像")
        else:
            exit(RETURN_STATUS_ERROR + " + 未知错误，请检查数据集中图片")
    else:
        print('Calibration successful')
        calib_files = find_calib_files(calib_dir)
        comment = os.getenv('CalibrationComment')
        if comment:
            for calibFile in calib_files:
                with open(os.path.join(calib_dir, calibFile), 'a') as f:
                    f.write('<!-- %s -->\n' % comment)


def backup_old_calib(calib_dir, qvr_root):
    old_calib = '%s/%s' % (qvr_root, 'device_calibration.xml')
    if adb_non_empty_file(old_calib):
        backup_dir = os.path.join(calib_dir, 'backups',
                                  datetime.now().strftime('%Y-%m-%d-%H_%M_%S'))
        print('Backup previous calibration to', backup_dir)
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        pull_output = adb_pull(old_calib, backup_dir)
        print(pull_output.decode().splitlines()[-1])


def find_calib_files(calib_dir):
    return list(filter(
        lambda f: f.endswith('xml') and not f.startswith(('Calib', 'Target')),
        os.listdir(calib_dir)))


def push_new_calib(calib_dir, qvr_root):
    calib_files = find_calib_files(calib_dir)
    print('Pushing %s to %s' % (' '.join(calib_files), qvr_root))
    calib_files_full = ' '.join(
        map(lambda f: os.path.join(calib_dir, f), calib_files))
    push_output = adb_push(calib_files_full, qvr_root)
    print(push_output.decode().splitlines()[-1])


if __name__ == '__main__':
    total_timer = Timer()
    main_parser = argparse.ArgumentParser(
        description='Run calibration automation')
    main_parser.add_argument('-a', '--calibApp', type=str, required=True,
                             help='Path to Calib app')
    main_parser.add_argument('-c', '--calibConfig', type=str,
                             help='Calib configuration file', required=True)
    main_parser.add_argument('-g', '--globalCSVDir', type=str,
                             help='(Optional) Set global location for '
                                  'appending calibration CSV summaries, '
                                  'defaults to using configured value or if '
                                  'unconfigured saving in '
                                  'device calibDetails folder')
    main_parser.add_argument('-r', '--robotController', type=str,
                             help='Path to Robot controller app, '
                                  'or set to "MANUAL" or "MANUAL-HANDHELD" '
                                  'for manual calibration flow with a hand '
                                  'held device, or set to MANUAL-ROBOT for '
                                  'manual mode with the device on a robot arm',
                             required=True)
    main_parser.add_argument('-s', '--robotStart', type=str,
                             help='[Optional] Arg/File to Robot controller to '
                                  'go to "start" position')
    main_parser.add_argument('-m', '--robotMotion', type=str,
                             help='Arg/File to Robot controller to '
                                  'execute calibration motion')
    main_parser.add_argument('-f', '--robotFinish', type=str,
                             help='[Optional] Arg/File to Robot controller to '
                                  'go to "finish" position')
    main_parser.add_argument('-d', '--duration', type=int, default=60,
                             help='Duration of capture in seconds '
                                  '(default: 60) (must be longer than '
                                  'robot calibration motion)')
    main_parser.add_argument('-x', '--excludeID', type=int, choices=[0, 1],
                             default=0,
                             help='Exclude device ID from calibration file, '
                                  'controls whether config file is portable')
    main_parser.add_argument('-t', '--targetConfig', type=str,
                             help='Target board configuration file, '
                                  '[Optional] if not provided, '
                                  'target config is read from calib config')
    main_parser.add_argument('-p', '--captureRoot', type=str,
                             help='Location to save data on device. Ensure '
                                  'there is enough space. [Optional] if not '
                                  'provided, set based on device and config')

    args = main_parser.parse_args()
    testargs = [args.calibApp, args.calibConfig]
    if args.robotController.startswith('MANUAL'):
        print('Manual calibration motion ' + args.robotController)
        validateRobotArmTrajectory = args.robotController == 'MANUAL-ROBOT'
    else:
        validateRobotArmTrajectory = True
        if args.robotMotion is None:
            print('Robot motion not specified, aborting...')
            exit(RETURN_STATUS_ERROR)
        testargs.append(args.robotController)
    for arg in filter(lambda f: not os.path.exists(f), testargs):
        print('Argument %s does not exist, aborting...' % arg)
        exit(RETURN_STATUS_ERROR)

    is_device_attached()
    adb_root_remount()
    qvrRoot = get_qvr_root()
    print('Found qvrservice config directory at:', qvrRoot)

    capture_timer = Timer()
    SOC_serial, captureDir = capture_data(args.robotController,
                                          args.robotStart, args.robotMotion,
                                          args.robotFinish, args.calibConfig,
                                          dev_capture_root=args.captureRoot,
                                          duration=args.duration)
    calibDir = os.path.dirname(captureDir)
    capture_timer.report_elapsed('Total capture time')

    calib_timer = Timer()

    excludeID = bool(args.excludeID)
    run_calib(SOC_serial, calibDir, args.globalCSVDir, args.calibApp, args.calibConfig,
              args.targetConfig, captureDir, validateRobotArmTrajectory, excludeID)

    calib_timer.report_elapsed('Total calib time')

    backup_old_calib(calibDir, qvrRoot)

    push_new_calib(calibDir, qvrRoot)

    total_timer.report_elapsed('Total time taken')

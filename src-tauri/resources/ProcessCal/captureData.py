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

import os
import re
import shutil
import subprocess
import sys
import time
from xml.etree import ElementTree as Et

from adb import (adb_shell, adb_pull, adb_shell_process, adb_non_empty_file,
                 adb_get_datalogger_version, adb_file_cat)

from utils import CaptureCommand, LoggerVersion, Timer


def get_device_id(dev_capture_dir):
    id_file = '%s/*.log/ID.txt' % dev_capture_dir
    if adb_non_empty_file(id_file):
        serial_num = adb_file_cat(id_file)
        print('Serial from ID.txt:', serial_num)
    else:
        print('ID.txt not found')
        serial_num = adb_file_cat('/sys/devices/soc0/serial_number')
        print('SOC Serial Number:', serial_num)

    return serial_num


def find_xml_tag(base_element, element_tag):
    """
    Search within base_element for XML element with tag element_tag
    if not found, create it
    """
    element = base_element.find(element_tag)
    if element is None:
        element = Et.SubElement(base_element, element_tag)
    return element


def parse_metainfo(metainfo, sequence, camera_dir):
    with open(metainfo, 'r') as saveoutput:
        metainfo_string = saveoutput.read()
        match = re.search(r'<CameraInfo.*</CameraInfo>', metainfo_string,
                          re.DOTALL)
        if match:
            cam_info = Et.fromstring(match.group(0))
            sequence.insert(0, cam_info)
        frameset = Et.SubElement(sequence, 'Frameset')
        frameline_matches = re.search(r'<Frame .*/>', metainfo_string,
                                      re.DOTALL).group(0)
        frame_count = 0
        if frameline_matches:
            for frame_line in frameline_matches.splitlines():
                frame_xml = Et.fromstring(frame_line)
                filenamematch = frame_xml.attrib['filename']
                filesizematch = frame_xml.attrib['nBytes']
                file_size_match = int(filesizematch.strip())
                if os.path.exists(os.path.join(camera_dir, filenamematch)):
                    file_size = os.path.getsize(os.path.join(camera_dir, filenamematch))
                    if file_size > file_size_match:
                        frameset.append(frame_xml)
                        frame_count += 1
                    else:
                        print(str("发现不完整图片，丢弃："), os.path.join(camera_dir, filenamematch))
            print(frame_count)
        return frame_count


def generate_meta_info(camera_dir):
    meta_info = os.path.join(camera_dir, 'MetaInfo.xml')
    print(meta_info)
    sequence = Et.Element('Sequence')
    if os.path.exists(meta_info):
        frames_count = parse_metainfo(meta_info, sequence, camera_dir)
        shutil.move(meta_info, meta_info + '.orig')
        Et.SubElement(sequence, 'CaptureInfo',
                      attrib={'stereo': 'false',
                              'interleaved': 'true',
                              'numberOfFrames': str(frames_count)})
        Et.ElementTree(sequence).write(meta_info, encoding='utf-8',
                                       xml_declaration=True)
    else:
        raise SystemError('MetaInfo.xml not found!')


def move_robot(controller, motion):
    if controller.startswith('MANUAL'):
        print('Begin calibration motion')
        if os.getenv('TEAMCITY_VERSION'):
            time.sleep(30)
        else:
            prompt = 'Press "Enter" key twice when ' \
                     'calibration motion is complete'
            if sys.version_info.major < 3:
                raw_input(prompt)
            else:
                input(prompt)
    else:
        #subprocess.call([controller, motion], stdout=subprocess.PIPE)
        os.system("python3 " + controller + " " + motion )

def pull_capture_data(dev_capture_dir, host_capture_dir, manual_frame_removal):
    if os.path.exists(host_capture_dir):
        print('Clearing existing capture log at:', host_capture_dir)
        shutil.rmtree(host_capture_dir)
    os.makedirs(host_capture_dir)
    output = adb_shell('ls --color=never -d %s/*.log' % dev_capture_dir)
    sensor_logs = output.decode().splitlines()[0]
    output = adb_shell('ls --color=never -d %s/Camera*' % sensor_logs)
    camera_folders = output.decode().splitlines()
    if manual_frame_removal:
        for cameraFolder in camera_folders:
            # delete every other image frame (2,4,6...), simulating 15fps
            adb_shell(r"rm -rf $(ls %s/*pgm|sed -n 'n;p')" % cameraFolder)
    # Copy the whole capture folder over, instead of sensors and camera only
    pull_output = adb_pull('%s/.' % sensor_logs, host_capture_dir)
    print(pull_output.decode().splitlines()[-1])


def get_num_frames(camera_dir):
    with open(os.devnull, 'w') as devnull:
        output = adb_shell('ls --color=never %s/*.pgm|wc -l' %
                           camera_dir, stderr=devnull)
        frames = output.decode().splitlines()
        num_frames = int(frames[0]) if len(frames) else 0
        print('# of Frames:', num_frames)
    return num_frames


def check_camera_folders(dev_capture_dir):
    camera_folders = []
    for i in range(20):
        try:
            output = adb_shell('ls --color=never -d '
                               '%s/*log/Camera*' % dev_capture_dir).decode()
            if "No such file or directory" in output:
                raise Exception('Capture directory does not exist')
            camera_folders.append(output.splitlines()[0])
        except:
            print('Waiting for camera folders in seconds', i)
            time.sleep(1)
            continue
        break
    return exit(1) if not camera_folders else camera_folders


def find_calib_xml_root(xml, calib_roots=('XRCalib', 'VIOCalib')):
    for calib_root in calib_roots:
        calib = xml.find(calib_root)
        if calib is not None:
            return calib


def get_camera_config_info(calib_config,
                           defaults=dict(capture_fps='15', res='quarter')):
    xml_tree = Et.parse(calib_config)
    calib = find_calib_xml_root(xml_tree)
    calib_cameras = find_xml_tag(calib, 'Cameras')
    camera_configs = dict()
    for camera in calib_cameras.findall('Camera'):
        camera_name = camera.get('name')
        if camera_name is None:
            print("Error: each <Camera> tag must include a name attribute")
            exit(1)
        if 'ctrl-trackingA' in camera_name:
            camera_name = 'ctrl-tracking'
        elif 'ctrl-trackingB' in camera_name:
            continue
        elif 'trackingA' in camera_name:
            camera_name = 'tracking'
        elif 'trackingB' in camera_name:
            continue
        elif 'trackingC' in camera_name:
            continue
        elif 'trackingD' in camera_name:
            continue
        camera_config = dict()
        for key in defaults.keys():
            camera_config[key] = camera.get(key, default=defaults[key])
        camera_configs[camera_name] = camera_config
    return camera_configs


def generate_command(capture_app, dev_capture_root, duration,
                     calib_config, capture_rate=30, manual_frame_removal=True):
    version_number = LoggerVersion(*adb_get_datalogger_version())
    print('Datalogger version:', version_number)
    camera_params = get_camera_config_info(calib_config)
    cmd = CaptureCommand(capture_app, dev_capture_root, duration)
    # Logic:
    # Version >=1.11 tracking and rgb names and res/fps params supported
    # Version 1.5-1.8 only rgb cameras names are supported
    # version <1.5 no rgb names supported
    if version_number >= LoggerVersion(1, 20):
        manual_frame_removal = False
        for name in camera_params:
            cmd.add_params(cmd.make_options(camera_params, name))
            if 'tracking' in name:
                capture_rate = int(camera_params[name]['capture_fps'])
            elif 'rgb' in name:
                cmd.set_dev_capture_root('/data')
            if camera_params[name]['res'] == 'full':
                print('It will take longer than usual for completing '
                      'the calibration because of full resolution!')
                cmd.set_dev_capture_root('/data')
    elif version_number >= LoggerVersion(1, 5):
        for name in camera_params:
            if 'tracking' in name:
                continue
            if 'rgb' in name:
                print('It will take longer than usual for completing the '
                      'calibration because of full resolution and high FPS')
                cmd.set_dev_capture_root('/data')
            cmd.add_params(name)
    elif 'rgb' in ' '.join(camera_params.keys()):
        raise SystemError('RGB cameras found in calib config file with '
                          'incompatible datalogger version ')
    capture_command, dev_capture_dir = cmd.create_command()
    print('Datalogger command:', capture_command)
    return capture_command, manual_frame_removal, capture_rate, dev_capture_dir


def capture_data(controller, robot_start, robot_motion, robot_finish,
                 calib_config, dev_capture_root=None, duration=60,
                 pre_stationary_frames=5, post_stationary_frames=20,
                 capture_timeout=60, capture_app='qvrdatalogger'):
    if robot_start:
        move_robot(controller, robot_start)

    pre_motion_timer = Timer()
    capture_command, manual_remove_frames, capture_rate, dev_capture_dir = \
        generate_command(capture_app, dev_capture_root, duration, calib_config)

    capture_proc = adb_shell_process(capture_command)
    camera_folders = check_camera_folders(dev_capture_dir)
    for cameraFolder in camera_folders:
        while get_num_frames(cameraFolder) < pre_stationary_frames:
            if pre_motion_timer.seconds_elapsed() > capture_timeout:
                print('Capture tool failed to start, aborting...')
                exit(1)
    pre_motion_timer.report_elapsed('Pre-motion stationary delay')

    motion_timer = Timer()
    move_robot(controller, robot_motion)
    motion_timer.report_elapsed('Calibration motion duration')

    post_motion_timer = Timer()
    for cameraFolder in camera_folders:
        stop_frame = min(get_num_frames(cameraFolder) + post_stationary_frames,
                         (duration - 1) * capture_rate)
        while get_num_frames(cameraFolder) < stop_frame:
            if post_motion_timer.seconds_elapsed() > capture_timeout:
                print('Capture tool failed to finish, aborting...')
                exit(1)

    kill_timer = Timer()
    adb_shell('pkill %s' % capture_app)
    capture_proc.communicate()
    kill_timer.report_elapsed('Time taken for graceful exit')
    post_motion_timer.report_elapsed('Post-motion stationary delay')

    device_id = get_device_id(dev_capture_dir)
    if os.getenv('TEAMCITY_VERSION'):
        host_calib_dir = 'Calibration'
    else:
        host_calib_dir = os.path.join('Calibration', device_id)
    host_capture_dir = os.path.join(host_calib_dir, 'sensorLogs')

    pull_timer = Timer()
    pull_capture_data(dev_capture_dir, host_capture_dir, manual_remove_frames)
    pull_timer.report_elapsed('Pull data')

    camera_folders = os.listdir(host_capture_dir)
    for cameraFolder in camera_folders:
        if 'Camera' in cameraFolder:
            prep_data_timer = Timer()
            generate_meta_info(os.path.join(host_capture_dir, cameraFolder))
            prep_data_timer.report_elapsed('Prep data')

    if robot_finish:
        move_robot(controller, robot_finish)

    return device_id, host_capture_dir

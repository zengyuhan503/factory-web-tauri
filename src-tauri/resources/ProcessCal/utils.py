"""
/******************************************************************************
* Copyright (c) 2017 Qualcomm Technologies, Inc.
* All Rights Reserved
* Confidential and Proprietary - Qualcomm Technologies, Inc.
******************************************************************************/
"""
from datetime import datetime

from adb import adb_shell, adb_shell_process, adb_directory_exists


def find_capture_root(roots=('/storage', '/tmp')):
    for root in roots:
        if adb_directory_exists(root):
            return root
    raise Exception('could not choose/find capture root on device, '
                    'please use --captureRoot script arg')


class CaptureCommand:
    def __init__(self, capture_app, dev_capture_root, duration):
        self.capture_app = capture_app
        self.duration = duration
        self.dev_capture_root = dev_capture_root
        self.params = ''

    def set_dev_capture_root(self, dev_capture_root):
        if self.dev_capture_root is None:
            self.dev_capture_root = dev_capture_root

    def create_command(self):
        dev_capture_dir = self.get_dev_capture_dir()
        capture_command = '%s -j -t 6 -o %s -d %d' % (
            self.get_capture_app_path(), dev_capture_dir, self.duration)
        capture_command += self.params
        return capture_command, dev_capture_dir

    @staticmethod
    def make_options(params, name):
        options = name
        for i, key in enumerate(params[name].keys()):
            sep = ',' if i else ':'
            options += '%s%s=%s' % (sep, key, params[name][key])
        return options

    def add_params(self, param):
        self.params += ' -n %s' % param

    def get_dev_capture_dir(self):
        if self.dev_capture_root is None:
            self.dev_capture_root = find_capture_root()
        # clean up prior captures on device
        adb_shell('rm -rf %s/calibration.??????' % self.dev_capture_root)

        # prepare tmpdir on device for new capture
        output = adb_shell(
            'mktemp -d -p %s calibration.XXXXXX' % self.dev_capture_root)
        dev_capture_dir = output.decode().splitlines()[0]
        print('logging to tempdir:', dev_capture_dir)
        return dev_capture_dir

    def get_capture_app_path(self):
        which_capture_app = adb_shell_process('which %s' % self.capture_app)
        return which_capture_app.stdout.read().decode().splitlines()[0]


class LoggerVersion:
    def __init__(self, major, minor):
        self.major = major
        self.minor = minor

    def __ge__(self, other):
        if self.major >= other.major and self.minor >= other.minor:
            return True
        return False

    def __str__(self):
        return '%d.%d' % (self.major, self.minor)


class Timer:
    def __init__(self):
        self.start = datetime.now()

    def seconds_elapsed(self):
        return (datetime.now()-self.start).total_seconds()

    def report_elapsed(self, event_label):
        print('%s:' % event_label, datetime.now() - self.start)

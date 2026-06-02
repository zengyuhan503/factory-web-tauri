"""
/******************************************************************************
* Copyright (c) 2017 Qualcomm Technologies, Inc.
* All Rights Reserved
* Confidential and Proprietary - Qualcomm Technologies, Inc.
******************************************************************************/
"""
import re
import subprocess
import time

ADB_WAIT_CMDS = ('shell', 'push', 'pull', 'root', 'remount', 'reboot')
ADB_NONWAIT_CMDS = ('get-serialno', 'kill-server', 'start-server', 'version')
ADB_CMDS = {cmd: 'adb wait-for-device %s' % cmd for cmd in ADB_WAIT_CMDS}
ADB_CMDS.update({cmd: 'adb %s' % cmd for cmd in ADB_NONWAIT_CMDS})


def adb_shell_process(cmd, stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT):
    return subprocess.Popen('%s %s' % (ADB_CMDS['shell'], cmd),
                            stdout=stdout,
                            stderr=stderr)


def adb_shell(cmd, stderr=None):
    output = subprocess.check_output('%s %s' % (ADB_CMDS['shell'], cmd),
                                     stderr=stderr)
    return output


def adb_keyevent(keycode):
    keyevent = 'input keyevent %s' % keycode
    adb_shell(keyevent)


def adb_root_remount(post_root_sleep=1):
    subprocess.check_call(ADB_CMDS['root'])
    time.sleep(post_root_sleep)
    subprocess.check_call(ADB_CMDS['remount'])
    subprocess.call('%s %s' % (ADB_CMDS['shell'], 'mount -o remount, rw /'))
    subprocess.call('%s %s' % (ADB_CMDS['shell'], 'setenforce 0'))
    subprocess.call('%s %s' % (ADB_CMDS['shell'], "for POLICY in /sys/devices/system/cpu/cpufreq/policy*; do echo pinning clocks high in $POLICY; cat $POLICY/scaling_max_freq > $POLICY/scaling_min_freq; done"))


def adb_push(source, target):
    adb_cmd = '%s %s %s' % (ADB_CMDS['push'], source, target)
    output = subprocess.check_output(adb_cmd)
    adb_shell('sync')
    return output


def adb_pull(source, target):
    adb_cmd = '%s %s %s' % (ADB_CMDS['pull'], source, target)
    output = subprocess.check_output(adb_cmd)
    return output


def adb_get_serial():
    adbget = subprocess.Popen(ADB_CMDS['get-serialno'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
    if adbget.wait():
        print('\n'.join(adbget.stdout.read().decode().splitlines()))
        exit(1)
    else:
        return adbget.stdout.read().decode().split()[0]


def adb_get_datalogger_version():
    adb_output = adb_shell_process('qvrdatalogger -V', stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
    version_string = adb_output.stdout.read().decode()
    match = re.search(r'qvrdatalogger version: ([0-9]*?).([0-9]*?)-',
                      version_string, re.IGNORECASE)
    if match:
        return int(match.group(1).strip()), int(match.group(2).strip())
    else:
        return 0, 0


def adb_non_empty_file(filename):
    exit_code = f"sh -c '[ -s {filename} ]'; echo $?"
    return not int(adb_shell(exit_code).decode().strip())


def adb_directory_exists(directory):
    exit_code = f"sh -c '[ -d {directory} ]'; echo $?"
    return not int(adb_shell(exit_code).decode().strip())


def adb_file_cat(filename):
    file_cat = ' cat %s' % filename
    adbcat = adb_shell_process(file_cat, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    if adbcat.wait():
        print('\n'.join(adbcat.stdout.read().decode().splitlines()))
        exit(1)
    else:
        return adbcat.stdout.read().decode().split()[0]

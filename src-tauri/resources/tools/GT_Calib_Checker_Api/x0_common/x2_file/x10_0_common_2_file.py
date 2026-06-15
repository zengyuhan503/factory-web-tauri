import os

'''
description: 查找以suffix结尾的子文件夹列表
param {*} dir
param {*} suffix
return {*}
'''
def findSubdirWithSuffix(dir, suffix):

    if(not os.path.exists(dir)):
        return False , []
    
    result = []
    for dir_name in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, dir_name)) and dir_name.endswith(suffix):
            result.append(dir_name)
    return (len(result) > 0), result


'''
description: 查找以suffix结尾的子文件列表
param {*} dir
param {*} suffix
return {*}
'''
def findSubFileWithSuffix(dir, suffix, doSort = True):
    if(not os.path.exists(dir)):
        return False , []
    result = []
    for file_name in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, file_name)) and file_name.endswith(suffix):
            result.append(file_name)
    if(len(result) <= 0):
        return False, []
    return True, sorted(result)
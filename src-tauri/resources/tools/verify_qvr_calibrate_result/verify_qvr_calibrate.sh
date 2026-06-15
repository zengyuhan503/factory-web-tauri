#!/bin/bash

search_keyword() {
    keyword=$1
    file_path="$2/device_calibration.xml"

    result=$(grep "$keyword" "$file_path")
    data=$(echo "$result" | grep -oP "\d+\.\d+" | tr -d '\n')  # remove newlines
    echo "$data"  # return data
}

trackingA_reproject=$(search_keyword "Full-trackingA" $1)
trackingB_reproject=$(search_keyword "Full-trackingB" $1)
ctrl_trackingA_reproject=$(search_keyword "Full-ctrl-trackingA" $1)
ctrl_trackingB_reproject=$(search_keyword "Full-ctrl-trackingB" $1)
rgb_left_reproject=$(search_keyword "Full-rgb-left" $1)
rgb_right_reproject=$(search_keyword "Full-rgb-right" $1)

OK=0
CAMERA0_DETECT_ERROR=$((1 << 1))
CAMERA1_DETECT_ERROR=$((1 << 2))
CAMERA2_DETECT_ERROR=$((1 << 3))
CAMERA3_DETECT_ERROR=$((1 << 4))
CAMERA4_DETECT_ERROR=$((1 << 5))
CAMERA5_DETECT_ERROR=$((1 << 6))
CAMERA0_REPROJECT_ERROR=$((1 << 7))
CAMERA1_REPROJECT_ERROR=$((1 << 8))
CAMERA2_REPROJECT_ERROR=$((1 << 9))
CAMERA3_REPROJECT_ERROR=$((1 << 10))
CAMERA4_REPROJECT_ERROR=$((1 << 11))  # 修正此处的错误
CAMERA5_REPROJECT_ERROR=$((1 << 12))  # 修正此处的错误

check_reproject() {
    keyword=$1
    reproject_value=$2
    if [[ $reproject_value > 1 ]]; then  
        echo "$keyword=$reproject_value > 1 "
        if [[ $keyword == "Full-trackingA" ]]; then
            OK=$((OK | CAMERA0_REPROJECT_ERROR))  # 这里使用 $(( )) 进行整数运算
        elif [[ $keyword == "Full-trackingB" ]]; then
            OK=$((OK | CAMERA1_REPROJECT_ERROR))  
        elif [[ $keyword == "Full-ctrl-trackingA" ]]; then
            OK=$((OK | CAMERA2_REPROJECT_ERROR)) 
        elif [[ $keyword == "Full-ctrl-trackingB" ]]; then
            OK=$((OK | CAMERA3_REPROJECT_ERROR))  
        elif [[ $keyword == "Full-rgb-left" ]]; then
            OK=$((OK | CAMERA4_REPROJECT_ERROR)) 
        elif [[ $keyword == "Full-rgb-right" ]]; then
            OK=$((OK | CAMERA5_REPROJECT_ERROR))  
        fi
    else
        echo "$keyword=$reproject_value <= 1"
    fi
}

check_reproject "Full-trackingA" "$trackingA_reproject"  # 调用函数并传入关键词和对应的值
check_reproject "Full-trackingB" "$trackingB_reproject"  # 调用函数并传入关键词和对应的值
check_reproject "Full-ctrl_trackingA" "$ctrl_trackingA_reproject"  # 调用函数并传入关键词和对应的值
check_reproject "Full-ctrl_trackingB" "$ctrl_trackingB_reproject"  # 调用函数并传入关键词和对应的值
#check_reproject "Full-rgb-left" "$rgb_left_reproject"  # 调用函数并传入关键词和对应的值
#check_reproject "Full-rgb-right" "$rgb_right_reproject"  # 调用函数并传入关键词和对应的值
#echo "return $((CAMERA5_REPROJECT_ERROR | CAMERA4_REPROJECT_ERROR))"
echo "return $OK"
exit $OK




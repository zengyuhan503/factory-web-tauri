#ifndef DETECT_BOARD_H
#define DETECT_BOARD_H
#include <vector>
#include <fstream>
#include <sys/stat.h>
#include <iostream>
#include <memory>
#include <boost/filesystem.hpp>
#include <opencv2/highgui.hpp>
#include "PointCalibrateBoard.h"
class DetectBoard
{
private:
    std::vector<std::shared_ptr<PointCalibrateBoard>> m_global_boards_points;
    void clear_board_points();
public:
    DetectBoard(/* args */);
    ~DetectBoard();
    
int detect_board(cv::Mat src, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_a_points, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_b_points);
private:
std::vector<std::weak_ptr<PointCalibrateBoard>> get_contours(cv::Mat binary_img);


};


#endif
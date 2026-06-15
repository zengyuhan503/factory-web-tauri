#ifndef MODEL_ERROR_H
#define MODEL_ERROR_H
#include "Camera.h"
#include "PointCalibrateBoard.h"
#include "ReadQvrCalResult.h"
#include <map>
#include <fstream>
class ModelError
{
private:
    /* data */
    std::vector<std::shared_ptr<Camera>> mCams;
    std::vector<std::vector<std::vector<std::vector<std::pair<cv::Point2d,  cv::Point2d>>>>> mModelError;
    std::map<int,int> mCamId2Index;
    std::vector<cv::Point2d> mMeanError;
    std::vector<cv::Point2d> mMaxError;
    std::vector<cv::Point2d> mStdError;
    std::vector<size_t> mCount;
    std::ofstream mOutFile;
    
public:
    ModelError(ReadQvrCalResult &device_calibration,std::string mResultFile);
    ~ModelError();
    void ComputeError(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points,
                                    std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points,int cam_id);
    void StatisticError(int cam_id);
    cv::Point2d GetMeanError(int cam_id);
    cv::Point2d GetMaxError(int cam_id);
    cv::Point2d GetStdError(int cam_id);
    size_t GetCount(int cam_id);
};



#endif
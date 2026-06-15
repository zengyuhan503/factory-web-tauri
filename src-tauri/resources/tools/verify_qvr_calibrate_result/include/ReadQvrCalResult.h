#ifndef READ_QVR_CAL_RESULT_H
#define READ_QVR_CAL_RESULT_H
#include <string>
#include <vector>
#include <Eigen/Core>
#include <Eigen/Geometry>
#include "TinyXML2.h"
class TargetConfig
{
public:
    std::string target_type;
    float dot_spacing;
    int dots_x;
    int dots_y;
    int apex_dot_index_x;
    int apex_dot_index_y;

public:
    TargetConfig(/* args */){};
    ~TargetConfig(){};
};


class IMUCalbrateResult

{
public:
    float ombc[3];
    float tbc[3];
    float a_bias[3];
    float w_bias[3];
    float ka[3];
    float kg[3];
    float na[3];
    float ng[3];
    float ombg[3];
    float acc_delta;
    float delta;

    float moving_acc_noise;
    float moving_gyro_noise;
    float stationary_acc_noise;
    float stationary_gyro_noise;

public:
    IMUCalbrateResult(/* args */){};
    ~IMUCalbrateResult(){};
};

class CameraCalibrateResult
{
public:
    std::string cam_name;
    int id;
    int width;
    int height;
    double cx;
    double cy;
    double fx;
    double fy;
    std::string model; // 畸变模型
    std::vector<double> radial_distortion;
    double distortion_limit;
    double undistortion_limit;
    Eigen::Matrix4d rig;
    double delta_time_alignment;

public:
    CameraCalibrateResult(/* args */){};
    ~CameraCalibrateResult(){};
};

class ReadQvrCalResult
{
public:
    std::string deviceUID;
    std::vector<CameraCalibrateResult> cameras;
    IMUCalbrateResult imu;
    std::vector<TargetConfig> targets;

public:
    ReadQvrCalResult(std::string cal_result_file,std::string cal_target_config_file);
    ~ReadQvrCalResult();
private:
   void TraversingCalResult(tinyxml2::XMLNode* node);
   void TraversingTargetConfig(tinyxml2::XMLNode* node);
};
#endif

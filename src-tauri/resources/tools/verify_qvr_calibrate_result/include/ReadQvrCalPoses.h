#ifndef READ_QVR_CAL_POSES_H
#define READ_QVR_CAL_POSES_H
#include <vector>
#include <Eigen/Geometry>
#include <jsoncpp/json/json.h>
class ReadQvrCalPoses
{
public:
    std::vector<std::size_t> m_timestamps;
   
    std::vector<Eigen::Matrix4d> m_poses;
    
public:
    ReadQvrCalPoses(std::string pose_file);
    int GetPose(std::size_t time,Eigen::Matrix4d &pose);
    ~ReadQvrCalPoses();
private:
    int GetNearTimes(std::size_t time_now,std::size_t &time_pre_index,std::size_t &time_next_index);
};



#endif
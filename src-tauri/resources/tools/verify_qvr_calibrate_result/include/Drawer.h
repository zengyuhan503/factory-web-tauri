#ifndef DRAWER_H
#define DRAWER_H
#ifdef SHOW
#include<pangolin/pangolin.h>
#include<pangolin/windowing/window.h>
#include <Eigen/Geometry>
#include <mutex>
class Drawer
{
private:
    /* data */
    double mKeyFrameSize=0.08;
    double mKeyFrameLineWidth=0.05;
    double mViewpointF=500;
    double mViewpointX=0;
    double mViewpointY=0.6;
    double mViewpointZ=3.5;
    pangolin::OpenGlRenderState s_cam;
    pangolin::View d_cam;

    std::vector<Eigen::Matrix4d> poses_qvr;
    std::vector<Eigen::Matrix4d> poses_cal;
    std::mutex mTx;
    bool mbRun=true;

public:
    Drawer(/* args */);
    ~Drawer();
    void Run();
    void Stop(){mbRun=false;}

    void SetQvrPoses(std::vector<Eigen::Matrix4d> poses);
    void SetCalPoses(std::vector<Eigen::Matrix4d> poses);
private:
void GetOpgenglCameraMatrix(Eigen::Matrix4d pose,pangolin::OpenGlMatrix &M, pangolin::OpenGlMatrix &MOw);
void ShowPose(Eigen::Matrix4d Twc,float r,float g,float b);
};

#endif

#endif
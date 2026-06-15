#include "ReprojectionError.h"
#include "KannalaBrandt8.h"
#include "Pinhole.h"
#include <iostream>
#include <opencv2/imgproc.hpp>
#include <opencv2/calib3d.hpp>
#include "Utils.h"
#ifdef SHOW
ReprojectionError::ReprojectionError(ReadQvrCalResult &device_calibration, Drawer *drawer) : m_device_calibration(device_calibration), m_drawer(drawer)
#else
ReprojectionError::ReprojectionError(ReadQvrCalResult &device_calibration) : m_device_calibration(device_calibration)
#endif
{
    auto cameras = m_device_calibration.cameras;
    m_cams.resize(cameras.size());
    for (auto it = cameras.begin(); it != cameras.end(); it++)
    {
        auto cam = (*it);
        if (it->model == std::string("FISHEYE_4_PARAMETERS"))
        {
            std::shared_ptr<KannalaBrandt8> fish_eye_camera = std::make_shared<KannalaBrandt8>(cam.fx, cam.fy, cam.cx, cam.cy, cam.radial_distortion, cam.width, cam.height);
            fish_eye_camera->SetId(cam.id);
            fish_eye_camera->SetPoseToCamera0(cam.rig);
            m_cams[cam.id] = fish_eye_camera;
        }
        if (it->model == std::string("RADIAL_6_PARAMETERS"))
        {
            std::shared_ptr<Pinhole> pinhole_camera = std::make_shared<Pinhole>(cam.fx, cam.fy, cam.cx, cam.cy, cam.radial_distortion, cam.width, cam.height);
            pinhole_camera->SetId(cam.id);
            pinhole_camera->SetPoseToCamera0(cam.rig);
            m_cams[cam.id] = pinhole_camera;
        }
    }
}

ReprojectionError::~ReprojectionError()
{
}
std::vector<std::weak_ptr<PointCalibrateBoard>> ReprojectionError::GetCenterBoardPoint(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_points)
{
    std::vector<std::weak_ptr<PointCalibrateBoard>> ret;
    for (auto it = board_points.begin(); it != board_points.end(); it++)
    {
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            if (p->bCenter)
            {
                ret.push_back(p);
                break;
            }
        }
    }
    return ret;
}

int ReprojectionError::ComputeWorldCoordinatePoints(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points)
{
    static float dot_spacing_a = 0;
    static float dot_spacing_b = 0;
    static int ori_x = 0;
    static int ori_y = 0;
    static int rows = 0;
    static int cols = 0;
    if (dot_spacing_a < 0.00001)
    {
        auto targets = m_device_calibration.targets;
        for (auto it = targets.begin(); it != targets.end(); it++)
        {
            auto target = (*it);
            if (target.target_type == TARGET_A)
            {
                dot_spacing_a = target.dot_spacing;
            }
            else if (target.target_type == TARGET_B)
            {
                dot_spacing_b = target.dot_spacing;
            }
            ori_x = target.apex_dot_index_x;
            ori_y = target.apex_dot_index_y;
            rows = target.dots_x;
            cols = target.dots_y;
        }
    }

    for (auto it = board_points.begin(); it != board_points.end(); it++)
    {
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            //if (p->col > 0 && p->col < 19 && p->row > 5 && p->row < 43)
            {
                if (p->type == TARGET_A)
                {
                    p->center_world_coordinate = cv::Point3d((p->row - ori_x - 1) * dot_spacing_a, (p->col - ori_y) * dot_spacing_a * (-1), 0);
                    p->bWorld = true;
                    
                }
                else if (p->type == TARGET_B)
                {
                    p->center_world_coordinate = cv::Point3d((p->row - ori_x) * dot_spacing_b, (p->col - ori_y) * dot_spacing_b, 0);
                    p->bWorld = true;
                }
            }
        }
    }
    return 0;
}
int ReprojectionError::ComputeCameraCoordinatePoints(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points, Eigen::Matrix4d pose)
{

    for (auto it = board_points.begin(); it != board_points.end(); it++)
    {
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            Eigen::Vector4d pp(p->center_world_coordinate.x, p->center_world_coordinate.y, p->center_world_coordinate.z, 1);

            pp = pose * pp;
            p->center_camera_coordinate = cv::Point3d(pp.x(), pp.y(), pp.z());
        }
    }
    return 0;
}
int ReprojectionError::ComputeImageCoordinatePoints(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points, Eigen::Matrix4d pose, int camera_id)
{
    std::vector<cv::Point3d> world_pts;
    std::vector<cv::Point2d> img_pts;
    std::vector<cv::Point2d> img_pts_reproject;
    int index = 0;
    for (auto it = board_points.begin(); it != board_points.end(); it++)
    {
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            //if (p->col > 0 && p->col < 19 && p->row > 5 && p->row < 43)
            {
                world_pts.push_back(p->center_world_coordinate);
                img_pts.push_back(p->center_image);
            }
        }
    }
    if (world_pts.empty())
    {
        return -1;
    }
    Eigen::Matrix4d pose_camera=m_cams[camera_id]->GetPoseToCamera0()*pose;
    //std::cout<<"pose="<<pose<<std::endl;
   // std::cout<<"m_cams[camera_id]->GetPoseToCamera0()="<<m_cams[camera_id]->GetPoseToCamera0()<<std::endl;
   // std::cout<<"pose_camera="<<pose_camera<<std::endl;
    img_pts_reproject = m_cams[camera_id]->Project(world_pts, pose_camera);

    for (auto it = board_points.begin(); it != board_points.end(); it++)
    {
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            //if (p->col > 0 && p->col < 19 && p->row > 5 && p->row < 43)
            {
                
                
                p->center_image_reproject = img_pts_reproject[index];
                auto d=p->center_image_reproject-p->center_image;
                // std::cout<<",d="<<d << ",center_image_reproject=" << p->center_image_reproject << ",center_image=" << p->center_image << ",center_world_coordinate=" << p->center_world_coordinate<< std::endl;
                //if( std::sqrt(d.x*d.x+d.y*d.y)<20 )
                {
                    p->bReProject=true;
                   

                }
            
                
                 index++;
            }
        }
    }
    return 0;
}
std::vector<std::vector<cv::Point2f>> image_points;
std::vector<std::vector<cv::Point3f>> object_points;
std::vector<cv::Point2f> img_pts_reproject;
void ReprojectionError::Show(cv::Mat show, std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points, std::string name)
{
#ifdef SHOW

    int index = 0;

    for (auto it = board_points.begin(); it != board_points.end(); it++)
    {
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            if (p->bReProject)
            {
                cv::circle(show, p->center_image, 1, cv::Scalar(0, 0, 255), -1);
                cv::circle(show, p->center_image_reproject, 3, cv::Scalar(0, 255, 0), 1);
                // cv::circle(show, img_pts_reproject[index], 5, cv::Scalar(255, 0, 0), 1);
                index++;
            }
        }
    }
    cv::imshow(name, show);
    //cv::waitKey();
#endif
}

std::vector<Eigen::Matrix4d> poses_cal;
std::vector<Eigen::Matrix4d> poses_qvr;
void ReprojectionError::TestPose(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> &board_points, Eigen::Matrix4d &pose_calib, Eigen::Matrix4d pose, int camera_id)
{
    std::vector<cv::Point2f> img_pts;
    std::vector<cv::Point3f> world_pts;

    for (auto it = board_points.begin(); it != board_points.end(); it++)
    {

        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            //if (p->col > 0 && p->col < 19 && p->row > 5 && p->row < 43)
            {
                img_pts.push_back(p->center_image);
                world_pts.push_back(p->center_world_coordinate);
            }
        }
    }
    if (img_pts.size() < 50)
    {
        return;
    }
    image_points.push_back(img_pts);
    object_points.push_back(world_pts);

    if (image_points.size() > 100)
    {
        image_points.erase(image_points.begin());
        object_points.erase(object_points.begin());
    }

    cv::Mat cameraMatrix, distCoeffs;
    std::vector<cv::Mat> rvec, tvec;
    cv::calibrateCamera(object_points, image_points, cv::Size(640, 480), cameraMatrix, distCoeffs, rvec, tvec);
    if (m_cams.size() == 6)
    {
        auto test = std::make_shared<Pinhole>();
        m_cams.push_back(test);

        test->SetK(cameraMatrix);
        test->SetDistCoeff(distCoeffs);
        test->SetType(Camera::CAM_PINHOLE);
        test->SetSize(640, 480);

        //std::cout << "test->SetK=" << test->K() << std::endl;
        //std::cout << "test->distCoeffs=" << toCvMat(test->DistCoeff()) << std::endl;
    }

   // std::cout << "cameraMatrix=" << cameraMatrix << std::endl;
   // std::cout << "distCoeffs=" << distCoeffs << std::endl;
   // std::cout << "rvec=" << rvec[rvec.size() - 1] << std::endl;
   // std::cout << "tvec=" << tvec[rvec.size() - 1] << std::endl;
   // std::cout << "tvec=" << toVector3d(tvec[rvec.size() - 1]) << std::endl;
    poses_cal.clear();

    for (size_t i = 0; i < rvec.size(); i++)
    {
        cv::Mat R;
        cv::Rodrigues(rvec[i], R); // 先把旋转向量rvec通过罗德里格斯公式计算得到旋转矩阵R
        Eigen::Matrix3d rotate = toMatrix3d(R);
        Eigen::Matrix4d pose = Eigen::Matrix4d::Identity();
        Eigen::Vector3d traslation = toVector3d(tvec[i]);
        pose.block(0, 0, 3, 3) = rotate;
        pose.block(0, 3, 3, 1) = traslation;

        Eigen::AngleAxisd rotate_v;
        rotate_v.fromRotationMatrix(rotate);
        if (i == rvec.size() - 1)
        {
            pose_calib = pose;
        }
        poses_cal.push_back(pose);
        // std::cout << "rotation_vector2 " << "angle is: " << rotate_v.angle()
        //                            << " axis is: " << rotate_v.angle()*rotate_v.axis().transpose() << std::endl;
    }
    
    poses_qvr.push_back(pose);

}
int ReprojectionError::ComputeError(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points,
                                    std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points, Eigen::Matrix4d pose, int camera_id,cv::Mat img)
{

    ComputeWorldCoordinatePoints(board_a_points);
    Eigen::Matrix4d pose_callib = Eigen::Matrix4d::Identity();

    //TestPose(board_a_points, pose_callib, pose, camera_id);

   // m_drawer->SetCalPoses(poses_cal);
   // m_drawer->SetQvrPoses(poses_qvr);

    ComputeImageCoordinatePoints(board_a_points, pose, camera_id);
   // std::cout << "ComputeError pose_qvr=" << pose.matrix() << std::endl;
   if(!img.empty())
   {
     Show(img, board_a_points, "Board_A_cam_"+std::to_string(camera_id));
     cv::waitKey(1);
   }
   

    return 0;
}

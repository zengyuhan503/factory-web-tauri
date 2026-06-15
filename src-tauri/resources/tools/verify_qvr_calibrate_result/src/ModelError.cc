#include "ModelError.h"
#include "KannalaBrandt8.h"
#include "Pinhole.h"
#include <iostream>
#include <fstream>
#include <opencv2/imgproc.hpp>
ModelError::ModelError(ReadQvrCalResult &device_calibration, std::string mResultFile)
{
    mOutFile = std::ofstream(mResultFile);

    auto cameras = device_calibration.cameras;
    mCams.resize(cameras.size());
    for (int i = 0; i < cameras.size(); i++)
    {
        auto cam = cameras[i];
        if (cam.model == std::string("FISHEYE_4_PARAMETERS"))
        {
            std::shared_ptr<KannalaBrandt8> fish_eye_camera = std::make_shared<KannalaBrandt8>(cam.fx, cam.fy, cam.cx, cam.cy, cam.radial_distortion, cam.width, cam.height);
            fish_eye_camera->SetId(cam.id);
            mCams[i] = fish_eye_camera;
        }
        if (cam.model == std::string("RADIAL_6_PARAMETERS"))
        {
            std::shared_ptr<Pinhole> pinhole_camera = std::make_shared<Pinhole>(cam.fx, cam.fy, cam.cx, cam.cy, cam.radial_distortion, cam.width, cam.height);
            pinhole_camera->SetId(cam.id);
            mCams[i] = pinhole_camera;
        }
    }

    mModelError.resize(mCams.size());

    for (int k = 0; k < mCams.size(); k++)
    {
        auto cam = mCams[k];
        std::cout << "cam->GetHeight()=" << cam->GetHeight() << ",cam->GetWidth()=" << cam->GetWidth() << std::endl;
        mModelError[k].resize(cam->GetHeight());
        for (int row = 0; row < mModelError[k].size(); row++)
        {
            mModelError[k][row].resize(cam->GetWidth());
        }
        mCamId2Index.insert(std::make_pair(cam->GetId(), k));
    }
    mMeanError.resize(mCams.size());
    mMaxError.resize(mCams.size());
    mStdError.resize(mCams.size());
    mCount.resize(mCams.size());
}

ModelError::~ModelError()
{
}
void ModelError::ComputeError(std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points,
                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points, int cam_id)
{
    int index = mCamId2Index[cam_id];

    for (auto it = board_a_points.begin(); it != board_a_points.end(); it++)
    {
        for (auto itt = (*it).begin(); itt != (*it).end(); itt++)
        {
            auto p = (*itt).lock();
            if (p->bReProject)
            {
                int row = p->center_image.y;
                int col = p->center_image.x;
                auto d = p->center_image_reproject - p->center_image;
                // std::cout << "ComputeError d=" << d << std::endl;
                if (std::sqrt(d.x * d.x + d.y * d.y) < 20)
                {
                    mModelError[index][row][col].push_back(std::make_pair(p->center_image, p->center_image_reproject));
                }
            }
        }
    }
    // ShowError(cam_id);
}
size_t ModelError::GetCount(int cam_id)
{
    if(cam_id>=mCamId2Index.size())
    {
        return 0;
    }
    int camera_index = mCamId2Index[cam_id];
    auto camera = mCams[camera_index];
    return mCount[camera_index];
}

void ModelError::StatisticError(int cam_id)
{
    if(cam_id>=mCamId2Index.size())
    {
        return ;
    }
    int camera_index = mCamId2Index[cam_id];
    auto camera = mCams[camera_index];
    bool bUpdate = false;
#ifdef SHOW

    int scale = 10;

    cv::Mat Error = cv::Mat::zeros(camera->GetHeight() * scale, camera->GetWidth() * scale, CV_8UC3);

    for (int row = 16; row < camera->GetHeight() - 16; row += 16)
    {
        for (int col = 16; col < camera->GetWidth() - 16; col += 16)
        {
            bool bHasPoint = false;

            cv::Point2d p1(0, 0), p2(0, 0);
            int count = 0;
            for (int ii = -8; ii < 8; ii++)
            {
                for (int jj = -8; jj < 8; jj++)
                {
                    if (mModelError[camera_index][row + ii][col + jj].size() > 0)
                    {
                        for (int i = 0; i < mModelError[camera_index][row + ii][col + jj].size(); i++)
                        {
                            auto p0 = mModelError[camera_index][row + ii][col + jj][i].first;
                            auto pi = mModelError[camera_index][row + ii][col + jj][i].second;
                            if (pi.x < 0 || pi.x >= camera->GetWidth() || pi.y < 0 || pi.y >= camera->GetHeight())
                            {
                                continue;
                            }

                            count++;
                            p1 += p0;
                            p2 += pi;
                            bHasPoint = true;

                            // Error.at<cv::Vec3b>(pi)[2] = 255;
                        }
                    }
                }
            }
            p1 = p1 / count;
            p2 = p2 / count;

            if (bHasPoint)
            {
                bUpdate = true;
                cv::line(Error, p1 * scale, p2 * scale,
                         cv::Scalar(0, 0, 255), 3, cv::LINE_AA);
            }
        }
    }

    if (bUpdate)
    {
        cv::namedWindow("ModelError" + std::to_string(camera_index), cv::WINDOW_NORMAL);
        cv::resizeWindow("ModelError" + std::to_string(camera_index), 640, 480);
        cv::imshow("ModelError" + std::to_string(camera_index), Error);

        cv::imwrite("ModelError " + std::to_string(camera_index) + ".png", Error);
        cv::waitKey();
    }

#endif

    cv::Point2d mean_error(0, 0);
    cv::Point2d max_error(0, 0);
    cv::Point2d std_error(0, 0);
    size_t count = 0;
    for (int row = 0; row < camera->GetHeight(); row += 1)
    {
        for (int col = 0; col < camera->GetWidth(); col += 1)
        {
            if (mModelError[camera_index][row][col].size() > 0)
            {
                for (int i = 0; i < mModelError[camera_index][row][col].size(); i++)
                {
                    auto p0 = mModelError[camera_index][row][col][i].first;
                    auto pi = mModelError[camera_index][row][col][i].second;
                    auto d = pi - p0;
                    mean_error = mean_error + d;
                    count++;

                    if (Eigen::Vector2d(d.x, d.y).norm() > Eigen::Vector2d(max_error.x, max_error.y).norm())
                    {
                        max_error = d;
                        if (!bUpdate)
                        {
                            bUpdate = true;
                        }
                    }
                }
            }
        }
    }
    mean_error.x = mean_error.x / count;
    mean_error.y = mean_error.y / count;
    for (int row = 0; row < camera->GetHeight(); row += 1)
    {
        for (int col = 0; col < camera->GetWidth(); col += 1)
        {
            if (mModelError[camera_index][row][col].size() > 0)
            {
                for (int i = 0; i < mModelError[camera_index][row][col].size(); i++)
                {
                    auto p0 = mModelError[camera_index][row][col][i].first;
                    auto pi = mModelError[camera_index][row][col][i].second;
                    auto d = pi - p0;

                    d = (d - mean_error);

                    std_error.x = std_error.x + d.x * d.x;
                    std_error.y = std_error.y + d.y * d.y;
                    bUpdate = true;
                }
            }
        }
    }
    std_error.x = std_error.x / count;
    std_error.y = std_error.y / count;

    if (bUpdate)
    {
        std::cout << "camera " << camera_index << ",count =" << count << std::endl;
        std::cout << "camera " << camera_index << ",mean reproject error " << mean_error << std::endl;
        std::cout << "camera " << camera_index << ",max reproject error " << max_error << std::endl;
        std::cout << "camera " << camera_index << ",std reproject error " << std_error << std::endl;
        mMeanError[camera_index] = mean_error;
        mMaxError[camera_index] = max_error;
        mStdError[camera_index] = std_error;
        mCount[camera_index]=count;
        if (mOutFile.is_open())
        {

            mOutFile << "camera " << camera_index << ",count =" << count << std::endl;
            mOutFile << "camera " << camera_index << ",mean reproject error " << mean_error << std::endl;
            mOutFile << "camera " << camera_index << ",max reproject error " << max_error << std::endl;
            mOutFile << "camera " << camera_index << ",std reproject error " << std_error << std::endl;
        }
    }
    else
    {
        std::cout << "camera " << camera_index << " cannot detect calibrate points" << std::endl;
        if (mOutFile.is_open())
        {
            mOutFile << "camera " << camera_index << " cannot detect calibrate points" << std::endl;
        }
    }
}

cv::Point2d ModelError::GetMeanError(int cam_id)
{
    if(cam_id>=mCamId2Index.size())
    {
        return cv::Point2d();
    }
    int camera_index = mCamId2Index[cam_id];
    return mMeanError[camera_index];

}
cv::Point2d ModelError::GetMaxError(int cam_id)
{
    if(cam_id>=mCamId2Index.size())
    {
        return cv::Point2d();
    }
     int camera_index = mCamId2Index[cam_id];
     return mMaxError[camera_index];

}
cv::Point2d ModelError::GetStdError(int cam_id)
{
    if(cam_id>=mCamId2Index.size())
    {
        return cv::Point2d();
    }
     int camera_index = mCamId2Index[cam_id];
     return mStdError[camera_index];

}
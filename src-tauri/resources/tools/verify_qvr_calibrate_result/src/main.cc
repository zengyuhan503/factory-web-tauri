#include "DetectBoard.h"
#include "Utils.h"
#include "ReadQvrCalResult.h"
#include "ReadQvrCalPoses.h"
#include "ReprojectionError.h"
#include <opencv2/imgproc.hpp>
#include "Drawer.h"
#include "ModelError.h"
#include "ErrorCode.h"
#include <chrono>
#include <thread>
#define MIN_POINTS_NUM 100
int detect_camera(cv::Mat img, Eigen::Matrix4d pose, int cam_id, DetectBoard &detectBoard, ReprojectionError &reprojectionError, ModelError &modelError)
{
    std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points;
    std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points;

    if (detectBoard.detect_board(img, board_a_points, board_b_points) < 0)
    {
        return -1;
    }

    reprojectionError.ComputeError(board_a_points, board_b_points, pose, cam_id, img);

    modelError.ComputeError(board_a_points, board_b_points, cam_id);

    return 0;
}
int main(int argc, char **argv)
{
#ifdef MEASURE_RUNNING_TIME
    // 设置开始时间
    auto start = std::chrono::system_clock::now();
#endif
    Error error = 0;

    std::string calibrate_path = std::string("/run/user/1000/gvfs/smb-share:server=172.28.248.234,share=ssnwt/skycalib/CalibratResult/2338519280");
    std::string rgb_camera4_path = calibrate_path + "/qvrdataset/34116397538.log/Camera4";
    std::string rgb_camera5_path = calibrate_path + "/qvrdataset/34116397538.log/Camera5";
    std::string tracking_camera8_path = calibrate_path + "/qvrdataset/34116397538.log/Camera8";
    std::string tracking_camera9_path = calibrate_path + "/qvrdataset/34116397538.log/Camera9";
    std::string device_calibration_path = calibrate_path + "/qvrdataset/calibDetails/device_calibration.xml";
    std::string target_config_path = calibrate_path + "/qvrdataset/Target-config.xml";
    std::string poses_path = calibrate_path + "/qvrdataset/calibDetails/XRCalibPoses.json";

    if (argc == 2)
    {
        calibrate_path = std::string(argv[1]);
        std::cout << calibrate_path << std::endl;
        std::string img_path;
        std::vector<std::string> dirs = get_subdirectory(calibrate_path + "/qvrdataset/");
        for (auto dir : dirs)
        {
            if (endWith(dir, ".log"))
            {
                std::cout << "dir=" << dir << std::endl;
                img_path = dir;
                break;
            }
        }
        rgb_camera4_path = img_path + "/Camera4";
        rgb_camera5_path = img_path + "/Camera5";
        tracking_camera8_path = img_path + "/Camera8";
        tracking_camera9_path = img_path + "/Camera9";
        device_calibration_path = calibrate_path + "/qvrdataset/calibDetails/device_calibration.xml";
        target_config_path = calibrate_path + "/qvrdataset/Target-config.xml";
        poses_path = calibrate_path + "/qvrdataset/calibDetails/XRCalibPoses.json";
    }
    else
    {
         std::cout << "usage: verify_qvr_calibrate_result data_dir" << std::endl;
         return -1;
    }
    ReadQvrCalResult device_calibration(device_calibration_path, target_config_path);
    ReadQvrCalPoses poses(poses_path);
    std::vector<Eigen::Matrix4d> qvr_poses;
#ifdef SHOW
    Drawer drawer;
    drawer.Run();
    ReprojectionError repreject_error(device_calibration, &drawer);
#else
    ReprojectionError repreject_error(device_calibration);
#endif

    ModelError modelError(device_calibration, calibrate_path + "/qvrdataset/verify_result.txt");
    DetectBoard detectBoard0;
    DetectBoard detectBoard1;
    DetectBoard detectBoard2;
    DetectBoard detectBoard3;
    DetectBoard detectBoard4;
    DetectBoard detectBoard5;

    auto tracking_camera4_imgs = get_directory_files(rgb_camera4_path);
    auto tracking_camera5_imgs = get_directory_files(rgb_camera5_path);

    auto tracking_camera8_imgs = get_directory_files(tracking_camera8_path);
    auto tracking_camera9_imgs = get_directory_files(tracking_camera9_path);

    boost::filesystem::path p(tracking_camera8_imgs[0]);
    auto tracking_camera8_dir = p.remove_filename().string();

    // std::cout << "tracking_camera8_dir=" << tracking_camera8_dir << std::endl;
    std::vector<std::thread> workers;

    //  workers.push_back(std::thread([&]()
                                  {
                                      bool bOK_Left = false;
                                      bool bOK_Right = false;
                                      for (int i = 0; i < tracking_camera8_imgs.size(); i++)
                                      {

                                          std::string path = tracking_camera8_imgs[i];
                                          // cv::Mat src = cv::imread("/home/home/chuanqi/work/Github/skycalib/3212055723-230922/3212055723/qvrdataset/34116397538.log/Camera8/47180233945.pgm");
                                          std::cout << path << std::endl;
                                          cv::Mat src = cv::imread(path);
                                          if (src.empty())
                                          {
                                              continue;
                                          }
                                          cv::Mat Left = src(cv::Rect(0, 0, 640, 480));
                                          cv::Mat Right = src(cv::Rect(640, 0, 640, 480));

                                          if (poses.m_poses.empty())
                                          {
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points0;
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points0;
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points1;
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points1;
                                              if(!bOK_Left)
                                              {
                                                    if(detectBoard0.detect_board(Left, board_a_points0, board_b_points0)==0)
                                                    {
                                                        bOK_Left=true;
                                                    }
                                                
                                              }
                                              if(!bOK_Right)
                                              {
                                                    if(detectBoard1.detect_board(Right, board_a_points1, board_b_points1)==0)
                                                    {
                                                        bOK_Right=true;
                                                    }
                                                
                                              }
                                                if(bOK_Left && bOK_Right)
                                                {
                                                  break;
                                                }
                                          }
                                          else
                                          {
                                              std::size_t t;
                                              boost::filesystem::path p(path);
                                              boost::filesystem::path filename = p.filename();
                                              std::stringstream ss(filename.string()); // 将字符串初始化到stringstream中
                                              ss >> t;
                                              Eigen::Matrix4d pose;
                                              if(poses.GetPose(t, pose) == 0)
                                              {
                                                    if(!bOK_Left)
                                                {
                                                    
                                                    if (detect_camera(Left, pose, 0, detectBoard0, repreject_error, modelError)==0)
                                                    {
                                                        bOK_Left=true;
                                                    }
                                                }
                                                if(!bOK_Right)
                                                {
                                                    
                                                    if (detect_camera(Right, pose, 1, detectBoard1, repreject_error, modelError)==0)
                                                    {
                                                        bOK_Right=true;
                                                    }
                                                }

                                              }
                                              if(bOK_Left && bOK_Right)
                                                {
                                                  break;
                                                }
                                          }

                                          
                                      }
                                      if (!bOK_Left && tracking_camera8_imgs.size() > 0)
                                      {
                                          error |= ErrorCode::CAMERA0_DETECT_DERROR;
                                      }
                        
                                      if(!bOK_Right && tracking_camera8_imgs.size()>0)
                                      {
                                        error |= ErrorCode::CAMERA1_DETECT_DERROR;
                                      } }//));
#ifdef SHOW

    for (auto &worker : workers)
    {
        if(worker.joinable())
        {
            worker.join();
        }
        
    }

#endif
  // workers.push_back(std::thread([&]()
                                  {
                                      bool bOK_Left = false;
                                      bool bOK_Right = false;
                                      for (int i = 0; i < tracking_camera9_imgs.size(); i++)
                                      {

                                          std::string path = tracking_camera9_imgs[i];
                                          // cv::Mat src = cv::imread("/home/home/chuanqi/work/Github/skycalib/3212055723-230922/3212055723/qvrdataset/34116397538.log/Camera8/47180233945.pgm");
                                          std::cout << path << std::endl;
                                          cv::Mat src = cv::imread(path);
                                          if (src.empty())
                                          {
                                              continue;
                                          }
                                          cv::Mat Left = src(cv::Rect(0, 0, 640, 480));
                                          cv::Mat Right = src(cv::Rect(640, 0, 640, 480));

                                          if (poses.m_poses.empty())
                                          {
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points2;
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points2;
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points3;
                                              std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points3;
                                              if(!bOK_Left)
                                              {
                                                    if(detectBoard2.detect_board(Left, board_a_points2, board_b_points2)==0)
                                                    {
                                                        bOK_Left=true;
                                                    }
                                                
                                              }
                                              if(!bOK_Right)
                                              {
                                                    if(detectBoard3.detect_board(Right, board_a_points3, board_b_points3)==0)
                                                    {
                                                        bOK_Right=true;
                                                    }
                                                
                                              }
                                                if(bOK_Left && bOK_Right)
                                                {
                                                  break;
                                                }
                                          }
                                          else
                                          {
                                              std::size_t t;
                                              boost::filesystem::path p(path);
                                              boost::filesystem::path filename = p.filename();
                                              std::stringstream ss(filename.string()); // 将字符串初始化到stringstream中
                                              ss >> t;
                                              Eigen::Matrix4d pose;

                                               if(poses.GetPose(t, pose) == 0)
                                              {
                                                    if(!bOK_Left)
                                                {
                                                    if(detect_camera(Left, pose, 2, detectBoard2, repreject_error, modelError)==0)
                                                    {
                                                        bOK_Left=true;
                                                    }
                                                }
                                                if(!bOK_Right)
                                                {
                                                    if (detect_camera(Right, pose, 3, detectBoard3, repreject_error, modelError)==0)
                                                    {
                                                        bOK_Right=true;
                                                    }
                                                }

                                              }
                                              

                                              if(bOK_Left && bOK_Right)
                                                {
                                                  break;
                                                }
                                          }

                                          
                                      }
                                      if (!bOK_Left && tracking_camera9_imgs.size() > 0)
                                      {
                                          error |= ErrorCode::CAMERA2_DETECT_DERROR;
                                      }
                        
                                      if(!bOK_Right && tracking_camera9_imgs.size()>0)
                                      {
                                        error |= ErrorCode::CAMERA3_DETECT_DERROR;
                                      } }//));
#ifdef SHOW

    for (auto &worker : workers)
    {
        if(worker.joinable())
        {
            worker.join();
        }
    }

#endif

   // workers.push_back(std::thread([&]()
                                  {
                                    
                                  bool bOK=false;
                                      for (int i = 0; i < tracking_camera4_imgs.size(); i++)
                                      {

                                          std::string path = tracking_camera4_imgs[i];
                                          // cv::Mat src = cv::imread("/home/home/chuanqi/work/Github/skycalib/3212055723-230922/3212055723/qvrdataset/34116397538.log/Camera8/47180233945.pgm");
                                          std::cout << path << std::endl;
                                          cv::Mat src = cv::imread(path);
                                          if (src.empty())
                                          {
                                              continue;
                                          }
                                         

                                        //  if(poses.m_poses.empty())
                                          {
                                                std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points;
                                                std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points;

                                                detectBoard4.detect_board(src, board_a_points, board_b_points);
                                                for(auto &board:board_a_points)
                                                {
                                                    if(board.size()>10)
                                                    {
                                                        std::cout<<"detectBoard4 board.size="<<board.size()<<std::endl;
                                                        bOK=true;
                                                        break;
                                                    }
                                                }
                                                if(bOK)
                                                {
                                                  break;
                                                }
                                            

                                          }

                                          
                                      } 
                                      if(!bOK && tracking_camera4_imgs.size()>0)
                                      {
                                        error |= ErrorCode::CAMERA4_DETECT_DERROR;
                                      } }
                                      //));

#ifdef SHOW

    for (auto &worker : workers)
    {
        if(worker.joinable())
        {
            worker.join();
        }
    }

#endif
   // workers.push_back(std::thread([&]()
                                  {
                                  
                                  bool bOK=false;
                                      for (int i = 0; i < tracking_camera5_imgs.size(); i++)
                                      {

                                          std::string path = tracking_camera5_imgs[i];
                                          // cv::Mat src = cv::imread("/home/home/chuanqi/work/Github/skycalib/3212055723-230922/3212055723/qvrdataset/34116397538.log/Camera8/47180233945.pgm");
                                          std::cout << path << std::endl;
                                          cv::Mat src = cv::imread(path);
                                          if (src.empty())
                                          {
                                              continue;
                                          }
                                         

                                         // if(poses.m_poses.empty())
                                          {
                                                std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_a_points;
                                                std::vector<std::vector<std::weak_ptr<PointCalibrateBoard>>> board_b_points;

                                                detectBoard5.detect_board(src, board_a_points, board_b_points);
                                                for(auto &board:board_a_points)
                                                {
                                                    if(board.size()>10)
                                                    {
                                                        std::cout<<"detectBoard5 board.size="<<board.size()<<std::endl;
                                                        bOK=true;
                                                        break;
                                                    }
                                                }
                                                if(bOK)
                                                {
                                                  break;
                                                }
                                                
                                            

                                          }

                                          
                                      } 
                                      if(!bOK && tracking_camera5_imgs.size()>0)
                                      {
                                        error |= ErrorCode::CAMERA5_DETECT_DERROR;
                                      } }//));

    for (auto &worker : workers)
    {
        if(worker.joinable())
        {
            worker.join();
        }
    }
    if(device_calibration.cameras.size()>=4)
    {
        modelError.StatisticError(0);
        modelError.StatisticError(1);
        modelError.StatisticError(2);
        modelError.StatisticError(3);
        size_t count0=modelError.GetCount(0);
        size_t count1=modelError.GetCount(1);
        size_t count2=modelError.GetCount(2);
        size_t count3=modelError.GetCount(3);
        cv::Point2d mean0=modelError.GetMeanError(0);
        cv::Point2d mean1=modelError.GetMeanError(1);
        cv::Point2d mean2=modelError.GetMeanError(2);
        cv::Point2d mean3=modelError.GetMeanError(3);

        cv::Point2d max0=modelError.GetMaxError(0);
        cv::Point2d max1=modelError.GetMaxError(1);
        cv::Point2d max2=modelError.GetMaxError(2);
        cv::Point2d max3=modelError.GetMaxError(3);


        cv::Point2d std0=modelError.GetStdError(0);
        cv::Point2d std1=modelError.GetStdError(1);
        cv::Point2d std2=modelError.GetStdError(2);
        cv::Point2d std3=modelError.GetStdError(3);
        if ( count0< 100||Eigen::Vector2d(mean0.x,mean0.y).norm()>3.0)
        {
            error |= ErrorCode::CAMERA0_REPROJECT_DERROR;
            std::cout << "ErrorCode=" << error << ",CAMERA0_REPROJECT_DERROR" << std::endl;
        }
        if ( count0< 100||Eigen::Vector2d(mean1.x,mean1.y).norm()>3.0)
        {
            error |= ErrorCode::CAMERA1_REPROJECT_DERROR;
            std::cout << "ErrorCode=" << error << ",CAMERA1_REPROJECT_DERROR" << std::endl;
        }
        if ( count0< 100||Eigen::Vector2d(mean2.x,mean2.y).norm()>3.0)
        {
            error |= ErrorCode::CAMERA2_REPROJECT_DERROR;
            std::cout << "ErrorCode=" << error << ",CAMERA2_REPROJECT_DERROR" << std::endl;
        }
        if ( count0< 100||Eigen::Vector2d(mean3.x,mean3.y).norm()>3.0)
        {
            error |= ErrorCode::CAMERA3_REPROJECT_DERROR;
            std::cout << "ErrorCode=" << error << "CAMERA3_REPROJECT_DERROR" << std::endl;
        }
    }
    

    
#ifdef MEASURE_RUNNING_TIME
    // 设置结束时间
    auto end = std::chrono::system_clock::now();

    // 精确到微秒，除此之外，还有五种时间单位：hours, minutes, seconds, milliseconds, nanoseconds
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    std::cout << "totol time duration= " << double(duration.count()) * std::chrono::microseconds::period::num / std::chrono::microseconds::period::den << std::endl;
#endif
#ifdef SHOW
    drawer.Stop();
#endif
    if (error & ErrorCode::CAMERA0_DETECT_DERROR)
    {
        std::cout << "CAMERA0_DETECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA1_DETECT_DERROR)
    {
        std::cout << "CAMERA1_DETECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA2_DETECT_DERROR)
    {
        std::cout << "CAMERA2_DETECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA3_DETECT_DERROR)
    {
        std::cout << "CAMERA3_DETECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA4_DETECT_DERROR)
    {
        std::cout << "CAMERA4_DETECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA5_DETECT_DERROR)
    {
        std::cout << "CAMERA5_DETECT_DERROR" << std::endl;
    }

    if (error & ErrorCode::CAMERA0_REPROJECT_DERROR)
    {
        std::cout << "CAMERA0_REPROJECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA1_REPROJECT_DERROR)
    {
        std::cout << "CAMERA1_REPROJECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA2_REPROJECT_DERROR)
    {
        std::cout << "CAMERA2_REPROJECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA3_REPROJECT_DERROR)
    {
        std::cout << "CAMERA3_REPROJECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA4_REPROJECT_DERROR)
    {
        std::cout << "CAMERA4_REPROJECT_DERROR" << std::endl;
    }
    if (error & ErrorCode::CAMERA5_REPROJECT_DERROR)
    {
        std::cout << "CAMERA5_REPROJECT_DERROR" << std::endl;
    }
    return error;
}

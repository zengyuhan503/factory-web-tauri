#include "Drawer.h"
#include "opencv2/highgui.hpp"
#include <thread>
#ifdef SHOW
Drawer::Drawer(/* args */)
{
}

Drawer::~Drawer()
{
}
std::shared_ptr<std::thread> show;
void Drawer::Run()
{

    show = std::make_shared<std::thread>(
      [&](){
        while (poses_cal.empty())
        {
            if(!mbRun)
            {
                return;
            }
            std::this_thread::sleep_for(std::chrono::microseconds(10));
        }
        
    pangolin::CreateWindowAndBind("Main", 1024, 768);
    glEnable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
       s_cam = pangolin::OpenGlRenderState(
        pangolin::ProjectionMatrix(1024, 768, mViewpointF, mViewpointF, 512, 389, 0.1, 1000),
        pangolin::ModelViewLookAt(mViewpointX, mViewpointY, mViewpointZ, 0, 0, 0, 0.0, -1.0, 0.0));

    pangolin::Handler3D handler(s_cam);
    d_cam = pangolin::CreateDisplay()
                .SetBounds(0.0, 1.0, pangolin::Attach::Pix(175), 1.0, -1024.0f / 768.0f)
                .SetHandler(&handler);
    
     size_t cont=poses_cal.size();
    while (!pangolin::ShouldQuit())
    {
        if(!mbRun)
        {
            return;
        }
        if(poses_cal.empty())
        {
         
            continue;
        }
       
       

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        d_cam.Activate(s_cam);
        pangolin::OpenGlMatrix Twc;
        Twc.SetIdentity();
        pangolin::OpenGlMatrix Ow; // Oriented with g in the z axis
        Ow.SetIdentity();
        GetOpgenglCameraMatrix(poses_qvr[0], Twc, Ow);

        s_cam.Follow(Ow);

        // 需要绘制的东西写在这里
        const float &w = mKeyFrameSize;
        const float h = w * 0.75;
        const float z = w * 0.6;
        std::lock_guard<std::mutex> lk(mTx);

        for (size_t i = 0; i < poses_cal.size(); i++)
        {
            auto pose = poses_qvr[i];

            Eigen::Matrix4d Twc = pose.matrix();
            ;
            // unsigned int index_color = pKF->mnOriginMapId;

            glPushMatrix();

            glMultMatrixd((GLdouble *)Twc.data());



                // cout << "Child KF: " << (Map::IdSharedPtrKeyFrames(vpKFs[i]))->mnId << endl;
            glLineWidth(mKeyFrameLineWidth);

            glColor3f(1.0f, 1.0f, 1.0f); // Basic color

            glBegin(GL_LINES);

            

            glVertex3f(0, 0, 0);
            glVertex3f(w, h, z);
            glVertex3f(0, 0, 0);
            glVertex3f(w, -h, z);
            glVertex3f(0, 0, 0);
            glVertex3f(-w, -h, z);
            glVertex3f(0, 0, 0);
            glVertex3f(-w, h, z);

            glVertex3f(w, h, z);
            glVertex3f(w, -h, z);

            glVertex3f(-w, h, z);
            glVertex3f(-w, -h, z);

            glVertex3f(-w, h, z);
            glVertex3f(w, h, z);

            glVertex3f(-w, -h, z);
            glVertex3f(w, -h, z);
            glEnd();

            glPopMatrix();

            glEnd();
        }

        for (size_t i = 0; i < poses_cal.size(); i++)
        {
            auto pose = poses_cal[i];
            auto pose_qvr = poses_qvr[i];

            auto diff=pose*pose_qvr.inverse();
             if(cont!=poses_cal.size())
            {
                std::cout<<"diff="<<diff.matrix()<<std::endl;
            }

            

            

            Eigen::Matrix4d Twc = pose.matrix();
            ;
            // unsigned int index_color = pKF->mnOriginMapId;

            glPushMatrix();

            glMultMatrixd((GLdouble *)Twc.data());


                // cout << "Child KF: " << (Map::IdSharedPtrKeyFrames(vpKFs[i]))->mnId << endl;
            glLineWidth(mKeyFrameLineWidth);

            glColor3f(1.0f, 0.0f, 0.0f); // Basic color

            glBegin(GL_LINES);
            

            glVertex3f(0, 0, 0);
            glVertex3f(w, h, z);
            glVertex3f(0, 0, 0);
            glVertex3f(w, -h, z);
            glVertex3f(0, 0, 0);
            glVertex3f(-w, -h, z);
            glVertex3f(0, 0, 0);
            glVertex3f(-w, h, z);

            glVertex3f(w, h, z);
            glVertex3f(w, -h, z);

            glVertex3f(-w, h, z);
            glVertex3f(-w, -h, z);

            glVertex3f(-w, h, z);
            glVertex3f(w, h, z);

            glVertex3f(-w, -h, z);
            glVertex3f(w, -h, z);
            glEnd();

            glPopMatrix();

            glEnd();
        }
        cont=poses_cal.size();
        //

        pangolin::FinishFrame();
    } });
    show->detach();
}

void Drawer::GetOpgenglCameraMatrix(Eigen::Matrix4d pose, pangolin::OpenGlMatrix &M, pangolin::OpenGlMatrix &MOw)
{
    Eigen::Matrix4d Twc;

    Twc = pose.matrix();
    ;

    for (int i = 0; i < 4; i++)
    {
        M.m[4 * i] = Twc(0, i);
        M.m[4 * i + 1] = Twc(1, i);
        M.m[4 * i + 2] = Twc(2, i);
        M.m[4 * i + 3] = Twc(3, i);
    }

    MOw.SetIdentity();
    MOw.m[12] = Twc(0, 3);
    MOw.m[13] = Twc(1, 3);
    MOw.m[14] = Twc(2, 3);
}
void Drawer::SetQvrPoses(std::vector<Eigen::Matrix4d> poses)
{
    std::lock_guard<std::mutex> lk(mTx);
    poses_qvr=poses;
}

void Drawer::SetCalPoses(std::vector<Eigen::Matrix4d> poses)
{
    std::lock_guard<std::mutex> lk(mTx);
    poses_cal=poses;
}
#endif
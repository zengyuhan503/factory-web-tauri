
#include "ReadQvrCalPoses.h"
#include <fstream>
#include <iostream>
#include "Utils.h"
ReadQvrCalPoses::ReadQvrCalPoses(std::string pose_file)
{
   std::ifstream ifs(pose_file);
   Json::Reader reader;
   Json::Value obj;

   while (ifs.good())
   {
      char szBuf[1024] = {0};
      ifs.getline(szBuf, 1024);
      reader.parse(szBuf, obj);
      std::size_t time = obj["t_ns"].asUInt64();
      m_timestamps.push_back(time);
      Eigen::Matrix4d pose=Eigen::Matrix4d::Identity();

      pose << obj["Rcp"][0].asDouble(), obj["Rcp"][1].asDouble(), obj["Rcp"][2].asDouble(),obj["Tcp_mm"][0].asDouble()*0.001,
          obj["Rcp"][3].asDouble(), obj["Rcp"][4].asDouble(), obj["Rcp"][5].asDouble(),obj["Tcp_mm"][1].asDouble()*0.001,
          obj["Rcp"][6].asDouble(), obj["Rcp"][7].asDouble(), obj["Rcp"][8].asDouble(),obj["Tcp_mm"][2].asDouble()*0.001,
          0,0,0,1;
      
      m_poses.push_back(pose);

     // std::cout << "t_ns=" << obj["t_ns"] << std::endl;
     // std::cout << "pose=" << pose << std::endl;
   }
}

ReadQvrCalPoses::~ReadQvrCalPoses()
{
}
int  ReadQvrCalPoses::GetNearTimes(std::size_t time_now,std::size_t &time_pre_index,std::size_t &time_next_index)
{
   if(time_pre_index+1==time_next_index )
   {
      // std::cout<<"6time_now="<<time_now<<",m_timestamps["<<time_pre_index<<"]= "<<m_timestamps[time_pre_index] <<",m_timestamps["<<time_next_index<<"]="<<m_timestamps[time_next_index]<<std::endl;
      return 0;
   }
   std::size_t time_midle_index=(time_pre_index+time_next_index)/2;
   
   if(time_now==m_timestamps[time_pre_index] )
   {
      time_next_index=time_pre_index;
       //std::cout<<"1time_now="<<time_now<<",m_timestamps["<<time_pre_index<<"]= "<<m_timestamps[time_pre_index] <<",m_timestamps["<<time_next_index<<"]="<<m_timestamps[time_next_index]<<std::endl;
      return 0;
   }
   if(time_now==m_timestamps[time_midle_index] )
   {
      time_pre_index=time_midle_index;
      time_next_index=time_midle_index;
      // std::cout<<"2time_now="<<time_now<<",m_timestamps["<<time_pre_index<<"]= "<<m_timestamps[time_pre_index] <<",m_timestamps["<<time_next_index<<"]="<<m_timestamps[time_next_index]<<std::endl;
      return 0;
   }
   if(time_now==m_timestamps[time_next_index] )
   {
      time_pre_index=time_next_index;
       //std::cout<<"3time_now="<<time_now<<",m_timestamps["<<time_pre_index<<"]= "<<m_timestamps[time_pre_index] <<",m_timestamps["<<time_next_index<<"]="<<m_timestamps[time_next_index]<<std::endl;
      return 0;
   }

   
   if(m_timestamps[time_pre_index]<time_now && m_timestamps[time_midle_index]>time_now)
   {
      time_next_index=time_midle_index;
      // std::cout<<"4time_now="<<time_now<<",m_timestamps["<<time_pre_index<<"]= "<<m_timestamps[time_pre_index] <<",m_timestamps["<<time_next_index<<"]="<<m_timestamps[time_next_index]<<std::endl;
      GetNearTimes(time_now,time_pre_index,time_next_index);
   }
   if(m_timestamps[time_midle_index]<time_now && m_timestamps[time_next_index]>time_now)
   {
      time_pre_index=time_midle_index;
      //std::cout<<"5time_now="<<time_now<<",m_timestamps["<<time_pre_index<<"]= "<<m_timestamps[time_pre_index] <<",m_timestamps["<<time_next_index<<"]="<<m_timestamps[time_next_index]<<std::endl;
      GetNearTimes(time_now,time_pre_index,time_next_index);
   }
   
   return -1;
}

int ReadQvrCalPoses::GetPose(std::size_t time,Eigen::Matrix4d &pose)
{
   std::size_t time_pre_index=0;
   std::size_t time_next_index=m_timestamps.size()-1;
   GetNearTimes(time,time_pre_index,time_next_index);
   
   if(time_next_index==time_pre_index)
   {
      //std::cout<<"time="<<time<<std::endl;
      //std::cout<<"pose="<<m_poses[time_pre_index].matrix()<<std::endl;
      pose=m_poses[time_pre_index];
      return 0;
   }
   size_t dt1=m_timestamps[time_next_index]-time;
   size_t dt2=time-m_timestamps[time_pre_index];
   if(dt1<1e6 &&dt1<dt2)
   {
      pose=m_poses[time_next_index];
      return 0;
     
   }
   if(dt2<1e6 &&dt1>dt2)
   {
      pose=m_poses[time_pre_index];
      return 0;
     
   }
 
   
   return -1;



}
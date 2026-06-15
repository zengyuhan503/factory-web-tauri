#include <map>
#include <jsoncpp/json/json.h>
#include <fstream>
#include <sys/stat.h>
#include <opencv2/imgproc.hpp>
#include <iostream>
#include <memory>
#include <Settings.h>

enum DataType
{
    isInt,
    isFloat,
    isDouble,
    isString,
    isEigenMatrix,
    isEigenVec,
    isCvMat
};
struct VarData
{
    /* data */
    std::shared_ptr<void> data;
    DataType data_type;
};
std::pair<std::string,double> get_kalibr_data(std::string pre_key, std::string key,std::string data)
{
    auto key_pos_start=data.find(key);
    auto key_pos_end=data.find(' ',key_pos_start);
    auto key_data_start=key_pos_end+1;
    auto key_data_end=data.find(',',key_data_start);
    std::stringstream s(data.substr(key_data_start,key_data_end-key_data_start));
    double double_data;
    s>>double_data;
    std::cout<<"read "<<pre_key<<"_"<<key<<"="<<double_data<<std::endl;
    return std::make_pair(pre_key+"_"+key,double_data);
}

void add_cfg_data(std::pair<std::string, double> &data_in, std::map<std::string, VarData> &cfg)
{
    VarData data;
    data.data = std::make_shared<double>();
    data.data_type = isDouble;
    std::shared_ptr<double> p=  std::static_pointer_cast<double>(data.data);
    *p = data_in.second;
    cfg[data_in.first] = data;
}

void read_kalibr_result(std::string calib_txt,std::map<std::string, VarData> &cfg)
{
    std::ifstream calibr_result(calib_txt);
    std::string str_data;
    int line_num=0;
    while (getline(calibr_result,str_data))
    {
        /* code */
        line_num++;
        if(line_num<14)
        {
            continue;
        }
        if(line_num==14)
        {
            std::pair<std::string,double>  mean= get_kalibr_data("cam0_Reprojection_error","mean",str_data);
            add_cfg_data(mean,cfg);

            std::pair<std::string,double>  median= get_kalibr_data("cam0_Reprojection_error","median",str_data);
            add_cfg_data(median,cfg);

            std::pair<std::string,double>  std= get_kalibr_data("cam0_Reprojection_error","std",str_data);
            add_cfg_data(std,cfg);

        }
        if(line_num==15)
        {
            std::pair<std::string,double>  mean= get_kalibr_data("cam1_Reprojection_error","mean",str_data);
            add_cfg_data(mean,cfg);

            std::pair<std::string,double>  median= get_kalibr_data("cam1_Reprojection_error","median",str_data);
            add_cfg_data(median,cfg);

            std::pair<std::string,double>  std= get_kalibr_data("cam1_Reprojection_error","std",str_data);
            add_cfg_data(std,cfg);

        }
        if(line_num==16)
        {
            std::pair<std::string,double>  mean= get_kalibr_data("cam2_Reprojection_error","mean",str_data);
            add_cfg_data(mean,cfg);

            std::pair<std::string,double>  median= get_kalibr_data("cam2_Reprojection_error","median",str_data);
            add_cfg_data(median,cfg);

            std::pair<std::string,double>  std= get_kalibr_data("cam2_Reprojection_error","std",str_data);
            add_cfg_data(std,cfg);

        }
        if(line_num==17)
        {
            std::pair<std::string,double>  mean= get_kalibr_data("cam3_Reprojection_error","mean",str_data);
            add_cfg_data(mean,cfg);

            std::pair<std::string,double>  median= get_kalibr_data("cam3_Reprojection_error","median",str_data);
            add_cfg_data(median,cfg);

            std::pair<std::string,double>  std= get_kalibr_data("cam3_Reprojection_error","std",str_data);
            add_cfg_data(std,cfg);

        }
        if(line_num==18)
        {
            std::pair<std::string,double>  mean= get_kalibr_data("imu0_Gyroscope_error","mean",str_data);
            add_cfg_data(mean,cfg);

            std::pair<std::string,double>  median= get_kalibr_data("imu0_Gyroscope_error","median",str_data);
            add_cfg_data(median,cfg);

            std::pair<std::string,double>  std= get_kalibr_data("imu0_Gyroscope_error","std",str_data);
            add_cfg_data(std,cfg);

        }
        if(line_num==19)
        {
            std::pair<std::string,double>  mean= get_kalibr_data("imu0_Accelerometer_error","mean",str_data);
            add_cfg_data(mean,cfg);

            std::pair<std::string,double>  median= get_kalibr_data("imu0_Accelerometer_error","median",str_data);
            add_cfg_data(median,cfg);

            std::pair<std::string,double>  std= get_kalibr_data("imu0_Accelerometer_error","std",str_data);
            add_cfg_data(std,cfg);

        }
        
    }
    


}


void readcfg(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg)
{
    cv::FileNode node = fSettings.root();
    for (auto it = node.begin(); it != node.end(); it++)
    {
        cv::FileNode node = *it;

        if (node.isInt())
        {
            std::cout << "read int " << node.name() << "=" << node.operator int() << std::endl;
            VarData data;
            data.data = std::make_shared<int>() ;
            data.data_type = isInt;
            std::shared_ptr<int> p=  std::static_pointer_cast<int>(data.data);
            *p = node.operator int();
            cfg[node.name()] = data;
        }
        else if (node.isReal())
        {

            std::cout << "read  real " << node.name() << "=" << node.real() << std::endl;
            VarData data;
            data.data = std::make_shared<double>();
            data.data_type = isDouble;
            std::shared_ptr<double> p=  std::static_pointer_cast<double>(data.data);
            *p = node.real();
            cfg[node.name()] = data;
        }
        else if (node.isString())
        {
            std::cout << "read string " << node.name() << "=" << node.string() << std::endl;
            VarData data;
            data.data = std::make_shared<std::string>();
            data.data_type = isString;
            std::shared_ptr<std::string> p=  std::static_pointer_cast<std::string>(data.data);
            *p = node.string();
            cfg[node.name()] = data;
        }
        else
        {
            std::cout << "read mat " << node.name();
            std::cout << "read mat " << node.name() << "=" << node.mat() << std::endl;
            VarData data;
            data.data = std::make_shared<cv::Mat>();
            data.data_type = isCvMat;
            std::shared_ptr<cv::Mat> p=  std::static_pointer_cast<cv::Mat>(data.data);
            *p = node.mat();
            cfg[node.name()] = data;
        }
    }
}


void writecfg(cv::FileStorage &fSettings, std::map<std::string, VarData> &cfg)
{
    for (auto it : cfg)
    {
        std::string key = it.first;
        VarData value = it.second;

        if (value.data_type == isInt)
        {
            std::shared_ptr<int> p = std::static_pointer_cast<int>(value.data);
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isFloat)
        {
             std::shared_ptr<float> p = std::static_pointer_cast<float>(value.data);
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isDouble)
        {
             std::shared_ptr<double> p = std::static_pointer_cast<double>(value.data);
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isString)
        {
             std::shared_ptr<std::string> p = std::static_pointer_cast<std::string>(value.data);
            writeParameter(fSettings, key, *p);
        }
        else if (value.data_type == isCvMat)
        {
            std::shared_ptr<cv::Mat> p = std::static_pointer_cast<cv::Mat>(value.data);
            writeParameter(fSettings, key, *p);
        }
    }
}


bool verifyResult(  std::map<std::string, VarData> &std_cfg,std::map<std::string, VarData> &cfg,std::string key,VarData &dmin,VarData &dmax)
{
    
    VarData value=cfg[key];
    VarData std_value=std_cfg[key];
   // std::cout<<"key="<<key<<std::endl;;
   // std::cout<<"value.data_type="<<value.data_type<<std::endl;
   // std::cout<<"min.data_type="<<min.data_type<<std::endl;

    assert(value.data_type==dmin.data_type);
    assert(value.data_type==dmax.data_type);
    if(value.data_type==isFloat)
    {
        std::shared_ptr<float> val=  std::static_pointer_cast<float>(value.data);
        std::shared_ptr<float> val_std=  std::static_pointer_cast<float>(std_value.data);
        std::shared_ptr<float> val_dmin=  std::static_pointer_cast<float>(dmin.data);
        std::shared_ptr<float> val_dmax=  std::static_pointer_cast<float>(dmax.data);

        if((*val)<=(*val_std)+(*val_dmax)&&(*val)>=(*val_std)-(*val_dmin))
        {
            return true;
        }
        else{
            std::cout<< key<<"="<<(*val)<<", should between "<<(*val_std)-(*val_dmin)<<" and "<<(*val_std)+(*val_dmax)<<std::endl;
            return false;
        }

    }
    else if(value.data_type==isDouble)
    {
         std::shared_ptr<double> val=  std::static_pointer_cast<double>(value.data);
        std::shared_ptr<double> val_std=  std::static_pointer_cast<double>(std_value.data);
        std::shared_ptr<double> val_dmin=  std::static_pointer_cast<double>(dmin.data);
        std::shared_ptr<double> val_dmax=  std::static_pointer_cast<double>(dmax.data);

        if((*val)<=(*val_std)+(*val_dmax)&&(*val)>=(*val_std)-(*val_dmin))
        {
            return true;
        }
        else{
            std::cout<< key<<"="<<(*val)<<", should between "<<(*val_std)-(*val_dmin)<<" and "<<(*val_std)+(*val_dmax)<<std::endl;
            return false;
        }

    }
    else if(value.data_type==isInt)
    {
        std::shared_ptr<int> val=  std::static_pointer_cast<int>(value.data);
        std::shared_ptr<int> val_std=  std::static_pointer_cast<int>(std_value.data);
        std::shared_ptr<int> val_dmin=  std::static_pointer_cast<int>(dmin.data);
        std::shared_ptr<int> val_dmax=  std::static_pointer_cast<int>(dmax.data);

        if((*val)<=(*val_std)+(*val_dmax)&&(*val)>=(*val_std)-(*val_dmin))
        {
            return true;
        }
        else{
            std::cout<< key<<"="<<(*val)<<", should between "<<(*val_std)-(*val_dmin)<<" and "<<(*val_std)+(*val_dmax)<<std::endl;
            return false;
        }

    }
    else if(value.data_type==isCvMat)
    {
        std::shared_ptr<cv::Mat> val=  std::static_pointer_cast<cv::Mat>(value.data);
        std::shared_ptr<cv::Mat> val_std=  std::static_pointer_cast<cv::Mat>(std_value.data);
        std::shared_ptr<cv::Mat> val_dmin=  std::static_pointer_cast<cv::Mat>(dmin.data);
        std::shared_ptr<cv::Mat> val_dmax=  std::static_pointer_cast<cv::Mat>(dmax.data);

        auto size=val->size();
        float std_norm=0;
        float norm=0;

        for (int i = 0; i < size.height; i++)
        {
            for (int j = 0; j < size.width; j++)
            {
                if(i<3&&j<3)
                {
                    if (((*val).at<float>(i, j) <= (*val_std).at<float>(i, j) + (*val_dmax).at<float>(i, j)) && ((*val).at<float>(i, j) >= (*val_std).at<float>(i, j) - (*val_dmin).at<float>(i, j)))
                    {
                        continue;
                        ;
                    }
                    else
                    {
                        std::cout << key << "[" << i << "," << j << "]=" << (*val).at<float>(i, j) << ", should between " << (*val_std).at<float>(i, j) - (*val_dmin).at<float>(i, j) << " and " << (*val_std).at<float>(i, j) + (*val_dmax).at<float>(i, j) << std::endl;
                        return false;
                    }
                }
                else if(i==3&&j==3)
                {
                     norm=norm+(*val).at<float>(i, j)*(*val).at<float>(i, j);
                     std_norm=std_norm+(*val_std).at<float>(i, j);

                }
                
            }
        }
        if(norm>0.001)
        {
            float d=abs((norm-std_norm)/std_norm);
            if(d>0.2)
            {
                std::cout << key <<" translate norm ="<<norm<<",std_norm="<<std_norm<<","<<"(norm-std_norm)/std_norm="<<d<<std::endl;
                return false;
            }
            else
            {
                return true;
            }
        }



    }
    return true;

}

bool verifyKeyValue(std::map<std::string, VarData> &std_cfg,std::map<std::string, VarData> &cfg,std::string key,VarData dmin,VarData dmax)
{

    bool is_ok=true;
    is_ok=verifyResult(std_cfg,cfg,key,dmin,dmax);

    if(is_ok)
    {
         std::cout<<key<<" is OK  \n";
    }
    return is_ok;

}

bool verifyKeyValue(std::map<std::string, VarData> &std_cfg,std::map<std::string, VarData> &cfg,std::string key,cv::Mat dmin,cv::Mat dmax)
{
    VarData min, max;
    auto pmin = std::make_shared<cv::Mat>();
    auto pmax = std::make_shared<cv::Mat>();
    *pmin = dmin;
    *pmax = dmax;
    min.data = pmin;
    min.data_type = isCvMat;
    max.data = pmax;
    max.data_type = isCvMat;
    bool is_ok = true;
    is_ok=verifyResult(std_cfg,cfg,key,min,max);

    if(is_ok)
    {
         std::cout<<key<<" is OK  \n";
    }
    return is_ok;

}
template<typename T>
T max(T data[],int sz)
{
    T ret=-9999999.99;
    for(int i=0;i<sz;i++)
    {
        if(ret<data[i])
        {
            ret=data[i];
        }

    }
    return ret;
}


template<typename T>
T min(T data[],int sz)
{
    T ret=9999999.99;
    for(int i=0;i<sz;i++)
    {
        
        if(ret>data[i])
        {
            ret=data[i];
        }

    }
    return ret;
}

template<typename T>
T diffrent(T data[],int sz)
{
    T tmax=max(data,sz);
    T tmin=min(data,sz);
    T diff=(tmax-tmin)/tmin;
    return diff;
}


bool VerifyCameraMatrixSelf(std::map<std::string, VarData> &cfg,VarData df)
{
    
    double fx[4],fy[4],cx[4],cy[4];
    for(int i=1;i<5;i++)
    {
        auto data_fx=cfg["Camera"+std::to_string(i)+"_fx"];
        if(data_fx.data_type==isDouble)
        {
            fx[i-1]=*std::static_pointer_cast<double>(data_fx.data);
        }
        else if(data_fx.data_type==isFloat)
        {
            fx[i-1]=*std::static_pointer_cast<float>(data_fx.data);
        }

        auto data_fy=cfg["Camera"+std::to_string(i)+"_fy"];
        if(data_fy.data_type==isDouble)
        {
            fy[i-1]=*std::static_pointer_cast<double>(data_fy.data);
        }
        else if(data_fy.data_type==isFloat)
        {
            fy[i-1]=*std::static_pointer_cast<float>(data_fy.data);
        }

        auto data_cx=cfg["Camera"+std::to_string(i)+"_cx"];
        if(data_fx.data_type==isDouble)
        {
            cx[i-1]=*std::static_pointer_cast<double>(data_cx.data);
        }
        else if(data_fx.data_type==isFloat)
        {
            cx[i-1]=*std::static_pointer_cast<float>(data_cx.data);
        }


        auto data_cy=cfg["Camera"+std::to_string(i)+"_cy"];
        if(data_cy.data_type==isDouble)
        {
            cy[i-1]=*std::static_pointer_cast<double>(data_cy.data);
        }
        else if(data_cy.data_type==isFloat)
        {
            cy[i-1]=*std::static_pointer_cast<float>(data_cy.data);
        }
        
    }
    bool ret=true;
    assert(df.data_type==isDouble);
    double d=(*std::static_pointer_cast<double>(df.data));

    if(diffrent(fx,4)>d)
    {
        ret=false;
        std::cout<<"max fx="<<max(fx,4)<<",min fx="<<min(fx,4)<<",and (max-min)/min="<<diffrent(fx,4)<<">"<<d<<std::endl;
    }
    if(diffrent(fy,4)>d)
    {
        ret=false;
        std::cout<<"max fy="<<max(fy,4)<<",min fy="<<min(fy,4)<<",and (max-min)/min="<<diffrent(fy,4)<<">"<<d<<std::endl;
    }
    if(diffrent(cx,4)>d)
    {
        ret=false;
        std::cout<<"max fx="<<max(cx,4)<<",min fx="<<min(cx,4)<<",and (max-min)/min="<<diffrent(cx,4)<<">"<<d<<std::endl;
    }
    if(diffrent(cy,4)>d)
    {
        ret=false;
        std::cout<<"max fx="<<max(cy,4)<<",min fx="<<min(cy,4)<<",and (max-min)/min="<<diffrent(cy,4)<<">"<<d<<std::endl;
    }

    std::cout<<"fx fy cx cy differce is OK\n";
    return ret;

    

}



bool VerifyResults(std::map<std::string, VarData> &std_cfg, std::map<std::string, VarData> &cfg, std::map<std::string, VarData> &verify_cfg)
{
    bool ret=true;
    ret=ret&&VerifyCameraMatrixSelf(cfg,verify_cfg["VerifyCameraMatrixSelf"]);

    ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera1_fx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera1_fy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera2_fx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera2_fy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera3_fx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera3_fy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera4_fx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera4_fy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);

     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera1_cx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera2_cx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera3_cx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera4_cx",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);

     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera1_cy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera2_cy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera3_cy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"Camera4_cy",verify_cfg["Camera_fxfycxcy_min_distance"],verify_cfg["Camera_fxfycxcy_max_distance"]);

    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam0_Reprojection_error_mean",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam1_Reprojection_error_mean",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam2_Reprojection_error_mean",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam3_Reprojection_error_mean",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);

    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam0_Reprojection_error_median",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam1_Reprojection_error_median",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam2_Reprojection_error_median",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam3_Reprojection_error_median",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);

    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam0_Reprojection_error_std",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam1_Reprojection_error_std",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam2_Reprojection_error_std",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"cam3_Reprojection_error_std",verify_cfg["cam_Reprojection_error_min_distance"],verify_cfg["cam_Reprojection_error_max_distance"]);

    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"imu0_Gyroscope_error_mean",verify_cfg["imu_Gyroscope_error_min_distance"],verify_cfg["imu_Gyroscope_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"imu0_Gyroscope_error_median",verify_cfg["imu_Gyroscope_error_min_distance"],verify_cfg["imu_Gyroscope_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"imu0_Gyroscope_error_std",verify_cfg["imu_Gyroscope_error_min_distance"],verify_cfg["imu_Gyroscope_error_max_distance"]);

    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"imu0_Accelerometer_error_mean",verify_cfg["imu_Accelerometer_error_min_distance"],verify_cfg["imu_Accelerometer_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"imu0_Accelerometer_error_median",verify_cfg["imu_Accelerometer_error_min_distance"],verify_cfg["imu_Accelerometer_error_max_distance"]);
    //  ret=ret&&verifyKeyValue(std_cfg,cfg,"imu0_Accelerometer_error_std",verify_cfg["imu_Accelerometer_error_min_distance"],verify_cfg["imu_Accelerometer_error_max_distance"]);
     

     VarData data_tcb_r_min=verify_cfg["Tcb_rotate_min_distance"];
     VarData data_tcb_r_max=verify_cfg["Tcb_rotate_max_distance"];

     VarData data_tcb_t_min=verify_cfg["Tcb_transition_min_distance"];
     VarData data_tcb_t_max=verify_cfg["Tcb_transition_max_distance"];

     double tcb_r_min=(*std::static_pointer_cast<double>(data_tcb_r_min.data));
     double tcb_r_max=(*std::static_pointer_cast<double>(data_tcb_r_max.data));

     double tcb_t_min=(*std::static_pointer_cast<double>(data_tcb_t_min.data));
     double tcb_t_max=(*std::static_pointer_cast<double>(data_tcb_t_max.data));

    cv::Mat IMU_T_c_b_dmin=(cv::Mat_<float>(4,4)<<tcb_r_min, tcb_r_min, tcb_r_min,tcb_t_min, tcb_r_min, tcb_r_min, tcb_r_min, tcb_t_min, tcb_r_min, tcb_r_min, tcb_r_min, tcb_t_min,0., 0., 0., 0.);
    cv::Mat IMU_T_c_b_dmax=(cv::Mat_<float>(4,4)<<tcb_r_max, tcb_r_max, tcb_r_max,tcb_t_max, tcb_r_max, tcb_r_max, tcb_r_max, tcb_t_max, tcb_r_max, tcb_r_max, tcb_r_max, tcb_t_max,0., 0., 0., 0.);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"IMU_T_c1_b",IMU_T_c_b_dmin,IMU_T_c_b_dmax);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"IMU_T_c2_b",IMU_T_c_b_dmin,IMU_T_c_b_dmax);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"IMU_T_c3_b",IMU_T_c_b_dmin,IMU_T_c_b_dmax);
     ret=ret&&verifyKeyValue(std_cfg,cfg,"IMU_T_c4_b",IMU_T_c_b_dmin,IMU_T_c_b_dmax);

     VarData data_imucal_r_min=verify_cfg["Imucal_R_min_distance"];
     VarData data_imucal_r_max=verify_cfg["Imucal_R_max_distance"];

     double imucal_r_min=(*std::static_pointer_cast<double>(data_imucal_r_min.data));
     double imucal_r_max=(*std::static_pointer_cast<double>(data_imucal_r_max.data));

     cv::Mat Imucal_R_dmin=(cv::Mat_<float>(3,3)<<imucal_r_min, imucal_r_min, imucal_r_min,imucal_r_min, imucal_r_min, imucal_r_min, imucal_r_min, imucal_r_min, imucal_r_min);
    cv::Mat Imucal_R_dmax=(cv::Mat_<float>(3,3)<<imucal_r_max, imucal_r_max, imucal_r_max,imucal_r_max, imucal_r_max, imucal_r_max,imucal_r_max, imucal_r_max, imucal_r_max);
    ret=ret&&verifyKeyValue(std_cfg,cfg,"Imucal_R_a",Imucal_R_dmin,Imucal_R_dmax);
    ret=ret&&verifyKeyValue(std_cfg,cfg,"Imucal_R_g",Imucal_R_dmin,Imucal_R_dmax);

     VarData data_imucal_k_min=verify_cfg["Imucal_K_min_distance"];
     VarData data_imucal_k_max=verify_cfg["Imucal_K_max_distance"];
     double imucal_k_min=(*std::static_pointer_cast<double>(data_imucal_k_min.data));
     double imucal_k_max=(*std::static_pointer_cast<double>(data_imucal_k_max.data));

    cv::Mat Imucal_K_dmin=(cv::Mat_<float>(3,3)<<imucal_k_min, 0.0, 0.0,0.0, imucal_k_min, 0.0, 0.0, 0.0, imucal_k_min);
    cv::Mat Imucal_K_dmax=(cv::Mat_<float>(3,3)<<imucal_k_max, 0.0, 0.0,0.0, imucal_k_max, 0.0,0.0, 0.0, imucal_k_max);
    // ret=ret&&verifyKeyValue(std_cfg,cfg,"Imucal_K_a",Imucal_K_dmin,Imucal_K_dmax);
    // ret=ret&&verifyKeyValue(std_cfg,cfg,"Imucal_K_g",Imucal_K_dmin,Imucal_K_dmax);
     

    return  ret;
   

    
}


inline bool FileExists(const std::string &name)
{
    struct stat buffer;
    return (stat(name.c_str(), &buffer) == 0);
}


void add_cfg_data(std::string key, double value,std::map<std::string, VarData> &cfg)
{
    std::pair data=std::make_pair(key,value);
    add_cfg_data(data,cfg);

}

void GenerateDiffConfig()
{
    std::map<std::string, VarData> diff_cfg;
    add_cfg_data("VerifyCameraMatrixSelf",0.1,diff_cfg);
    add_cfg_data("Camera_fxfycxcy_max_distance",20,diff_cfg);
    add_cfg_data("Camera_fxfycxcy_min_distance",20,diff_cfg);
    add_cfg_data("cam_Reprojection_error_max_distance",0.2,diff_cfg);
    add_cfg_data("cam_Reprojection_error_min_distance",0.2,diff_cfg);
    add_cfg_data("imu_Gyroscope_error_max_distance",0.2,diff_cfg);
    add_cfg_data("imu_Gyroscope_error_min_distance",0.2,diff_cfg);

    add_cfg_data("imu_Accelerometer_error_max_distance",1.0,diff_cfg);
    add_cfg_data("imu_Accelerometer_error_min_distance",1.0,diff_cfg);

    add_cfg_data("Tcb_rotate_min_distance",0.1,diff_cfg);
    add_cfg_data("Tcb_rotate_max_distance",0.1,diff_cfg);
    add_cfg_data("Tcb_transition_min_distance",0.02,diff_cfg);
    add_cfg_data("Tcb_transition_max_distance",0.02,diff_cfg);


    add_cfg_data("Imucal_R_min_distance",0.2,diff_cfg);
    add_cfg_data("Imucal_R_max_distance",0.2,diff_cfg);

    add_cfg_data("Imucal_K_min_distance",0.2,diff_cfg);
    add_cfg_data("Imucal_K_max_distance",0.2,diff_cfg);
    cv::FileStorage frSettings("verify_config.yaml", cv::FileStorage::WRITE);
    writecfg(frSettings, diff_cfg);
    frSettings.release();
    


}
int main(int argc, char **argv)
{
    std::string std_configFile = "std_xr2.yaml";
    std::string configFile = "xr2.yaml";
    std::string std_calibrResult="std-results-imucam-data.txt";
    std::string calibrResult="results-imucam-data.txt";
    std::string verify_config_file="verify_config.yaml";

    if (argc < 4 || argc != 4)
    {
        // std::cout << "useage: ./verify_calibrate_result std_xr2.yaml xr2.yaml std-results-imucam-data.txt results-imucam-data.txt verify_config.yaml\n";
        std::cout << "useage: ./verify_calibrate_result std_xr2.yaml xr2.yaml verify_config.yaml\n";
        //GenerateDiffConfig();
        exit(0);
    }
    std_configFile = argv[1];
    configFile=argv[2];
    // std_calibrResult = argv[3];
    // calibrResult = argv[4];
    verify_config_file=argv[3];


    if (!FileExists(std_configFile))
    {
        std::cout << "file " << std_configFile << " is not exist" << std::endl;
        exit(-1);
    }
    if (!FileExists(configFile))
    {
        std::cout << "file " << configFile << " is not exist" << std::endl;
        exit(-1);
    }
    // if (!FileExists(calibrResult))
    // {
    //     std::cout << "file " << calibrResult << " is not exist" << std::endl;
    //     exit(-1);
    // }


    // Open settings file
    cv::FileStorage std_frSettings(std_configFile, cv::FileStorage::READ);
    cv::FileStorage frSettings(configFile, cv::FileStorage::READ);
    cv::FileStorage verify_FrSettings(verify_config_file, cv::FileStorage::READ);
    std::map<std::string, VarData> cfg;
    std::map<std::string, VarData> std_cfg;
    std::map<std::string, VarData> verify_cfg;
    readcfg(frSettings, cfg);
    readcfg(std_frSettings, std_cfg);
    readcfg(verify_FrSettings,verify_cfg);
    // read_kalibr_result(calibrResult,cfg);
    // read_kalibr_result(std_calibrResult,std_cfg);
    bool ok= VerifyResults(std_cfg,cfg,verify_cfg);
    
    std::cout<<"VerifyResults is "<<ok<<std::endl; 
    return ok;

}

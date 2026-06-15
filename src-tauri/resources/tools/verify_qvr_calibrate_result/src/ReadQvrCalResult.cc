#include "ReadQvrCalResult.h"
#include "TinyXML2.h"
#include "Utils.h"
#include <iostream>
using namespace tinyxml2;

void ReadQvrCalResult::TraversingCalResult(XMLNode* node)
{
    if(node == nullptr)
		return;
	if(node->ToDeclaration()) {
		auto declaration = dynamic_cast<XMLDeclaration*>(node);
		//std::cout << "XML 声明，value=" << declaration->Value() << std::endl;
	}
	if(node->ToElement()) {
		auto element = dynamic_cast<XMLElement*>(node);
		//std::cout << "XML 元素，name=" << element->Name() << ", value=" << element->Value() << std::endl;
        const XMLAttribute* attribute = element->FirstAttribute();
        if(std::string(element->Name())==std::string("DeviceConfiguration"))
        {
            while (attribute != nullptr)
            {
               // std::cout << "\t属性 " << attribute->Name() << "=" << attribute->Value() << std::endl;
                if(std::string(attribute->Name())==std::string("deviceUID"))
                {
                    deviceUID=std::string(attribute->Value());
                   // std::cout <<"deviceUID="<<deviceUID<<std::endl;
                }

                attribute = attribute->Next();
            }
            
        }
        if(std::string(element->Name())==std::string("Camera"))
        {
            CameraCalibrateResult cam;
            while (attribute != nullptr)
            {
               // std::cout << "\t属性 " << attribute->Name() << "=" << attribute->Value() << std::endl;
                if(std::string(attribute->Name())==std::string("cam_name"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>cam.cam_name;
                    std::cout <<"cam.cam_name="<<cam.cam_name<<std::endl;
                }
                if(std::string(attribute->Name())==std::string("id"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>cam.id;
                    std::cout <<"cam.id="<<cam.id<<std::endl;
                }

                attribute = attribute->Next();
            }
            XMLNode* child = node->FirstChild();
            auto element = dynamic_cast<XMLElement*>(child);
           // std::cout << "XML 元素，name=" << element->Name() << ", value=" << element->Value() << std::endl;
            if(std::string(element->Name())==std::string("Calibration"))
            {
                const XMLAttribute* attribute = element->FirstAttribute();
                while (attribute != nullptr)
                {
                   // std::cout << "\t属性 " << attribute->Name() << "=" << attribute->Value() << std::endl;
                    if(std::string(attribute->Name())==std::string("size"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>cam.width>>cam.height;
                        std::cout<<"cam.width="<<cam.width<<",cam.height="<<cam.height<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("principal_point"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>cam.cx>>cam.cy;
                        std::cout<<"cam.cx="<<cam.cx<<",cam.cy="<<cam.cy<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("focal_length"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>cam.fx>>cam.fy;
                        std::cout<<"cam.fx="<<cam.fx<<",cam.fy="<<cam.fy<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("model"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中
                        ss>>cam.model;
                        std::cout <<"cam.model="<<cam.model<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("radial_distortion"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中
                        if(cam.model==std::string("FISHEYE_4_PARAMETERS"))
                        {
                            cam.radial_distortion.resize(4,0);
                            ss>>cam.radial_distortion[0]>>cam.radial_distortion[1]>>cam.radial_distortion[2]>>cam.radial_distortion[3];
                            std::cout<<"cam.radial_distortion="<<cam.radial_distortion[0]<<" "<<cam.radial_distortion[1]<<" "<<cam.radial_distortion[2]<<" "<<cam.radial_distortion[3]<<std::endl;
                        }
                        else if(cam.model==std::string("RADIAL_6_PARAMETERS"))
                        {
                            cam.radial_distortion.resize(8,0);
                            ss>>cam.radial_distortion[0]>>cam.radial_distortion[1]>>cam.radial_distortion[4]>>cam.radial_distortion[5]>>cam.radial_distortion[6]>>cam.radial_distortion[7];
                            std::cout<<"cam.radial_distortion="<<cam.radial_distortion[0]<<" "<<cam.radial_distortion[1]<<" "<<cam.radial_distortion[2]<<" "<<cam.radial_distortion[3]<<" "<<cam.radial_distortion[4]<<" "<<cam.radial_distortion[5]<<" "<<cam.radial_distortion[6]<<" "<<cam.radial_distortion[7]<<std::endl;
                        }
                        

                        
                        
                    }
                    if(std::string(attribute->Name())==std::string("distortion_limit"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>cam.distortion_limit;
                        std::cout<<"cam.distortion_limit="<<cam.distortion_limit<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("undistortion_limit"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>cam.undistortion_limit;
                        std::cout<<"cam.undistortion_limit="<<cam.undistortion_limit<<std::endl;
                    }

                    attribute = attribute->Next();
                }
                   
            }
            child = child->NextSibling();
            element = dynamic_cast<XMLElement*>(child);
           // std::cout << "XML 元素，name=" << element->Name() << ", value=" << element->Value() << std::endl;
            if(std::string(element->Name())==std::string("Rig"))
            {
                const XMLAttribute* attribute = element->FirstAttribute();
                cam.rig=Eigen::Matrix4d::Identity();
                while (attribute != nullptr)
                {
                   // std::cout << "\t属性 " << attribute->Name() << "=" << attribute->Value() << std::endl;
                    if(std::string(attribute->Name())==std::string("translation"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>cam.rig(0,3)>>cam.rig(1,3)>>cam.rig(2,3);
                        std::cout<<"cam.translation="<<cam.rig.block(0, 3, 3, 1)<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("rowMajorRotationMat"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>cam.rig(0,0)>>cam.rig(0,1)>>cam.rig(0,2)>>cam.rig(1,0)>>cam.rig(1,1)>>cam.rig(1,2)>>cam.rig(2,0)>>cam.rig(2,1)>>cam.rig(2,2);
                        std::cout<<"cam.rotation="<<cam.rig.block(0, 0, 3, 3)<<std::endl;
                    }

                    attribute = attribute->Next();
                }
                


                std::cout<<"cam.rig="<<cam.rig<<std::endl;
                   
            }
            cameras.push_back(cam);
            


        }
		
		if(std::string(element->Name())==std::string("SFConfig"))
        {
           
            XMLNode* child = node->FirstChild();
            auto element = dynamic_cast<XMLElement*>(child);
           // std::cout << "XML 元素，name=" << element->Name() << ", value=" << element->Value() << std::endl;
            if(std::string(element->Name())==std::string("Stateinit"))
            {
                const XMLAttribute* attribute = element->FirstAttribute();
                while (attribute != nullptr)
                {
                   // std::cout << "\t属性 " << attribute->Name() << "=" << attribute->Value() << std::endl;
                    if(std::string(attribute->Name())==std::string("ombc"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.ombc[0]>>imu.ombc[1]>>imu.ombc[2];
                        std::cout<<"imu.ombc="<<imu.ombc[0]<<","<<imu.ombc[1]<<","<<imu.ombc[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("tbc"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.tbc[0]>>imu.tbc[1]>>imu.tbc[2];
                        std::cout<<"imu.tbc="<<imu.tbc[0]<<","<<imu.tbc[1]<<","<<imu.tbc[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("aBias"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.a_bias[0]>>imu.a_bias[1]>>imu.a_bias[2];
                        std::cout<<"imu.a_bias="<<imu.a_bias[0]<<","<<imu.a_bias[1]<<","<<imu.a_bias[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("wBias"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.w_bias[0]>>imu.w_bias[1]>>imu.w_bias[2];
                        std::cout<<"imu.w_bias="<<imu.w_bias[0]<<","<<imu.w_bias[1]<<","<<imu.w_bias[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("ka"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.ka[0]>>imu.ka[1]>>imu.ka[2];
                        std::cout<<"imu.ka="<<imu.ka[0]<<","<<imu.ka[1]<<","<<imu.ka[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("kg"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.kg[0]>>imu.kg[1]>>imu.kg[2];
                        std::cout<<"imu.kg="<<imu.kg[0]<<","<<imu.kg[1]<<","<<imu.kg[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("na"))
                    {   std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.na[0]>>imu.na[1]>>imu.na[2];
                        std::cout<<"imu.na="<<imu.na[0]<<","<<imu.na[1]<<","<<imu.na[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("ng"))
                    {   std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.ng[0]>>imu.ng[1]>>imu.ng[2];
                        std::cout<<"imu.ng="<<imu.ng[0]<<","<<imu.ng[1]<<","<<imu.ng[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("ombg"))
                    {   std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.ombg[0]>>imu.ombg[1]>>imu.ombg[2];
                        std::cout<<"imu.ombg="<<imu.ombg[0]<<","<<imu.ombg[1]<<","<<imu.ombg[2]<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("accelDelta"))
                    {   std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.acc_delta;
                        std::cout<<"imu.acc_delta="<<imu.acc_delta<<std::endl;
                    }
                     
                    if(std::string(attribute->Name())==std::string("delta"))
                    {   std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.delta;
                        std::cout<<"imu.delta="<<imu.delta<<std::endl;
                    }
                    attribute = attribute->Next();
                }
            }
            child = child->NextSibling();
            element = dynamic_cast<XMLElement*>(child);
            //std::cout << "XML 元素，name=" << element->Name() << ", value=" << element->Value() << std::endl;
            if(std::string(element->Name())==std::string("IMUNoise"))
            {
                const XMLAttribute* attribute = element->FirstAttribute();
                while (attribute != nullptr)
                {
                   // std::cout << "\t属性 " << attribute->Name() << "=" << attribute->Value() << std::endl;
                    if(std::string(attribute->Name())==std::string("movingAccelNoise"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.moving_acc_noise;
                        std::cout<<"imu.moving_acc_noise="<<imu.moving_acc_noise<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("movingGyroNoise"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.moving_gyro_noise;
                        std::cout<<"imu.moving_gyro_noise="<<imu.moving_gyro_noise<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("stationaryAccelNoise"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.stationary_acc_noise;
                        std::cout<<"imu.stationary_acc_noise="<<imu.stationary_acc_noise<<std::endl;
                    }
                    if(std::string(attribute->Name())==std::string("stationaryGyroNoise"))
                    {
                        std::string value=std::string(attribute->Value());
                        std::stringstream ss(value); // 将字符串初始化到stringstream中

                        ss>>imu.stationary_gyro_noise;
                        std::cout<<"imu.stationary_gyro_noise="<<imu.stationary_gyro_noise<<std::endl;
                    }
                    attribute = attribute->Next();
                }
            }
        }
	}
	if(node->ToText()) {
		auto text = dynamic_cast<XMLText*>(node);
		//std::cout << "XML 文本：" << text->Value() << std::endl;
	}
	if(node->ToComment()) {
		auto comment = dynamic_cast<XMLComment*>(node);
		//std::cout << "XML 注释：" << comment->Value() << std::endl;
	}
	if(node->ToUnknown()) {
		auto unknown = dynamic_cast<XMLUnknown*>(node);
		//std::cout << "XML 未知：" << unknown->Value() << std::endl;
	}
	if(node->ToDocument()) {
		auto document = dynamic_cast<XMLDocument*>(node);
		//std::cout << "XML 文档：" << document->ErrorName() << std::endl;
	}
	if(node->NoChildren()) {
		return;
	}
	XMLNode* child = node->FirstChild();
	while(child != nullptr) {
		TraversingCalResult(child);
		child = child->NextSibling();
	}

}
void ReadQvrCalResult::TraversingTargetConfig(tinyxml2::XMLNode* node)
{
        if(node == nullptr)
		return;
	if(node->ToDeclaration()) {
		auto declaration = dynamic_cast<XMLDeclaration*>(node);
		//std::cout << "XML 声明，value=" << declaration->Value() << std::endl;
	}
	if(node->ToElement()) {
		auto element = dynamic_cast<XMLElement*>(node);
		//std::cout << "XML 元素，name=" << element->Name() << ", value=" << element->Value() << std::endl;
        const XMLAttribute* attribute = element->FirstAttribute();
        if(std::string(element->Name())==std::string("DotPattern"))
        {
            TargetConfig target;
            while (attribute != nullptr)
            {
                if(std::string(attribute->Name())==std::string("targetType"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>target.target_type;
                    std::cout <<"target.target_type="<<target.target_type<<std::endl;
                }
                if(std::string(attribute->Name())==std::string("dotSpacing"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>target.dot_spacing;
                    std::cout <<"target.dotSpacing="<<target.dot_spacing<<std::endl;
                }
                if(std::string(attribute->Name())==std::string("dotsX"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>target.dots_x;
                    std::cout <<"target.dotsX="<<target.dots_x<<std::endl;
                }
                if(std::string(attribute->Name())==std::string("dotsY"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>target.dots_y;
                    std::cout <<"target.dotsY="<<target.dots_y<<std::endl;
                }
                if(std::string(attribute->Name())==std::string("apexDotIndexX"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>target.apex_dot_index_x;
                    std::cout <<"target.apexDotIndexX="<<target.apex_dot_index_x<<std::endl;
                }
                if(std::string(attribute->Name())==std::string("apexDotIndexY"))
                {
                    std::string value=std::string(attribute->Value());
                    std::stringstream ss(value); // 将字符串初始化到stringstream中
                    ss>>target.apex_dot_index_y;
                    std::cout <<"target.apexDotIndexY="<<target.apex_dot_index_y<<std::endl;
                }

                attribute = attribute->Next();
            }
            targets.push_back(target);
            
        }
        
            
            
	}
	if(node->ToText()) {
		auto text = dynamic_cast<XMLText*>(node);
		//std::cout << "XML 文本：" << text->Value() << std::endl;
	}
	if(node->ToComment()) {
		auto comment = dynamic_cast<XMLComment*>(node);
		//std::cout << "XML 注释：" << comment->Value() << std::endl;
	}
	if(node->ToUnknown()) {
		auto unknown = dynamic_cast<XMLUnknown*>(node);
		//std::cout << "XML 未知：" << unknown->Value() << std::endl;
	}
	if(node->ToDocument()) {
		auto document = dynamic_cast<XMLDocument*>(node);
		//std::cout << "XML 文档：" << document->ErrorName() << std::endl;
	}
	if(node->NoChildren()) {
		return;
	}
	XMLNode* child = node->FirstChild();
	while(child != nullptr) {
		TraversingTargetConfig(child);
		child = child->NextSibling();
	}

}
ReadQvrCalResult::ReadQvrCalResult(std::string cal_result_file,std::string cal_target_config_file)
{
    XMLDocument doc_cal_result;
    XMLError error= doc_cal_result.LoadFile(cal_result_file.c_str());
    if(error!=XML_SUCCESS)
    {
        std::cout<<"reading "<<cal_result_file<<" failed!"<<std::endl;
        return;
    }
    TraversingCalResult(&doc_cal_result);


    XMLDocument doc_cal_target;
    error= doc_cal_target.LoadFile(cal_target_config_file.c_str());
    if(error!=XML_SUCCESS)
    {
        std::cout<<"reading "<<cal_target_config_file<<" failed!"<<std::endl;
        return;
    }
    TraversingTargetConfig(&doc_cal_target);

}

ReadQvrCalResult::~ReadQvrCalResult()
{
}
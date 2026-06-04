use base64::Engine;
use reqwest::multipart;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct OssPolicy {
    #[serde(rename = "Policy")]
    pub policy: String,
    #[serde(rename = "OSSAccessKeyId")]
    pub access_key_id: String,
    #[serde(rename = "Signature")]
    pub signature: String,
    #[serde(rename = "Host")]
    pub host: String,
    #[serde(rename = "HostPublic")]
    pub host_public: String,
    #[serde(rename = "SecurityToken")]
    pub security_token: Option<String>,
}

pub struct OssUploader {
    client: reqwest::Client,
    policy_api_url: String,
    api_key: String,
}

impl OssUploader {
    pub fn new() -> Self {
        Self {
            client: reqwest::Client::new(),
            policy_api_url: "https://console.skyworthxr.com/cms/console/file/policeForFactory".to_string(),
            api_key: "SkyWorthxr-CalibrationFile".to_string(),
        }
    }

    pub async fn get_policy(&self) -> Result<OssPolicy, String> {
        let auth = format!(
            "Basic {}",
            base64::engine::general_purpose::STANDARD.encode("factorySupportOnly:e2328254a2c6dd074b52b4a03e7bd882")
        );

        let res = self
            .client
            .get(&self.policy_api_url)
            .header("Authorization", auth)
            .send()
            .await
            .map_err(|e| format!("获取OSS策略失败: {}", e))?;

        let data: serde_json::Value = res
            .json()
            .await
            .map_err(|e| format!("解析OSS策略失败: {}", e))?;

        if data["code"] != 0 {
            return Err(format!("OSS策略API错误: {}", data["msg"]));
        }

        let policy: OssPolicy = serde_json::from_value(data["data"].clone())
            .map_err(|e| format!("解析策略数据失败: {}", e))?;

        Ok(policy)
    }

    pub async fn upload_file(
        &self,
        file_path: &str,
        oss_path: &str,
        file_name: &str,
    ) -> Result<String, String> {
        let policy = self.get_policy().await?;
        let upload_path = format!("files/{}/{}", oss_path, file_name);

        let file_content = tokio::fs::read(file_path)
            .await
            .map_err(|e| format!("读取文件失败: {}", e))?;

        let file_part = multipart::Part::bytes(file_content)
            .file_name(file_name.to_string())
            .mime_str("application/zip")
            .map_err(|e| e.to_string())?;

        let mut form = multipart::Form::new()
            .text("name", file_name.to_string())
            .text("key", upload_path.clone())
            .text("policy", policy.policy)
            .text("OSSAccessKeyId", policy.access_key_id)
            .text("success_action_status", "200")
            .text("signature", policy.signature)
            .part("file", file_part);

        if let Some(token) = policy.security_token {
            form = form.text("x-oss-security-token", token);
        }

        let res = self
            .client
            .post(&policy.host)
            .multipart(form)
            .send()
            .await
            .map_err(|e| format!("上传OSS失败: {}", e))?;

        if res.status().is_success() {
            let url = format!("{}/{}", policy.host_public, upload_path);
            Ok(url)
        } else {
            let err_text = res.text().await.unwrap_or_default();
            Err(format!("OSS上传失败: {}", err_text))
        }
    }

    pub async fn report_to_api(
        &self,
        url: &str,
        cpu: &str,
        create_time: &str,
        brand: i32,
    ) -> Result<(), String> {
        let api_url = format!(
            "https://api-dvc.skyworthxr.com/cms/device/api/calibrationFile/create?k={}",
            self.api_key
        );

        let params = serde_json::json!({
            "url": url,
            "cpu": cpu,
            "createTime": create_time,
            "brand": brand,
        });

        let res = self
            .client
            .post(&api_url)
            .json(&params)
            .send()
            .await
            .map_err(|e| format!("API上报失败: {}", e))?;

        let data: serde_json::Value = res
            .json()
            .await
            .map_err(|e| format!("解析API响应失败: {}", e))?;

        if data["code"] == 0 {
            Ok(())
        } else {
            Err(format!("API上报错误: {}", data["msg"]))
        }
    }
}

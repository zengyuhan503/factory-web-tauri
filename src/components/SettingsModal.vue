<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import { QVR_TYPE_TEXT, hasRGBByType, hasTofByType } from '../constants/deviceTypes';

interface Props {
  visible: boolean;
  initialConfig: {
    is_rgb: boolean;
    is_tof: boolean;
    qvr_type: string;
    file_max: number;
    verify_dof: number | null;
    verify_rgb: number | null;
    verify_tof: number | null;
    enable_sfr: boolean;
    sfr_mean_avg50_min: number | null;
    sfr_cam_std_max: number | null;
    detection_rate_threshold: number | null;
  };
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'save', config: Props['initialConfig'] & { enable_sfr: boolean }): void;
}>();

const SYSTEM_PASSWORD = 'ssnwt';

const showPasswordModal = ref(false);
const passwordInput = ref('');
const passwordError = ref(false);

const form = reactive({ ...props.initialConfig });

watch(() => props.visible, (val) => {
  if (val) {
    showPasswordModal.value = true;
    passwordInput.value = '';
    passwordError.value = false;
    Object.assign(form, props.initialConfig);
  }
});

watch(() => props.initialConfig, (val) => {
  Object.assign(form, val);
}, { deep: true });

function verifyPassword() {
  if (passwordInput.value === SYSTEM_PASSWORD) {
    showPasswordModal.value = false;
    passwordError.value = false;
  } else {
    passwordError.value = true;
    passwordInput.value = '';
  }
}

function closePassword() {
  showPasswordModal.value = false;
  passwordError.value = false;
  emit('update:visible', false);
}

function onQvrTypeChange() {
  form.is_rgb = hasRGBByType(form.qvr_type);
  form.is_tof = hasTofByType(form.qvr_type);
}

function onSave() {
  emit('save', { ...form });
  emit('update:visible', false);
}

function onCancel() {
  Object.assign(form, props.initialConfig);
  emit('update:visible', false);
}
</script>

<template>
  <div>
    <!-- 密码验证弹窗 -->
    <div v-if="showPasswordModal" class="modal-overlay" @click="closePassword">
      <div class="modal-content password-modal" @click.stop>
        <h3 class="modal-title">请输入密码</h3>
        <input
          v-model="passwordInput"
          type="password"
          class="password-input"
          placeholder="请输入密码"
          @keyup.enter="verifyPassword"
        />
        <p v-if="passwordError" class="error-text">密码错误，请重新输入</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closePassword">取消</button>
          <button class="btn btn-primary" @click="verifyPassword">确定</button>
        </div>
      </div>
    </div>

    <!-- 设置弹窗 -->
    <div v-else-if="visible" class="modal-overlay" @click="onCancel">
      <div class="modal-content settings-modal" @click.stop>
        <h3 class="modal-title">系统设置</h3>

        <!-- 设备信息 -->
        <div class="form-section">
          <div class="form-section-title">设备信息</div>
          <div class="form-row">
            <div class="form-group">
              <label>设备型号</label>
              <select v-model="form.qvr_type" class="form-select" @change="onQvrTypeChange">
                <option v-for="(text, key) in QVR_TYPE_TEXT" :key="key" :value="key">
                  {{ text }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>RGB 摄像头</label>
              <div class="radio-group">
                <label class="radio-label">
                  <input v-model="form.is_rgb" type="radio" :value="true" />
                  <span>有</span>
                </label>
                <label class="radio-label">
                  <input v-model="form.is_rgb" type="radio" :value="false" />
                  <span>无</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 存储与检测 -->
        <div class="form-section">
          <div class="form-section-title">存储与检测</div>
          <div class="form-row">
            <div class="form-group">
              <label>最大文件存储数量</label>
              <input v-model.number="form.file_max" type="number" class="form-input form-input-number" min="1" />
            </div>
            <div class="form-group">
              <label>标定板检测率阈值 (%)</label>
              <input v-model.number="form.detection_rate_threshold" type="number" step="1" class="form-input form-input-number" placeholder="默认 20" />
            </div>
          </div>
        </div>

        <!-- 覆盖率阈值 -->
        <div class="form-section">
          <div class="form-section-title">覆盖率阈值</div>
          <div class="form-row">
            <div class="form-group">
              <label>6DOF 覆盖率 (%)</label>
              <input v-model.number="form.verify_dof" type="number" class="form-input form-input-number" placeholder="可选" />
            </div>
            <div class="form-group">
              <label>RGB 覆盖率 (%)</label>
              <input v-model.number="form.verify_rgb" type="number" class="form-input form-input-number" placeholder="可选" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>TOF 覆盖率 (%)</label>
              <input v-model.number="form.verify_tof" type="number" class="form-input form-input-number" placeholder="可选" />
            </div>
            <div class="form-group"></div>
          </div>
        </div>

        <!-- SFR 清晰度测试 -->
        <div class="form-section">
          <div class="form-section-title">SFR 清晰度测试</div>
          <div class="form-group">
            <label class="switch-label">
              <span>开启 SFR 清晰度测试</span>
              <input v-model="form.enable_sfr" type="checkbox" class="switch-input" />
              <span class="switch-slider" :class="{ 'is-on': form.enable_sfr }"></span>
            </label>
          </div>
          <div v-if="form.enable_sfr" class="sfr-thresholds">
            <div class="form-row">
              <div class="form-group">
                <label>SFR 清晰度均值阈值</label>
                <input v-model.number="form.sfr_mean_avg50_min" type="number" step="0.01" class="form-input form-input-number" placeholder="默认 0.18" />
              </div>
              <div class="form-group">
                <label>SFR 摄像头间标准差阈值</label>
                <input v-model.number="form.sfr_cam_std_max" type="number" step="0.01" class="form-input form-input-number" placeholder="默认 0.05" />
              </div>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="onCancel">取消</button>
          <button class="btn btn-primary" @click="onSave">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.password-modal {
  width: 320px;
}

.settings-modal {
  width: 560px;
  max-height: 85vh;
  overflow-y: auto;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 20px 0;
}

.password-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 12px;
}

.password-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.error-text {
  color: #dc2626;
  font-size: 13px;
  margin: 0 0 12px 0;
}

.form-section {
  margin-bottom: 20px;
}

.form-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e5e7eb;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
  margin-bottom: 0;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-select,
.form-input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
}

.form-input-number {
  width: auto;
  max-width: 130px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.radio-group {
  display: flex;
  gap: 20px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
}

.radio-label input {
  cursor: pointer;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: #3b82f6;
  color: #fff;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #f3f4f6;
  color: #4b5563;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

/* 开关样式 */
.switch-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.switch-input {
  display: none;
}

.switch-slider {
  position: relative;
  width: 44px;
  height: 24px;
  background: #9ca3af;
  border-radius: 12px;
  transition: background 0.25s ease, box-shadow 0.25s ease;
  flex-shrink: 0;
  display: inline-block;
}

.switch-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
}

.switch-slider.is-on {
  background: #3b82f6;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.45);
}

.switch-slider.is-on::after {
  transform: translateX(20px);
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.35);
}

.sfr-thresholds {
  margin-top: 8px;
}
</style>

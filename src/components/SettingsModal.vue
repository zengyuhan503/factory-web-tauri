<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import { QVR_TYPE_TEXT, hasRGBByType, hasTofByType } from '../constants/deviceTypes';

interface Props {
  visible: boolean;
  initialConfig: {
    is_rgb: boolean;
    qvr_type: string;
    file_max: number;
    verify_dof: number | null;
    verify_rgb: number | null;
    verify_tof: number | null;
  };
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'save', config: Props['initialConfig']): void;
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
}

function onSave() {
  emit('save', { ...form });
  emit('update:visible', false);
}

function onCancel() {
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

        <div class="form-group">
          <label>最大文件存储数量</label>
          <input v-model.number="form.file_max" type="number" class="form-input" min="1" />
        </div>

        <div class="form-group">
          <label>6DOF 覆盖率阈值 (%)</label>
          <input v-model.number="form.verify_dof" type="number" class="form-input" placeholder="可选" />
        </div>

        <div class="form-group">
          <label>RGB 覆盖率阈值 (%)</label>
          <input v-model.number="form.verify_rgb" type="number" class="form-input" placeholder="可选" />
        </div>

        <div class="form-group">
          <label>TOF 覆盖率阈值 (%)</label>
          <input v-model.number="form.verify_tof" type="number" class="form-input" placeholder="可选" />
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
  width: 420px;
  max-height: 80vh;
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

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.form-select,
.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
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
</style>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { SlotState } from '../composables/useCalibration';

interface Props {
  slot: SlotState;
  size?: 'small' | 'medium' | 'large';
}

const props = withDefaults(defineProps<Props>(), {
  size: 'small',
});

const emit = defineEmits<{
  (e: 'start', slotId: number): void;
}>();

const showDetail = ref(false);

const statusText = computed(() => {
  switch (props.slot.status) {
    case 'empty': return '未连接';
    case 'connected': return '已连接';
    case 'running': return '测试中';
    case 'success': return '通过';
    case 'error': return '未通过';
    default: return '未知';
  }
});

const resultText = computed(() => {
  switch (props.slot.result) {
    case 'pending': return '待测试';
    case 'pass': return '通过';
    case 'fail': return '未通过';
    default: return '待测试';
  }
});

const canStart = computed(() => {
  return props.slot.status === 'connected';
});

const circumference = 2 * Math.PI * 45;
const strokeOffset = computed(() => {
  return circumference - (props.slot.progress / 100) * circumference;
});

const isOperationalError = computed(() => {
  return props.slot.error?.isOperational ?? false;
});

function handleStart() {
  emit('start', props.slot.slotId);
}

function toggleDetail() {
  if (props.slot.error) {
    showDetail.value = !showDetail.value;
  }
}
</script>

<template>
  <div class="device-card" :class="[`status-${slot.status}`, `size-${size}`]">
    <!-- 头部 -->
    <div class="card-header">
      <div class="header-left">
        <span class="device-label">第{{ slot.slotId + 1 }}号设备（CPUID  {{ slot.cpuId }}）</span>
      </div>
      <span class="device-status">{{ statusText }}</span>
    </div>

    <!-- 启动按钮 -->
    <button
      class="start-btn"
      :disabled="!canStart"
      @click="handleStart"
    >
      启动测试程序
    </button>

    <!-- 进度区域 -->
    <div class="progress-area">
      <div class="progress-ring">
        <svg viewBox="0 0 100 100" class="progress-svg">
          <circle class="track" cx="50" cy="50" r="45" />
          <circle
            class="progress"
            cx="50"
            cy="50"
            r="45"
            :stroke-dasharray="circumference"
            :stroke-dashoffset="strokeOffset"
          />
        </svg>
        <span class="progress-text">{{ slot.progress }}%</span>
      </div>

      <div class="step-info" :class="[`step-status-${slot.status}`]">
        <div class="step-name">{{ slot.stepName }}</div>
        <div class="step-hint">{{ slot.hint }}</div>
      </div>
    </div>

    <!-- 错误详情（仅在错误状态显示） -->
    <div v-if="slot.error" class="error-section">
      <div
        class="error-toggle"
        :class="{ 'operational': isOperationalError }"
        @click="toggleDetail"
      >
        <span class="error-toggle-icon">{{ showDetail ? '▼' : '▶' }}</span>
        <span class="error-toggle-text">
          {{ isOperationalError ? '操作问题，可按建议排查' : '系统异常，请联系技术支持' }}
        </span>
      </div>
      <div v-if="showDetail" class="error-detail">
        <div v-if="slot.error.detail" class="error-detail-item">
          <span class="error-detail-label">详细信息</span>
          <span class="error-detail-value">{{ slot.error.detail }}</span>
        </div>
        <div class="error-detail-item">
          <span class="error-detail-label">建议方案</span>
          <span class="error-detail-value suggestion">{{ slot.error.suggestion }}</span>
        </div>
      </div>
    </div>

    <!-- 测试结果 -->
    <div class="result-area">
      <span class="result-label">测试结果</span>
      <span class="result-badge" :class="[`result-${slot.result}`]">
        {{ resultText }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.device-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.device-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

/* 大尺寸（1台设备） */
.size-large {
  padding: 40px;
  gap: 24px;
}

.size-large .device-label {
  font-size: 24px;
}

.size-large .device-status {
  font-size: 16px;
  padding: 6px 16px;
}

.size-large .start-btn {
  padding: 16px 32px;
  font-size: 18px;
}

.size-large .progress-ring {
  width: 160px;
  height: 160px;
}

.size-large .progress-text {
  font-size: 28px;
}

.size-large .step-name {
  font-size: 20px;
}

.size-large .step-hint {
  font-size: 16px;
}

.size-large .result-label {
  font-size: 18px;
}

.size-large .result-badge {
  font-size: 18px;
  padding: 6px 16px;
}

/* 中尺寸（2-4台设备） */
.size-medium {
  padding: 28px;
  gap: 20px;
}

.size-medium .device-label {
  font-size: 18px;
}

.size-medium .progress-ring {
  width: 120px;
  height: 120px;
}

.size-medium .progress-text {
  font-size: 22px;
}

.size-medium .step-name {
  font-size: 16px;
}

.size-medium .result-label,
.size-medium .result-badge {
  font-size: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.device-label {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.device-cpu-id {
  font-size: 11px;
  color: #6b7280;
  font-family: monospace;
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 4px;
}

.device-status {
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 12px;
  background: #e5e7eb;
  color: #6b7280;
}

.status-running .device-status {
  background: #dbeafe;
  color: #2563eb;
}

.status-success .device-status {
  background: #d1fae5;
  color: #059669;
}

.status-error .device-status {
  background: #fee2e2;
  color: #dc2626;
}

.start-btn {
  width: 100%;
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 500;
  color: #fff;
  background: #3b82f6;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.start-btn:hover:not(:disabled) {
  background: #2563eb;
}

.start-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.progress-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.progress-ring {
  position: relative;
  width: 100px;
  height: 100px;
}

.progress-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.track {
  fill: none;
  stroke: #e5e7eb;
  stroke-width: 8;
}

.progress {
  fill: none;
  stroke: #3b82f6;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.5s ease;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.step-info {
  text-align: center;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f9fafb;
  transition: all 0.3s ease;
}

/* 测试中 - 蓝色 */
.step-status-running {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}
.step-status-running .step-name {
  color: #1e40af;
  font-weight: 600;
}
.step-status-running .step-hint {
  color: #3b82f6;
}

/* 通过 - 绿色 */
.step-status-success {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}
.step-status-success .step-name {
  color: #065f46;
  font-weight: 600;
}
.step-status-success .step-hint {
  color: #10b981;
}

/* 未通过 - 红色 */
.step-status-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
}
.step-status-error .step-name {
  color: #991b1b;
  font-weight: 700;
}
.step-status-error .step-hint {
  color: #ef4444;
  font-weight: 500;
}

/* 已连接 - 紫色 */
.step-status-connected {
  background: #faf5ff;
  border: 1px solid #e9d5ff;
}
.step-status-connected .step-name {
  color: #6b21a8;
  font-weight: 600;
}
.step-status-connected .step-hint {
  color: #a855f7;
}

/* 未连接 - 灰色 */
.step-status-empty {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}
.step-status-empty .step-name {
  color: #6b7280;
}
.step-status-empty .step-hint {
  color: #9ca3af;
}

.step-name {
  font-size: 15px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
  line-height: 1.4;
}

.step-hint {
  font-size: 13px;
  color: #6b7280;
  min-height: 20px;
  line-height: 1.5;
}

/* 错误详情区域 */
.error-section {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.error-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #991b1b;
  transition: all 0.2s;
  user-select: none;
}

.error-toggle:hover {
  background: #fecaca;
}

.error-toggle.operational {
  background: #fef3c7;
  border-color: #fde68a;
  color: #92400e;
}

.error-toggle.operational:hover {
  background: #fde68a;
}

.error-toggle-icon {
  font-size: 10px;
  width: 14px;
  text-align: center;
}

.error-toggle-text {
  font-weight: 500;
}

.error-detail {
  margin-top: 6px;
  padding: 10px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.error-detail-label {
  font-size: 11px;
  font-weight: 600;
  color: #991b1b;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.error-detail-value {
  font-size: 12px;
  color: #7f1d1d;
  line-height: 1.5;
  word-break: break-word;
}

.error-detail-value.suggestion {
  color: #166534;
  background: #dcfce7;
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid #22c55e;
}

.result-area {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: auto;
  width: 100%;
  padding-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.result-label {
  font-size: 14px;
  color: #6b7280;
}

.result-badge {
  font-size: 14px;
  font-weight: 600;
  padding: 5px 14px;
  border-radius: 20px;
  transition: all 0.3s ease;
}

.result-pending {
  background: #f3f4f6;
  color: #9ca3af;
}

.result-pass {
  background: #d1fae5;
  color: #059669;
  border: 1px solid #6ee7b7;
}

.result-fail {
  background: #fee2e2;
  color: #dc2626;
  border: 1px solid #fca5a5;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

/* 设备卡片整体状态边框 */
.device-card.status-error {
  border: 2px solid #fecaca;
  box-shadow: 0 2px 12px rgba(220, 38, 38, 0.15);
}

.device-card.status-success {
  border: 2px solid #a7f3d0;
  box-shadow: 0 2px 12px rgba(16, 185, 129, 0.15);
}

.device-card.status-running {
  border: 2px solid #bfdbfe;
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.15);
}
</style>

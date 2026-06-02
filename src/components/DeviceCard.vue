<script setup lang="ts">
import { computed } from 'vue';
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

function handleStart() {
  emit('start', props.slot.slotId);
}
</script>

<template>
  <div class="device-card" :class="[`status-${slot.status}`, `size-${size}`]">
    <!-- 头部 -->
    <div class="card-header">
      <span class="device-label">设备 {{ slot.slotId + 1 }}</span>
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

      <div class="step-info">
        <div class="step-name">{{ slot.stepName }}</div>
        <div class="step-hint">{{ slot.hint }}</div>
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

.device-label {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
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
  gap: 12px;
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
}

.step-name {
  font-size: 15px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
}

.step-hint {
  font-size: 13px;
  color: #6b7280;
  min-height: 20px;
}

.result-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: auto;
}

.result-label {
  font-size: 14px;
  color: #6b7280;
}

.result-badge {
  font-size: 14px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 12px;
}

.result-pending {
  background: #f3f4f6;
  color: #9ca3af;
}

.result-pass {
  background: #d1fae5;
  color: #059669;
}

.result-fail {
  background: #fee2e2;
  color: #dc2626;
}
</style>

<script setup lang="ts">
import { ref } from 'vue';

interface ToastItem {
  id: number;
  message: string;
  type: 'error' | 'warning' | 'success';
  slotId: number;
}

const toasts = ref<ToastItem[]>([]);
let nextId = 0;

function show(message: string, type: ToastItem['type'] = 'error', slotId: number = -1) {
  const id = nextId++;
  toasts.value.push({ id, message, type, slotId });
  setTimeout(() => {
    remove(id);
  }, 4000);
}

function remove(id: number) {
  const index = toasts.value.findIndex(t => t.id === id);
  if (index !== -1) {
    toasts.value.splice(index, 1);
  }
}

function typeIcon(type: string) {
  switch (type) {
    case 'error':
      return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>`;
    case 'warning':
      return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    case 'success':
      return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>`;
    default:
      return '';
  }
}

function typeClass(type: string) {
  switch (type) {
    case 'error': return 'toast-error';
    case 'warning': return 'toast-warning';
    case 'success': return 'toast-success';
    default: return 'toast-error';
  }
}

defineExpose({ show });
</script>

<template>
  <div class="toast-container">
    <transition-group name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast-item"
        :class="typeClass(toast.type)"
      >
        <span class="toast-icon" v-html="typeIcon(toast.type)"></span>
        <div class="toast-content">
          <div class="toast-title">
            {{ toast.type === 'error' ? '错误' : toast.type === 'warning' ? '警告' : '成功' }}
            <span v-if="toast.slotId >= 0" class="toast-slot">槽位 {{ toast.slotId + 1 }}</span>
          </div>
          <div class="toast-message">{{ toast.message }}</div>
        </div>
        <button class="toast-close" @click="remove(toast.id)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 72px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  min-width: 280px;
  max-width: 400px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  pointer-events: all;
  border-left: 4px solid;
}

.toast-error {
  border-left-color: #f5222d;
}

.toast-warning {
  border-left-color: #faad14;
}

.toast-success {
  border-left-color: #52c41a;
}

.toast-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin-top: 2px;
}

.toast-error .toast-icon {
  color: #f5222d;
}

.toast-warning .toast-icon {
  color: #faad14;
}

.toast-success .toast-icon {
  color: #52c41a;
}

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.toast-slot {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  background: #f3f4f6;
  padding: 1px 8px;
  border-radius: 4px;
}

.toast-message {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.5;
  word-break: break-word;
}

.toast-close {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  background: none;
  color: #9ca3af;
  cursor: pointer;
  margin-top: 2px;
  transition: color 0.2s;
}

.toast-close:hover {
  color: #4b5563;
}

/* transition */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
  margin-bottom: -60px;
}
</style>

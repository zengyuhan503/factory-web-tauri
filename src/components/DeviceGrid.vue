<script setup lang="ts">
import { computed } from 'vue';
import DeviceCard from './DeviceCard.vue';
import type { SlotState } from '../composables/useCalibration';

interface Props {
  slots: SlotState[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'start', slotId: number): void;
}>();

// 只取已连接的槽位
const connectedSlots = computed(() => {
  return props.slots.filter(s => s.status !== 'empty');
});

const connectedCount = computed(() => connectedSlots.value.length);
const hasDevices = computed(() => connectedCount.value > 0);

// 根据设备数量动态计算网格布局
const gridStyle = computed(() => {
  const count = connectedCount.value;
  if (count === 0) return {};

  let cols: number;
  let rows: number;

  if (count === 1) {
    cols = 1; rows = 1;
  } else if (count === 2) {
    cols = 2; rows = 1;
  } else if (count <= 4) {
    cols = 2; rows = 2;
  } else if (count <= 6) {
    cols = 3; rows = 2;
  } else if (count <= 8) {
    cols = 3; rows = 3;
  } else {
    cols = 3; rows = 3;
  }

  return {
    gridTemplateColumns: `repeat(${cols}, 1fr)`,
    gridTemplateRows: `repeat(${rows}, 1fr)`,
  };
});

const cardSize = computed(() => {
  const count = connectedCount.value;
  if (count <= 1) return 'large';
  if (count <= 4) return 'medium';
  return 'small';
});

function handleStart(slotId: number) {
  emit('start', slotId);
}
</script>

<template>
  <div class="device-grid-wrapper">
    <!-- 无设备时显示提示 -->
    <div v-if="!hasDevices" class="no-device-tip">
      <div class="tip-icon">📱</div>
      <div class="tip-text">请连接设备</div>
      <div class="tip-sub">插入 USB 后将自动识别</div>
    </div>

    <!-- 有设备时显示宫格 -->
    <div v-else class="device-grid" :style="gridStyle">
      <DeviceCard
        v-for="slot in connectedSlots"
        :key="slot.slotId"
        :slot="slot"
        :size="cardSize"
        @start="handleStart"
      />
    </div>
  </div>
</template>

<style scoped>
.device-grid-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.device-grid {
  display: grid;
  gap: 16px;
  width: 100%;
  max-width: 1200px;
  height: 100%;
  max-height: 800px;
  padding: 16px;
}

.no-device-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #9ca3af;
}

.tip-icon {
  font-size: 48px;
  opacity: 0.6;
}

.tip-text {
  font-size: 20px;
  font-weight: 500;
  color: #6b7280;
}

.tip-sub {
  font-size: 14px;
  color: #9ca3af;
}
</style>

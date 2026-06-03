<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import DeviceGrid from './components/DeviceGrid.vue';
import SettingsModal from './components/SettingsModal.vue';
import { useCalibration } from './composables/useCalibration';
import { saveConfig } from './services/tauriCommands';

const { slots, init, startTest, cleanup, globalConfig } = useCalibration();
const showSettings = ref(false);

onMounted(() => {
  init();
});

onUnmounted(() => {
  cleanup();
});

function openSettings() {
  showSettings.value = true;
}

async function handleSaveConfig(config: typeof globalConfig) {
  Object.assign(globalConfig, config);
  try {
    await saveConfig({
      is_rgb: config.is_rgb,
      is_tof: config.is_tof,
      qvr_type: config.qvr_type,
      file_max: config.file_max,
      verify_dof: config.verify_dof,
      verify_rgb: config.verify_rgb,
      verify_tof: config.verify_tof,
      slot_count: 4,
      sfr_mean_avg50_min: config.sfr_mean_avg50_min,
      sfr_cam_std_max: config.sfr_cam_std_max,
    });
  } catch (e) {
    console.error('保存配置失败:', e);
  }
}
</script>

<template>
  <div class="app">
    <header class="app-header">
      <h1 class="app-title">标定测试</h1>
      <button class="settings-btn" @click="openSettings">
        <svg class="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
        系统设置
      </button>
    </header>
    <main class="app-main">
      <DeviceGrid :slots="slots" @start="startTest" />
    </main>
    <SettingsModal
      v-model:visible="showSettings"
      :initial-config="globalConfig"
      @save="handleSaveConfig"
    />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f0f2f5;
}

.app-header {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.settings-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 14px;
  color: #4b5563;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.settings-btn:hover {
  background: #e5e7eb;
  color: #1f2937;
}

.settings-icon {
  width: 16px;
  height: 16px;
}

.app-main {
  flex: 1;
  padding: 20px;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>

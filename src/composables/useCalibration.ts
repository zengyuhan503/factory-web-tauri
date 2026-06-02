import { ref, reactive } from 'vue';
import { listen } from '@tauri-apps/api/event';
import { getSlotStatus, startDeviceTest, loadConfig } from '../services/tauriCommands';
import type { DeviceSlot, DeviceConfig } from '../services/tauriCommands';

export interface SlotState {
  slotId: number;
  serial: string | null;
  status: 'empty' | 'connected' | 'running' | 'success' | 'error';
  progress: number;
  stepName: string;
  hint: string;
  result: 'pending' | 'pass' | 'fail';
}

// 支持最多9个槽位（九宫格）
const MAX_SLOTS = 9;

function createEmptySlot(id: number): SlotState {
  return {
    slotId: id,
    serial: null,
    status: 'empty',
    progress: 0,
    stepName: '待连接',
    hint: '',
    result: 'pending',
  };
}

const slots = reactive<SlotState[]>(
  Array.from({ length: MAX_SLOTS }, (_, i) => createEmptySlot(i))
);

const globalConfig = reactive({
  is_rgb: false,
  is_tof: false,
  qvr_type: '1',
  file_max: 200,
  verify_dof: null as number | null,
  verify_rgb: null as number | null,
  verify_tof: null as number | null,
});

let listeners: (() => void)[] = [];

export function useCalibration() {
  const isLoading = ref(false);

  async function init() {
    try {
      const config = await loadConfig();
      Object.assign(globalConfig, config);
    } catch (e) {
      console.error('加载配置失败:', e);
    }

    try {
      const status = await getSlotStatus();
      updateSlotsFromStatus(status);
    } catch (e) {
      console.error('获取槽位状态失败:', e);
    }

    const unlistenConnected = await listen('device:connected', (event) => {
      const { slot_id, serial, cpu_id } = event.payload as any;
      const slot = slots.find(s => s.slotId === slot_id);
      if (slot) {
        slot.serial = serial;
        (slot as any).cpuId = cpu_id || null;
        slot.status = 'connected';
        slot.stepName = '已连接';
        slot.hint = '点击启动按钮开始标定';
      }
    });
    listeners.push(unlistenConnected);

    const unlistenDisconnected = await listen('device:disconnected', (event) => {
      const { slot_id } = event.payload as any;
      const slot = slots.find(s => s.slotId === slot_id);
      if (slot) {
        Object.assign(slot, createEmptySlot(slot_id));
      }
    });
    listeners.push(unlistenDisconnected);

    const unlistenStep = await listen('device:step', (event) => {
      const { slot_id, step_name, progress, hint } = event.payload as any;
      const slot = slots.find(s => s.slotId === slot_id);
      if (slot) {
        slot.status = 'running';
        slot.stepName = step_name;
        slot.progress = progress;
        slot.hint = hint;
      }
    });
    listeners.push(unlistenStep);

    const unlistenComplete = await listen('device:complete', (event) => {
      const { slot_id, success, message } = event.payload as any;
      const slot = slots.find(s => s.slotId === slot_id);
      if (slot) {
        slot.status = success ? 'success' : 'error';
        slot.result = success ? 'pass' : 'fail';
        slot.stepName = success ? '完成' : '失败';
        slot.hint = message;
        slot.progress = success ? 100 : slot.progress;
      }
    });
    listeners.push(unlistenComplete);

    const unlistenError = await listen('device:error', (event) => {
      const { slot_id, message } = event.payload as any;
      const slot = slots.find(s => s.slotId === slot_id);
      if (slot) {
        slot.status = 'error';
        slot.result = 'fail';
        slot.stepName = '失败';
        slot.hint = message;
      }
    });
    listeners.push(unlistenError);
  }

  function updateSlotsFromStatus(status: DeviceSlot[]) {
    for (const s of status) {
      const slot = slots.find(sl => sl.slotId === s.slot_id);
      if (slot) {
        slot.serial = s.serial;
        slot.status = s.status;
        slot.progress = s.progress;
        slot.stepName = s.step_name;
        slot.hint = s.hint;
        slot.result = s.result === 'pass' ? 'pass' : s.result === 'fail' ? 'fail' : 'pending';
      }
    }
  }

  async function startTest(slotId: number) {
    const slot = slots.find(s => s.slotId === slotId);
    if (!slot || slot.status !== 'connected') {
      console.warn('设备未连接或正在运行');
      return;
    }

    const config: DeviceConfig = {
      is_rgb: globalConfig.is_rgb,
      is_tof: globalConfig.is_tof,
      qvr_type: globalConfig.qvr_type,
      file_max: globalConfig.file_max,
      thresholds: {
        dof: globalConfig.verify_dof,
        rgb: globalConfig.verify_rgb,
        tof: globalConfig.verify_tof,
      },
    };

    try {
      slot.status = 'running';
      slot.progress = 0;
      slot.stepName = '初始化中...';
      slot.hint = '准备开始标定';
      await startDeviceTest(slotId, config);
    } catch (e) {
      console.error('启动标定失败:', e);
      slot.status = 'error';
      slot.result = 'fail';
      slot.stepName = '失败';
      slot.hint = String(e);
    }
  }

  function cleanup() {
    listeners.forEach(unlisten => unlisten());
    listeners = [];
  }

  return {
    slots,
    globalConfig,
    isLoading,
    init,
    startTest,
    cleanup,
  };
}

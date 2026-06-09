import { invoke } from '@tauri-apps/api/tauri';
import { emit } from '@tauri-apps/api/event';

export interface DeviceConfig {
  is_rgb: boolean;
  is_tof: boolean;
  qvr_type: string;
  file_max: number;
  thresholds: {
    dof: number | null;
    rgb: number | null;
    tof: number | null;
  };
  enable_sfr: boolean;
  sfr_mean_avg50_min: number | null;
  sfr_cam_std_max: number | null;
  detection_rate_threshold: number | null;
}

export interface AppConfig {
  is_rgb: boolean;
  is_tof: boolean;
  qvr_type: string;
  file_max: number;
  verify_dof: number | null;
  verify_rgb: number | null;
  verify_tof: number | null;
  slot_count: number;
  enable_sfr: boolean;
  sfr_mean_avg50_min: number | null;
  sfr_cam_std_max: number | null;
  detection_rate_threshold: number | null;
}

export interface DeviceSlot {
  slot_id: number;
  serial: string | null;
  cpu_id: string | null;
  status: 'empty' | 'connected' | 'running' | 'success' | 'error';
  progress: number;
  step_name: string;
  hint: string;
  result: 'pending' | 'pass' | 'fail';
}

export async function startDeviceTest(slotId: number, config: DeviceConfig): Promise<void> {
  const args = { slot_id: slotId, config };
  console.log('[tauriCommands] emit start_device_test with args:', JSON.stringify(args));
  await emit('start_device_test', args);
}

export async function getSlotStatus(): Promise<DeviceSlot[]> {
  return await invoke('get_slot_status');
}

export async function getConnectedDevices(): Promise<string[]> {
  return await invoke('get_connected_devices');
}

export async function saveConfig(config: AppConfig): Promise<void> {
  await invoke('save_config', { config });
}

export async function loadConfig(): Promise<AppConfig> {
  return await invoke('load_config');
}

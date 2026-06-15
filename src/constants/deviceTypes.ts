export const QVR_TYPE_TEXT: Record<string, string> = {
  '1': 'VQ910',
  '2': 'VQ910 + RGB摄像头',
  '3': 'VQ920',
  '4': 'VQ920 + RGB摄像头',
  '5': 'VQ920 + 手势功能',
  '6': 'VQ920 + 手势功能 + RGB摄像头',
  '11': 'VQ920 + 全局曝光RGB摄像头',
  '7': 'VQ930',
  '8': 'VQ930 + RGB摄像头',
  '9': 'VQ930 + TOF摄像头',
  '10': 'VQ930 + TOF摄像头 + RGB摄像头',
};

export const RGB_DEVICE_TYPES = [2, 4, 6, 8, 10];
export const TOF_DEVICE_TYPES = [9, 10];

export function hasRGBByType(qvrType: string): boolean {
  return RGB_DEVICE_TYPES.includes(parseInt(qvrType));
}

export function hasTofByType(qvrType: string): boolean {
  return TOF_DEVICE_TYPES.includes(parseInt(qvrType));
}

export function getAndroidVersion(qvrType: string): number | null {
  const value = parseInt(qvrType);
  if ([1, 2, 3, 4, 5, 6].includes(value)) return 12;
  if ([7, 8, 9, 10].includes(value)) return 14;
  return null;
}

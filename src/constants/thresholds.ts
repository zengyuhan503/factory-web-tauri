export interface ThresholdConfig {
  dof: number | null;
  rgb: number | null;
  tof: number | null;
}

export function checkArrayThreshold(arr: number[], threshold: number | null): boolean {
  if (!arr || arr.length === 0) return true;
  const thresholdNum = parseFloat(String(threshold));
  if (isNaN(thresholdNum)) return true;
  return arr.every(value => value >= thresholdNum);
}

export function verifyAllThresholds(
  results: { dof?: number[] | null; rgb?: number[] | null; tof?: number[] | null },
  thresholds: ThresholdConfig,
): boolean {
  const dofPass = results.dof != null
    ? checkArrayThreshold(results.dof, thresholds.dof)
    : true;
  const rgbPass = results.rgb != null
    ? checkArrayThreshold(results.rgb, thresholds.rgb)
    : true;
  const tofPass = results.tof != null
    ? checkArrayThreshold(results.tof, thresholds.tof)
    : true;
  return dofPass && rgbPass && tofPass;
}

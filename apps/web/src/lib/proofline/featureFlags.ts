/** Independent deployment flag for Proofline surfaces. Defaults on for continuity. */
export function isProoflineEnabled(): boolean {
  const raw = (import.meta.env.VITE_PROOFLINE_ENABLED ?? 'true').toString().trim().toLowerCase()
  return raw !== 'false' && raw !== '0'
}

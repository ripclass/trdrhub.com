/**
 * Throttle utility for frontend API calls
 */

export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let lastCallTime = 0;

  return function (this: any, ...args: Parameters<T>) {
    const now = Date.now();
    const timeSinceLastCall = now - lastCallTime;

    if (timeSinceLastCall >= wait) {
      lastCallTime = now;
      func.apply(this, args);
    } else {
      if (timeout) {
        clearTimeout(timeout);
      }
      timeout = setTimeout(() => {
        lastCallTime = Date.now();
        func.apply(this, args);
      }, wait - timeSinceLastCall);
    }
  };
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => {
      func.apply(this, args);
    }, wait);
  };
}


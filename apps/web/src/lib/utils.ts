import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility function to merge Tailwind CSS classes.
 * Combines clsx and tailwind-merge for optimal class merging.
 * 
 * @example
 * cn('px-2 py-1', 'bg-red-500', isActive && 'bg-blue-500')
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Ensure default export for compatibility
export default cn

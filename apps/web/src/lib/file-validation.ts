/**
 * Content-based file validation using magic bytes (file signatures).
 * This provides security by validating actual file content, not just extensions.
 */

export interface FileTypeInfo {
  mimeType: string;
  extension: string;
  description: string;
}

export const ALLOWED_FILE_TYPES: FileTypeInfo[] = [
  { mimeType: 'application/pdf', extension: '.pdf', description: 'PDF Document' },
  { mimeType: 'image/jpeg', extension: '.jpg', description: 'JPEG Image' },
  { mimeType: 'image/jpeg', extension: '.jpeg', description: 'JPEG Image' },
  { mimeType: 'image/png', extension: '.png', description: 'PNG Image' },
  { mimeType: 'image/tiff', extension: '.tiff', description: 'TIFF Image' },
  { mimeType: 'image/tiff', extension: '.tif', description: 'TIFF Image' },
];

// Magic bytes (file signatures) for different file types
const FILE_SIGNATURES: Record<string, number[][]> = {
  'application/pdf': [
    [0x25, 0x50, 0x44, 0x46], // %PDF
  ],
  'image/jpeg': [
    [0xFF, 0xD8, 0xFF], // JPEG start
  ],
  'image/png': [
    [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A], // PNG signature
  ],
  'image/tiff': [
    [0x49, 0x49, 0x2A, 0x00], // TIFF (little-endian) - II*
    [0x4D, 0x4D, 0x00, 0x2A], // TIFF (big-endian) - MM*
  ],
};

/**
 * Read file header bytes (first 8 bytes) to detect file type.
 */
async function readFileHeader(file: File, byteCount: number = 8): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target?.result instanceof ArrayBuffer) {
        const bytes = new Uint8Array(e.target.result.slice(0, byteCount));
        resolve(bytes);
      } else {
        reject(new Error('Failed to read file header'));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsArrayBuffer(file.slice(0, byteCount));
  });
}

/**
 * Check if file header matches a signature pattern.
 */
function matchesSignature(bytes: Uint8Array, signature: number[]): boolean {
  if (bytes.length < signature.length) {
    return false;
  }
  for (let i = 0; i < signature.length; i++) {
    if (bytes[i] !== signature[i]) {
      return false;
    }
  }
  return true;
}

/**
 * Detect file type from content (magic bytes).
 */
export async function detectFileTypeFromContent(file: File): Promise<string | null> {
  try {
    const headerBytes = await readFileHeader(file, 8);
    
    // Check each file type signature
    for (const [mimeType, signatures] of Object.entries(FILE_SIGNATURES)) {
      for (const signature of signatures) {
        if (matchesSignature(headerBytes, signature)) {
          return mimeType;
        }
      }
    }
    
    return null;
  } catch (error) {
    console.error('Error detecting file type:', error);
    return null;
  }
}

/**
 * Validate file content matches declared type.
 */
export async function validateFileContent(file: File): Promise<{
  valid: boolean;
  detectedType: string | null;
  declaredType: string | null;
  error?: string;
}> {
  const declaredType = file.type || getMimeTypeFromExtension(file.name);
  const detectedType = await detectFileTypeFromContent(file);
  
  // If we couldn't detect type, but file has a valid declared type, allow it
  // (Some files might be valid but we can't detect them)
  if (!detectedType) {
    if (declaredType && ALLOWED_FILE_TYPES.some(t => t.mimeType === declaredType)) {
      return {
        valid: true,
        detectedType: null,
        declaredType,
      };
    }
    return {
      valid: false,
      detectedType: null,
      declaredType,
      error: 'File type could not be detected and is not in allowed types',
    };
  }
  
  // Check if detected type is allowed
  const isAllowed = ALLOWED_FILE_TYPES.some(t => t.mimeType === detectedType);
  if (!isAllowed) {
    return {
      valid: false,
      detectedType,
      declaredType,
      error: `Detected file type ${detectedType} is not allowed`,
    };
  }
  
  // Check if detected type matches declared type (warning if mismatch)
  if (declaredType && declaredType !== detectedType) {
    // Check if they're compatible (e.g., .jpg vs .jpeg)
    const declaredInfo = ALLOWED_FILE_TYPES.find(t => t.mimeType === declaredType);
    const detectedInfo = ALLOWED_FILE_TYPES.find(t => t.mimeType === detectedType);
    
    if (declaredInfo?.mimeType !== detectedInfo?.mimeType) {
      return {
        valid: false,
        detectedType,
        declaredType,
        error: `File type mismatch: declared as ${declaredType} but detected as ${detectedType}`,
      };
    }
  }
  
  return {
    valid: true,
    detectedType,
    declaredType,
  };
}

/**
 * Get MIME type from file extension (fallback).
 */
function getMimeTypeFromExtension(filename: string): string | null {
  const ext = filename.toLowerCase().split('.').pop();
  if (!ext) return null;
  
  const fileType = ALLOWED_FILE_TYPES.find(
    t => t.extension.toLowerCase() === `.${ext}`
  );
  return fileType?.mimeType || null;
}

/**
 * Validate multiple files for content-based security.
 */
export async function validateFilesContent(files: File[]): Promise<{
  valid: boolean;
  errors: Array<{ filename: string; error: string }>;
  results: Array<{ filename: string; valid: boolean; detectedType: string | null }>;
}> {
  const errors: Array<{ filename: string; error: string }> = [];
  const results: Array<{ filename: string; valid: boolean; detectedType: string | null }> = [];
  
  for (const file of files) {
    const validation = await validateFileContent(file);
    results.push({
      filename: file.name,
      valid: validation.valid,
      detectedType: validation.detectedType,
    });
    
    if (!validation.valid) {
      errors.push({
        filename: file.name,
        error: validation.error || 'Invalid file content',
      });
    }
  }
  
  return {
    valid: errors.length === 0,
    errors,
    results,
  };
}


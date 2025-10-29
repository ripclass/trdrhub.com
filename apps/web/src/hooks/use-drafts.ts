import { useState, useCallback } from 'react';
import { nanoid } from 'nanoid';

// File metadata interface (no File objects)
export interface FileMeta {
  name: string;
  size: number;
  type?: string;
  tag?: string; // document type
}

// Extended file data for session storage
export interface FileData {
  id: string;
  name: string;
  size: number;
  type: string;
  documentType?: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;
  dataUrl?: string; // base64 encoded file data for session storage
}

// Draft data structure for localStorage
export interface DraftData {
  id: string;
  type: 'export';
  lcNumber?: string;
  issueDate?: string;
  notes?: string;
  filesMeta?: FileMeta[];
  updatedAt: string;
  sessionId?: string; // to link with session storage
}

export interface DraftError {
  message: string;
  type: 'storage' | 'validation' | 'unknown';
}

// localStorage key for drafts
const DRAFTS_STORAGE_KEY = 'trdr_drafts';
const SESSION_FILES_PREFIX = 'trdr_files_';

// Generate a session ID for this browser session
const getSessionId = () => {
  let sessionId = sessionStorage.getItem('trdr_session_id');
  if (!sessionId) {
    sessionId = nanoid();
    sessionStorage.setItem('trdr_session_id', sessionId);
  }
  return sessionId;
};

// Helper functions for localStorage operations
const getDraftsFromStorage = (): DraftData[] => {
  try {
    const stored = localStorage.getItem(DRAFTS_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error('Failed to parse drafts from localStorage:', error);
    return [];
  }
};

const saveDraftsToStorage = (drafts: DraftData[]): void => {
  try {
    localStorage.setItem(DRAFTS_STORAGE_KEY, JSON.stringify(drafts));
  } catch (error) {
    console.error('Failed to save drafts to localStorage:', error);
    throw new Error('Failed to save draft to storage');
  }
};

// Legacy interfaces for backward compatibility
export interface DraftFile {
  id: string;
  name: string;
  size: number;
  type: string;
  documentType?: string;
  url?: string;
  file?: File;
}

export interface CreateDraftRequest {
  draft_type: 'exporter' | 'importer_draft' | 'importer_supplier';
  lc_number?: string;
  issue_date?: string;
  notes?: string;
  files: DraftFile[];
}

export interface UpdateDraftRequest {
  lc_number?: string;
  issue_date?: string;
  notes?: string;
  files?: DraftFile[];
}

export interface Draft {
  draft_id: string;
  user_id: string;
  draft_type: 'exporter' | 'importer_draft' | 'importer_supplier';
  lc_number?: string;
  issue_date?: string;
  notes?: string;
  uploaded_docs: DraftFile[];
  status: 'incomplete' | 'submitted';
  created_at: string;
  updated_at: string;
}

// New localStorage-based draft functions
const createLocalDraft = (data: Omit<DraftData, 'id' | 'updatedAt' | 'sessionId'>): DraftData => {
  const draft: DraftData = {
    ...data,
    id: nanoid(),
    sessionId: getSessionId(),
    updatedAt: new Date().toISOString(),
  };

  const drafts = getDraftsFromStorage();
  drafts.push(draft);
  saveDraftsToStorage(drafts);

  return draft;
};

const getLocalDraft = (draftId: string): DraftData | null => {
  const drafts = getDraftsFromStorage();
  return drafts.find(d => d.id === draftId) || null;
};

const updateLocalDraft = (draftId: string, updates: Partial<Omit<DraftData, 'id' | 'updatedAt' | 'sessionId'>>): DraftData => {
  const drafts = getDraftsFromStorage();
  const draftIndex = drafts.findIndex(d => d.id === draftId);

  if (draftIndex === -1) {
    throw new Error('Draft not found');
  }

  const updatedDraft: DraftData = {
    ...drafts[draftIndex],
    ...updates,
    sessionId: getSessionId(), // Update session ID to current session
    updatedAt: new Date().toISOString(),
  };

  drafts[draftIndex] = updatedDraft;
  saveDraftsToStorage(drafts);

  return updatedDraft;
};

const deleteLocalDraft = (draftId: string): void => {
  const drafts = getDraftsFromStorage();
  const draft = drafts.find(d => d.id === draftId);

  // Clean up associated session storage
  if (draft?.sessionId) {
    sessionStorage.removeItem(SESSION_FILES_PREFIX + draft.sessionId);
  }

  const updatedDrafts = drafts.filter(d => d.id !== draftId);
  saveDraftsToStorage(updatedDrafts);
};

const listLocalDrafts = (): DraftData[] => {
  const drafts = getDraftsFromStorage();
  return drafts.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
};

// Legacy mock functions for backward compatibility with importer pages
let mockDrafts: Draft[] = [];
let draftIdCounter = 1;

const generateMockDraftId = () => `draft_${Date.now()}_${draftIdCounter++}`;

const mockCreateDraft = async (request: CreateDraftRequest): Promise<Draft> => {
  await new Promise(resolve => setTimeout(resolve, 500));

  const draft: Draft = {
    draft_id: generateMockDraftId(),
    user_id: 'demo_user',
    draft_type: request.draft_type,
    lc_number: request.lc_number,
    issue_date: request.issue_date,
    notes: request.notes,
    uploaded_docs: request.files,
    status: 'incomplete',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  mockDrafts.push(draft);
  return draft;
};

const mockGetDraft = async (draftId: string): Promise<Draft> => {
  await new Promise(resolve => setTimeout(resolve, 300));

  const draft = mockDrafts.find(d => d.draft_id === draftId);
  if (!draft) {
    throw new Error('Draft not found');
  }
  return draft;
};

const mockUpdateDraft = async (draftId: string, request: UpdateDraftRequest): Promise<Draft> => {
  await new Promise(resolve => setTimeout(resolve, 500));

  const draftIndex = mockDrafts.findIndex(d => d.draft_id === draftId);
  if (draftIndex === -1) {
    throw new Error('Draft not found');
  }

  const updatedDraft: Draft = {
    ...mockDrafts[draftIndex],
    lc_number: request.lc_number ?? mockDrafts[draftIndex].lc_number,
    issue_date: request.issue_date ?? mockDrafts[draftIndex].issue_date,
    notes: request.notes ?? mockDrafts[draftIndex].notes,
    uploaded_docs: request.files ?? mockDrafts[draftIndex].uploaded_docs,
    updated_at: new Date().toISOString(),
  };

  mockDrafts[draftIndex] = updatedDraft;
  return updatedDraft;
};

const mockDeleteDraft = async (draftId: string): Promise<void> => {
  await new Promise(resolve => setTimeout(resolve, 300));

  const draftIndex = mockDrafts.findIndex(d => d.draft_id === draftId);
  if (draftIndex === -1) {
    throw new Error('Draft not found');
  }

  mockDrafts.splice(draftIndex, 1);
};

const mockListDrafts = async (draftType?: string): Promise<Draft[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));

  let drafts = mockDrafts.filter(d => d.status === 'incomplete');

  if (draftType) {
    drafts = drafts.filter(d => d.draft_type === draftType);
  }

  return drafts.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
};

// Hook for managing drafts
export const useDrafts = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<DraftError | null>(null);

  // Session storage helpers for files
  const saveFilesToSession = useCallback((files: FileData[], sessionId: string): void => {
    try {
      sessionStorage.setItem(SESSION_FILES_PREFIX + sessionId, JSON.stringify(files));
    } catch (error) {
      console.warn('Failed to save files to session storage:', error);
    }
  }, []);

  const getFilesFromSession = useCallback((sessionId: string): FileData[] => {
    try {
      const stored = sessionStorage.getItem(SESSION_FILES_PREFIX + sessionId);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.warn('Failed to load files from session storage:', error);
      return [];
    }
  }, []);

  // New localStorage-based functions for export drafts
  const saveDraft = useCallback((data: {
    id?: string;
    lcNumber?: string;
    issueDate?: string;
    notes?: string;
    filesMeta?: FileMeta[];
    filesData?: FileData[]; // Include file data for session storage
  }): DraftData => {
    try {
      const sessionId = getSessionId();

      // Save files to session storage if provided
      if (data.filesData) {
        saveFilesToSession(data.filesData, sessionId);
      }

      if (data.id) {
        // Update existing draft
        return updateLocalDraft(data.id, {
          type: 'export',
          lcNumber: data.lcNumber,
          issueDate: data.issueDate,
          notes: data.notes,
          filesMeta: data.filesMeta,
        });
      } else {
        // Create new draft
        return createLocalDraft({
          type: 'export',
          lcNumber: data.lcNumber,
          issueDate: data.issueDate,
          notes: data.notes,
          filesMeta: data.filesMeta,
        });
      }
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'storage',
        message: err.message || 'Failed to save draft',
      };
      setError(draftError);
      throw draftError;
    }
  }, [saveFilesToSession]);

  const loadDraft = useCallback((draftId: string): { draft: DraftData; filesData: FileData[] } | null => {
    try {
      const draft = getLocalDraft(draftId);
      if (!draft) return null;

      // Try to load associated files from session storage
      const currentSessionId = getSessionId();
      let filesData: FileData[] = [];

      if (draft.sessionId === currentSessionId) {
        // Same session - files should be available
        filesData = getFilesFromSession(draft.sessionId);
      }

      return { draft, filesData };
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'storage',
        message: err.message || 'Failed to load draft',
      };
      setError(draftError);
      throw draftError;
    }
  }, [getFilesFromSession]);

  const removeDraft = useCallback((draftId: string): void => {
    try {
      deleteLocalDraft(draftId);
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'storage',
        message: err.message || 'Failed to delete draft',
      };
      setError(draftError);
      throw draftError;
    }
  }, []);

  const getAllDrafts = useCallback((): DraftData[] => {
    try {
      return listLocalDrafts();
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'storage',
        message: err.message || 'Failed to list drafts',
      };
      setError(draftError);
      throw draftError;
    }
  }, []);

  // Legacy functions for backward compatibility with importer pages
  const createDraft = useCallback(async (request: CreateDraftRequest): Promise<Draft> => {
    setIsLoading(true);
    setError(null);

    try {
      return await mockCreateDraft(request);
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'unknown',
        message: err.message || 'Failed to create draft',
      };
      setError(draftError);
      throw draftError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getDraft = useCallback(async (draftId: string): Promise<Draft> => {
    setIsLoading(true);
    setError(null);

    try {
      return await mockGetDraft(draftId);
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'unknown',
        message: err.message || 'Failed to fetch draft',
      };
      setError(draftError);
      throw draftError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateDraft = useCallback(async (draftId: string, request: UpdateDraftRequest): Promise<Draft> => {
    setIsLoading(true);
    setError(null);

    try {
      return await mockUpdateDraft(draftId, request);
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'unknown',
        message: err.message || 'Failed to update draft',
      };
      setError(draftError);
      throw draftError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteDraft = useCallback(async (draftId: string): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await mockDeleteDraft(draftId);
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'unknown',
        message: err.message || 'Failed to delete draft',
      };
      setError(draftError);
      throw draftError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const listDrafts = useCallback(async (draftType?: string): Promise<Draft[]> => {
    setIsLoading(true);
    setError(null);

    try {
      return await mockListDrafts(draftType);
    } catch (err: any) {
      const draftError: DraftError = {
        type: 'unknown',
        message: err.message || 'Failed to list drafts',
      };
      setError(draftError);
      throw draftError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const markDraftSubmitted = useCallback(async (draftId: string): Promise<void> => {
    try {
      const draft = mockDrafts.find(d => d.draft_id === draftId);
      if (draft) {
        draft.status = 'submitted';
        draft.updated_at = new Date().toISOString();
      }
    } catch (err) {
      console.log('Failed to mark draft as submitted:', err);
    }
  }, []);

  return {
    // New localStorage-based functions for export drafts
    saveDraft,
    loadDraft,
    removeDraft,
    getAllDrafts,
    saveFilesToSession,
    getFilesFromSession,
    // Legacy functions for backward compatibility
    createDraft,
    getDraft,
    updateDraft,
    deleteDraft,
    listDrafts,
    markDraftSubmitted,
    isLoading,
    error,
    clearError: () => setError(null),
  };
};
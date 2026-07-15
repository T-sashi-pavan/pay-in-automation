import axios from 'axios';
import type { UploadHistory, ExtractedRecordsResponse, CommissionRule, MasterListItem, EditableRuleField, EditableSlabField } from '../types';

// In production this must be set as a build-time env var (VITE_API_BASE_URL)
// pointing at the deployed backend, e.g. "https://payin-backend.onrender.com/api" —
// Vite only reads VITE_-prefixed vars, and bakes them in at build time, not runtime.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface FilterOption {
  value: string;
  count: number;
}

export type FilterOptionsMap = Record<string, FilterOption[]>;

export const api = {
  getUploads: async (): Promise<UploadHistory[]> => {
    const response = await apiClient.get<UploadHistory[]>('/uploads');
    return response.data;
  },

  uploadFile: async (file: File): Promise<{ upload_id: number; filename: string; total_records: number }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getExtractedRecords: async (
    id: number,
    params: {
      page?: number;
      limit?: number;
      search?: string;
      [key: string]: any;
    } = {}
  ): Promise<ExtractedRecordsResponse> => {
    const response = await apiClient.get<ExtractedRecordsResponse>(`/uploads/${id}`, {
      params,
    });
    return response.data;
  },

  deleteUpload: async (id: number): Promise<{ message: string }> => {
    const response = await apiClient.delete<{ message: string }>(`/uploads/${id}`);
    return response.data;
  },

  renameUpload: async (id: number, filename: string): Promise<{ id: number; filename: string }> => {
    const response = await apiClient.patch<{ id: number; filename: string }>(`/uploads/${id}/rename`, { filename });
    return response.data;
  },

  /** Returns distinct filter options WITH per-value row counts from the entire DB or isolated to an upload */
  getDistinctFilters: async (uploadId?: number): Promise<FilterOptionsMap> => {
    const response = await apiClient.get<FilterOptionsMap>('/filters', {
      params: uploadId !== undefined ? { upload_id: uploadId } : {},
    });
    return response.data;
  },

  /** POST /search — cross-file global search with multi-select filters */
  searchRules: async (payload: {
    filters: Record<string, string[]>;
    search?: string;
    effective_date_from?: string;
    effective_date_to?: string;
    page?: number;
    limit?: number;
  }): Promise<{
    metadata: { total: number; page: number; limit: number; pages: number };
    records: any[];
  }> => {
    const response = await apiClient.post('/search', payload);
    return response.data;
  },

  /** PATCH a single field on a commission rule. Returns the updated rule (same shape as the GET/search endpoints). */
  updateCommissionRuleField: async (
    id: number,
    field: EditableRuleField,
    value: unknown,
    editedBy?: string
  ): Promise<CommissionRule> => {
    const response = await apiClient.patch<CommissionRule>(`/commission-rule/${id}`, {
      field,
      value,
      edited_by: editedBy,
    });
    return response.data;
  },

  /** PATCH a single field on a slab tier. Returns the parent rule (same shape as the GET/search endpoints). */
  updateSlabDetailField: async (
    id: number,
    field: EditableSlabField,
    value: unknown,
    editedBy?: string
  ): Promise<CommissionRule> => {
    const response = await apiClient.patch<CommissionRule>(`/slab-detail/${id}`, {
      field,
      value,
      edited_by: editedBy,
    });
    return response.data;
  },

  /** Aggregated read-only counts for the Dashboard overview page. */
  getDashboardSummary: async (): Promise<{
    total_uploads: number;
    total_rules: number;
    slab_rules: number;
    non_slab_rules: number;
    valid_rules: number;
    warning_rules: number;
    insurer_breakdown: { insurer: string; count: number }[];
    recent_uploads: {
      id: number;
      filename: string;
      company: string | null;
      status: string;
      total_records: number;
      uploaded_at: string | null;
    }[];
  }> => {
    const response = await apiClient.get('/dashboard-summary');
    return response.data;
  },

  /** Read-only lookup dictionary for edit-popover autosuggest (not a hard enum). */
  getMasterList: async (kind: 'states' | 'products' | 'vehicle-types' | 'policy-types'): Promise<MasterListItem[]> => {
    const response = await apiClient.get<MasterListItem[]>(`/master/${kind}`);
    return response.data;
  },

  /**
   * Builds the download URL for GET /uploads/{id}/export.
   */
  getExportUrl: (id: number, params: Record<string, any> = {}): string => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.set(key, String(val));
      }
    });
    const qs = query.toString();
    return `${API_BASE_URL}/uploads/${id}/export${qs ? `?${qs}` : ''}`;
  },

  getExportJsonUrl: (id: number, params: Record<string, any> = {}): string => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.set(key, String(val));
      }
    });
    const qs = query.toString();
    return `${API_BASE_URL}/uploads/${id}/export/json${qs ? `?${qs}` : ''}`;
  },

  /**
   * Downloads a file via fetch() + Blob, triggering a browser save dialog.
   * Returns a promise so the caller can show/hide a loading toast.
   */
  downloadFile: async (url: string, suggestedFilename: string): Promise<void> => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objUrl;
    a.download = suggestedFilename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objUrl);
  },

  getAutomationUploads: async (): Promise<any[]> => {
    const response = await apiClient.get('/automation/uploads');
    return response.data;
  },

  getValidRows: async (id: number): Promise<any> => {
    const response = await apiClient.get(`/automation/uploads/${id}/valid-rows`);
    return response.data;
  },

  getUniqueValues: async (id: number): Promise<any> => {
    const response = await apiClient.get(`/automation/uploads/${id}/unique-values`);
    return response.data;
  },

  runAutomation: async (payload: { upload_id: number; frontend_url: string }): Promise<any> => {
    const response = await apiClient.post('/automation/run', payload);
    return response.data;
  },
};

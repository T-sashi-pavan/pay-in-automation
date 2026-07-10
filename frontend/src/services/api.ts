import axios from 'axios';
import type { UploadHistory, ExtractedRecordsResponse, CommissionRule, MasterListItem, EditableRuleField, EditableSlabField } from '../types';

// In production this must be set as a build-time env var (VITE_API_BASE_URL)
// pointing at the deployed backend, e.g. "https://payin-backend.onrender.com/api" —
// Vite only reads VITE_-prefixed vars, and bakes them in at build time, not runtime.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

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

  /** Export all matching search results as JSON file (downloaded in browser) */
  exportAsJSON: (records: any[], filename = 'commission_rules_export') => {
    const jsonStr = JSON.stringify(records, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.json`;
    link.click();
    URL.revokeObjectURL(url);
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

  /** Read-only lookup dictionary for edit-popover autosuggest (not a hard enum). */
  getMasterList: async (kind: 'states' | 'products' | 'vehicle-types' | 'policy-types'): Promise<MasterListItem[]> => {
    const response = await apiClient.get<MasterListItem[]>(`/master/${kind}`);
    return response.data;
  },

  /** Export all matching search results as CSV file (downloaded in browser) */
  exportAsCSV: (records: any[], filename = 'commission_rules_export') => {
    if (!records.length) return;
    const flatRecords = records.map((r) => {
      const { slabs, warnings, raw_json, ...rest } = r;
      return {
        ...rest,
        slab_count: slabs?.length ?? 0,
        has_warnings: (warnings?.length ?? 0) > 0,
      };
    });
    const headers = Object.keys(flatRecords[0]);
    const csvRows = [
      headers.join(','),
      ...flatRecords.map((row) =>
        headers.map((h) => {
          const val = row[h];
          if (val === null || val === undefined) return '';
          const str = String(val).replace(/"/g, '""');
          return str.includes(',') || str.includes('"') || str.includes('\n')
            ? `"${str}"`
            : str;
        }).join(',')
      ),
    ];
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  },
};

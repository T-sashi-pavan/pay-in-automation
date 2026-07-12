import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { FilterOptionsMap } from '../services/api';
import type { FilterOption } from '../components/MultiSelectFilter';
import { MultiSelectFilter } from '../components/MultiSelectFilter';
import { HistoryDrawer } from '../components/HistoryDrawer';
import type { CommissionRule, UploadHistory, EditableRuleField, EditableSlabField } from '../types';
import { ExpandedRuleDetails } from '../components/ExpandedRuleDetails';
import { createNonSlabColumns, createSlabColumns } from '../tableColumns/commissionRuleColumns';
import { useEditRuleField } from '../hooks/useEditRuleField';
import { useTheme } from '../contexts/ThemeContext';
import { useSidebar } from '../contexts/SidebarContext';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type VisibilityState,
} from '@tanstack/react-table';
import {
  Search,
  Filter,
  Download,
  ChevronRight,
  ChevronDown,
  ChevronLeft,
  RefreshCw,
  FileJson,
  History,
  Maximize2,
  Minimize2,
  Eye,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
  FileSpreadsheet,
  UploadCloud,
  Menu,
  Moon,
  Sun,
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

// The real filters object (owned by App.tsx) is a flat, dynamically-keyed
// string map (lob, file_type, commission_type, validation_status, etc.) —
// not the narrower named-property shape this used to declare, which never
// actually matched what App.tsx passes down or what this file reads via
// `filters[key]`/`filters.commission_type` elsewhere.
type FiltersState = Record<string, string>;

interface DashboardProps {
  // Table data
  records: CommissionRule[];
  totalRecords: number;
  currentPage: number;
  totalPages: number;
  isLoading: boolean;
  filename: string;
  company: string;
  onPageChange: (page: number) => void;
  onRefresh?: () => void;
  filters: FiltersState;
  setFilters: React.Dispatch<React.SetStateAction<FiltersState>>;
  // Upload / History (moved here from DashboardLayout)
  uploads: UploadHistory[];
  selectedUploadId: number | null;
  onSelectUpload: (id: number) => void;
  onDeleteUpload: (id: number) => void;
  isUploadsLoading: boolean;
  onUploadFile: (file: File) => void;
  isUploading: boolean;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const STATIC_VEHICLE_AGE: FilterOption[] = [
  { value: 'Upto 5 yrs', count: 0 },
  { value: '6 - 15 yrs', count: 0 },
  { value: '> 15 yrs', count: 0 },
];
const DEFAULT_VISIBILITY: VisibilityState = {
  remarks: false,
};

const getSavedVisibility = (): VisibilityState => {
  try {
    const saved = localStorage.getItem('dashboard_col_visibility');
    return saved ? JSON.parse(saved) : DEFAULT_VISIBILITY;
  } catch { return DEFAULT_VISIBILITY; }
};

// ─── Component ───────────────────────────────────────────────────────────────

export const Dashboard: React.FC<DashboardProps> = ({
  records,
  totalRecords,
  currentPage,
  totalPages,
  isLoading,
  filename,
  company,
  onPageChange,
  onRefresh,
  filters,
  setFilters,
  uploads,
  selectedUploadId,
  onSelectUpload,
  onDeleteUpload,
  isUploadsLoading,
  onUploadFile,
  isUploading,
}) => {
  const { theme, toggleTheme } = useTheme();
  const { openMobileSidebar } = useSidebar();

  const [searchInput, setSearchInput] = useState(filters.search);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const toggleRowExpanded = (rowId: string) => {
    setExpandedRows(prev => ({ ...prev, [rowId]: !prev[rowId] }));
  };

  // Drawer states
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Columns/Export are now accordion sections inside the single "More
  // Options" dropdown, rather than two separate floating dropdowns.
  const [isColsOpen, setIsColsOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const closeMore = () => { setIsMoreOpen(false); setIsColsOpen(false); setIsExportOpen(false); };

  // Upload Grid — permanent toolbar trigger (file input lives here now, not in HistoryDrawer)
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const handleUploadInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      onUploadFile(e.target.files[0]);
      e.target.value = '';
    }
  };

  // Drag-and-drop onto the upload banner
  const [isDragging, setIsDragging] = useState(false);
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onUploadFile(file);
  };

  // TanStack Table state
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(getSavedVisibility);

  // Persist column visibility
  useEffect(() => {
    try { localStorage.setItem('dashboard_col_visibility', JSON.stringify(columnVisibility)); } catch {}
  }, [columnVisibility]);

  // Close the "More Options" dropdown (and its Columns/Export accordions) on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) closeMore();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Escape exits fullscreen
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape' && isFullscreen) setIsFullscreen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isFullscreen]);

  // Sync search input
  useEffect(() => { setSearchInput(filters.search); }, [filters.search]);

  // Fetch distinct filter options from DB, isolated to current upload_id
  const { data: filterOptions = {} } = useQuery<FilterOptionsMap>({
    queryKey: ['filterOptions', selectedUploadId],
    queryFn: () => api.getDistinctFilters(selectedUploadId ?? undefined),
    enabled: selectedUploadId !== null,
    staleTime: 60_000,
  });

  // Reference dictionaries for edit-popover autosuggest (not hard enums — fields stay free-text)
  const { data: stateSuggestions } = useQuery({ queryKey: ['masterList', 'states'], queryFn: () => api.getMasterList('states'), staleTime: Infinity });
  const { data: productSuggestions } = useQuery({ queryKey: ['masterList', 'products'], queryFn: () => api.getMasterList('products'), staleTime: Infinity });

  const editRuleField = useEditRuleField();
  const handleEditRule = (ruleId: number, field: EditableRuleField, value: string) => {
    editRuleField.mutate({ ruleId, target: { kind: 'rule', field }, value });
  };
  const handleEditSlab = (slabId: number, field: EditableSlabField, value: string) => {
    const parentRuleId = records.find(r => r.slabs?.some(s => s.id === slabId))?.id ?? slabId;
    editRuleField.mutate({ ruleId: parentRuleId, target: { kind: 'slab', slabId, field }, value });
  };

  // ─── Handlers ──────────────────────────────────────────────────────────────

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFilters(prev => ({ ...prev, search: searchInput }));
  };

  const resetFilters = () => {
    setSearchInput('');
    const emptyFilters: Record<string, string> = {};
    Object.keys(filters).forEach(k => {
      emptyFilters[k] = k === 'commission_type' ? filters.commission_type : '';
    });
    setFilters(emptyFilters);
  };

  const activeFilterCount = Object.entries(filters)
    .filter(([key, val]) => val && key !== 'search' && key !== 'commission_type')
    .length;

  const handleExportCSV = () => {
    api.exportAsCSV(records, `Rules_${company || 'Export'}`);
  };

  const handleExportJSON = () => {
    api.exportAsJSON(records, `Rules_${company || 'Export'}`);
  };

  const getOpts = (key: string): FilterOption[] => {
    const raw = (filterOptions[key] as FilterOption[]) || [];
    if (key === 'commission_type') {
      return raw.map(opt => ({
        value: opt.value === 'SLAB' ? 'Slab' : (opt.value === 'NON_SLAB' ? 'Non-Slab' : opt.value),
        count: opt.count
      }));
    }
    return raw;
  };

  // ─── Table Columns & Data Switching ─────────────────────────────────────────

  const currentTab = filters.commission_type === 'SLAB' ? 'SLAB' : 'NON_SLAB';

  const tableData = records;

  const nonSlabColumns = useMemo<ColumnDef<any>[]>(
    () => createNonSlabColumns({
      expandedRows,
      toggleRowExpanded,
      onEditRule: handleEditRule,
      onEditSlab: handleEditSlab,
      stateSuggestions: stateSuggestions,
      productSuggestions: productSuggestions,
    }),
    [expandedRows, stateSuggestions, productSuggestions]
  );

  const slabColumns = useMemo<ColumnDef<any>[]>(
    () => createSlabColumns({
      expandedRows,
      toggleRowExpanded,
      onEditRule: handleEditRule,
      onEditSlab: handleEditSlab,
      stateSuggestions: stateSuggestions,
      productSuggestions: productSuggestions,
    }),
    [expandedRows, stateSuggestions, productSuggestions]
  );

  const columns = useMemo(() => {
    return currentTab === 'SLAB' ? slabColumns : nonSlabColumns;
  }, [currentTab, slabColumns, nonSlabColumns]);

  const table = useReactTable({
    data: tableData,
    columns,
    state: { sorting, columnVisibility },
    onSortingChange: setSorting,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // ─── Expanded details row ──────────────────────────────────────────────────
  const renderExpandedRow = (rule: CommissionRule, colCount: number, rowId: string) => (
    <ExpandedRuleDetails rule={rule} colCount={colCount} onEditSlab={handleEditSlab} onClose={() => toggleRowExpanded(rowId)} />
  );

  // ─── JSX ───────────────────────────────────────────────────────────────────

  const tableContent = (
    <div className={`flex flex-col h-full bg-white dark:bg-[#0B1220] ${isFullscreen ? 'fixed inset-0 z-[30]' : ''}`}>

      {/* ── UPLOAD BANNER (prominent, permanent drag-and-drop target) ── */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => uploadInputRef.current?.click()}
        className={`flex-shrink-0 flex items-center justify-between gap-4 mx-4 mt-3 mb-1 px-5 py-4 rounded-2xl border-2 border-dashed cursor-pointer transition-colors duration-150 ${
          isDragging
            ? 'border-[#4F46E5] bg-[#4F46E5]/5 dark:bg-indigo-500/10'
            : 'border-[#C7D2FE] dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 hover:border-[#4F46E5]/50 dark:hover:border-indigo-500/50'
        }`}
      >
        <input
          ref={uploadInputRef}
          type="file"
          accept=".xlsx,.xls,.pdf,.docx"
          className="hidden"
          onChange={handleUploadInputChange}
        />
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-[#4F46E5]/10 dark:bg-indigo-500/10 flex-shrink-0">
            <UploadCloud className="w-5 h-5 text-[#4F46E5] dark:text-indigo-400" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-800 dark:text-slate-100">Upload a new broker grid</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 truncate">Drag and drop a file here, or click to browse</p>
          </div>
        </div>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); uploadInputRef.current?.click(); }}
          disabled={isUploading}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#4F46E5] hover:bg-[#4338CA] disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-bold shadow-sm transition-colors duration-150 cursor-pointer flex-shrink-0"
        >
          {isUploading ? <RefreshCw className="w-4.5 h-4.5 animate-spin" /> : <UploadCloud className="w-4.5 h-4.5" />}
          <span>{isUploading ? 'Uploading...' : 'Upload Grid'}</span>
        </button>
      </div>

      {/* ── BREADCRUMB ROW: current file + History + Refresh ── */}
      <div className="flex-shrink-0 flex items-center justify-between gap-2 px-4 py-2 border-b border-[#E5E7EB] dark:border-[#1F2937] bg-white dark:bg-[#111827] flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          {/* Mobile sidebar trigger — the old top header bar (which owned this) was removed */}
          <button
            type="button"
            onClick={openMobileSidebar}
            className="md:hidden p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer flex-shrink-0"
            title="Open menu"
          >
            <Menu className="w-4.5 h-4.5" />
          </button>

          {company && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-500 min-w-0">
              <span>Upload Files</span>
              <span className="text-slate-300 dark:text-slate-700">›</span>
              <span className="font-semibold text-slate-700 dark:text-slate-300">{company}</span>
              {filename && (
                <>
                  <span className="text-slate-300 dark:text-slate-700">•</span>
                  <span className="truncate max-w-[220px]" title={filename}>{filename}</span>
                </>
              )}
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="font-semibold text-slate-700 dark:text-slate-300">{totalRecords.toLocaleString()} rules</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0 ml-auto">
          <button
            type="button"
            onClick={() => setIsHistoryOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-[#E5E7EB] dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 text-xs font-semibold transition-colors duration-150 cursor-pointer"
            title="Upload History"
          >
            <History className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">History</span>
            {uploads.length > 0 && (
              <span className="bg-[#4F46E5] text-white text-xs font-bold px-1.5 py-0.5 rounded-full leading-none">
                {uploads.length}
              </span>
            )}
          </button>

          {/* Theme toggle — moved here from the removed top header bar */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-[#E5E7EB] dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors duration-150 cursor-pointer"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </button>

          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-[#E5E7EB] dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors duration-150 cursor-pointer"
              title="Refresh data"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* ── SEARCH + TABS + MORE OPTIONS ROW ── */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-2 border-b border-[#E5E7EB] dark:border-[#1F2937] bg-white dark:bg-[#111827] flex-wrap">

        {/* Search */}
        <div className="order-1 w-full sm:w-auto sm:flex-1 sm:max-w-md">
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 dark:text-slate-500" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search Product, State, Insurer, Policy..."
              className="w-full pl-9 pr-8 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-slate-700 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:border-[#4F46E5]/60 focus:ring-1 focus:ring-[#4F46E5]/20 text-sm transition-colors duration-150"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => { setSearchInput(''); setFilters(prev => ({ ...prev, search: '' })); }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-600 hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </form>
        </div>

        {/* Non-Slab / Slab tabs — inline with search now, not a separate full-width row */}
        <div className="order-2 flex items-center gap-5 flex-shrink-0">
          {([
            { key: 'NON_SLAB', label: 'Non-Slab' },
            { key: 'SLAB', label: 'Slab' },
          ] as const).map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilters(prev => ({ ...prev, commission_type: key }))}
              className={`relative py-2 text-sm font-medium transition-colors duration-150 cursor-pointer ${
                currentTab === key
                  ? 'text-[#4F46E5] dark:text-indigo-400'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              {label}
              {currentTab === key && (
                <span className="absolute left-0 right-0 -bottom-2 h-0.5 bg-[#4F46E5] dark:bg-indigo-400 rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* Fullscreen + More Options */}
        <div className="order-3 flex items-center gap-2 flex-shrink-0 ml-auto">
          <button
            type="button"
            onClick={() => setIsFullscreen(prev => !prev)}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-[#E5E7EB] dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors duration-150 cursor-pointer"
            title={isFullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen table'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>

          <div className="relative" ref={moreRef}>
            <button
              type="button"
              onClick={() => setIsMoreOpen(prev => !prev)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-[#E5E7EB] dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold transition-colors duration-150 cursor-pointer"
            >
              <span>More Options</span>
              {activeFilterCount > 0 && (
                <span className="bg-[#4F46E5] text-white text-xs font-bold px-1.5 py-0.5 rounded-full leading-none">{activeFilterCount}</span>
              )}
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-150 ${isMoreOpen ? 'rotate-180' : ''}`} />
            </button>

            {isMoreOpen && (
              <div className="absolute right-0 top-full mt-2 w-64 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-700 rounded-xl shadow-lg z-30 p-2 flex flex-col gap-1">

                {/* Filters */}
                <button
                  type="button"
                  onClick={() => { setIsFilterOpen(true); closeMore(); }}
                  className="flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                >
                  <span className="flex items-center gap-2.5"><Filter className="w-4 h-4" /> Filters</span>
                  {activeFilterCount > 0 && (
                    <span className="bg-[#4F46E5] text-white text-xs font-bold px-1.5 py-0.5 rounded-full leading-none">{activeFilterCount}</span>
                  )}
                </button>

                <div className="h-px bg-[#E5E7EB] dark:bg-slate-800 my-1" />

                {/* Columns (expands in place) */}
                <button
                  type="button"
                  onClick={() => setIsColsOpen(prev => !prev)}
                  className="flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                >
                  <span className="flex items-center gap-2.5"><Eye className="w-4 h-4" /> Columns</span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-150 ${isColsOpen ? 'rotate-180' : ''}`} />
                </button>
                {isColsOpen && (
                  <div className="pl-3 pr-1 py-1 flex flex-col gap-0.5 max-h-56 overflow-y-auto">
                    {table.getAllLeafColumns()
                      .filter(col => col.getCanHide())
                      .map(col => (
                        <label key={col.id} className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors">
                          <input
                            type="checkbox"
                            checked={col.getIsVisible()}
                            onChange={col.getToggleVisibilityHandler()}
                            className="w-3.5 h-3.5 rounded accent-[#4F46E5] cursor-pointer"
                          />
                          <span className="text-xs text-slate-600 dark:text-slate-300 capitalize">{String(col.columnDef.header)}</span>
                        </label>
                      ))
                    }
                  </div>
                )}

                <div className="h-px bg-[#E5E7EB] dark:bg-slate-800 my-1" />

                {/* Export (expands in place) */}
                <button
                  type="button"
                  onClick={() => setIsExportOpen(prev => !prev)}
                  disabled={records.length === 0}
                  className="flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                >
                  <span className="flex items-center gap-2.5"><Download className="w-4 h-4" /> Export</span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-150 ${isExportOpen ? 'rotate-180' : ''}`} />
                </button>
                {isExportOpen && (
                  <div className="pl-3 pr-1 py-1 flex flex-col gap-1">
                    <button
                      type="button"
                      onClick={() => { handleExportCSV(); closeMore(); }}
                      className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" /> CSV
                    </button>
                    <button
                      type="button"
                      onClick={() => { handleExportJSON(); closeMore(); }}
                      className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                    >
                      <FileJson className="w-3.5 h-3.5" /> JSON
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── TABLE AREA ── */}
      <div className="flex-1 overflow-auto min-h-0">
        {isLoading ? (
          <div className="h-full flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-8 h-8 text-[#4F46E5] animate-spin" />
            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Loading records...</p>
          </div>
        ) : !selectedUploadId || records.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-4 px-4 text-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-900 flex items-center justify-center border border-[#E5E7EB] dark:border-slate-800">
              <FileSpreadsheet className="w-8 h-8 text-slate-300 dark:text-slate-700" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-700 dark:text-slate-300">
                {!selectedUploadId ? 'No upload selected' : 'No matching rules'}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-500 mt-1 max-w-xs">
                {!selectedUploadId
                  ? 'Click History to select an uploaded grid.'
                  : 'Try clearing filters or selecting a different upload.'}
              </p>
            </div>
            {!selectedUploadId && (
              <button
                type="button"
                onClick={() => setIsHistoryOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#4F46E5] hover:bg-[#4338CA] text-white text-sm font-semibold transition-colors duration-150 cursor-pointer"
              >
                <History className="w-4 h-4" /> Open History
              </button>
            )}
          </div>
        ) : (
          <table className="min-w-full divide-y divide-[#E5E7EB] dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-900/80 sticky top-0 z-10 backdrop-blur-sm">
              {table.getHeaderGroups().map(hg => (
                <tr key={hg.id}>
                  {hg.headers.map((header, idx) => (
                    <th
                      key={header.id}
                      scope="col"
                      onClick={header.column.getToggleSortingHandler()}
                      className={`px-4 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider whitespace-nowrap select-none
                        ${header.column.getCanSort() ? 'cursor-pointer hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors' : ''}
                        ${idx === 0 ? 'sticky left-0 z-20 bg-slate-50 dark:bg-slate-900' : ''}
                      `}
                    >
                      <div className="flex items-center gap-1.5">
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getCanSort() && (
                          <span className="text-slate-400 dark:text-slate-600">
                            {header.column.getIsSorted() === 'asc'
                              ? <ArrowUp className="w-3 h-3 text-[#4F46E5] dark:text-indigo-400" />
                              : header.column.getIsSorted() === 'desc'
                              ? <ArrowDown className="w-3 h-3 text-[#4F46E5] dark:text-indigo-400" />
                              : <ArrowUpDown className="w-3 h-3" />}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-[#E5E7EB]/70 dark:divide-slate-800/60">
              {table.getRowModel().rows.map(row => (
                <React.Fragment key={row.id}>
                  <tr className={`hover:bg-slate-50 dark:hover:bg-slate-900/40 transition-colors ${expandedRows[row.id] ? 'bg-slate-50 dark:bg-slate-900/20' : ''}`}>
                    {row.getVisibleCells().map((cell, idx) => (
                      <td
                        key={cell.id}
                        className={`px-4 py-3 whitespace-nowrap text-sm
                          ${idx === 0 ? 'sticky left-0 z-[5] bg-white dark:bg-[#0B1220] group-hover:bg-slate-50 dark:group-hover:bg-slate-900' : ''}
                        `}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                  {expandedRows[row.id] && renderExpandedRow(row.original, columns.length, row.id)}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── PAGINATION ── */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-t border-[#E5E7EB] dark:border-[#1F2937] bg-white dark:bg-[#111827] select-none">
        <span className="text-xs text-slate-500 dark:text-slate-500">
          Showing page <span className="font-semibold text-slate-700 dark:text-slate-300">{currentPage}</span> of{' '}
          <span className="font-semibold text-slate-700 dark:text-slate-300">{totalPages || 1}</span> —{' '}
          <span className="font-semibold text-slate-700 dark:text-slate-300">{totalRecords.toLocaleString()}</span> total rules
        </span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 px-2">{currentPage} / {totalPages || 1}</span>
          <button
            type="button"
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  // ─── Filter Drawer (right side) ────────────────────────────────────────────

  const filterDrawer = (
    <>
      <div
        onClick={() => setIsFilterOpen(false)}
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px] transition-opacity duration-300 ${
          isFilterOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      />
      <div
        className={`fixed right-0 top-0 bottom-0 z-50 w-80 bg-white dark:bg-slate-900 border-l border-[#E5E7EB] dark:border-slate-800 shadow-xl flex flex-col transition-transform duration-300 ease-in-out ${
          isFilterOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 h-14 border-b border-[#E5E7EB] dark:border-slate-800 flex-shrink-0">
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Column Filters</p>
            {activeFilterCount > 0 && (
              <p className="text-xs text-[#4F46E5] dark:text-indigo-400">{activeFilterCount} filter{activeFilterCount !== 1 ? 's' : ''} active</p>
            )}
          </div>
          <div className="flex items-center gap-1">
            {activeFilterCount > 0 && (
              <button
                type="button"
                onClick={resetFilters}
                className="px-2.5 py-1 rounded-lg text-xs font-bold text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 border border-red-200 dark:border-red-500/20 hover:border-red-300 dark:hover:border-red-500/40 transition-colors cursor-pointer"
              >
                Reset
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsFilterOpen(false)}
              className="p-1.5 rounded-lg text-slate-400 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {[
            { title: 'LOB', opts: getOpts('lob'), key: 'lob' },
            { title: 'File Type', opts: getOpts('file_type'), key: 'file_type' },
            { title: 'Insurer', opts: getOpts('insurance_company'), key: 'company' },
            { title: 'Product', opts: getOpts('product'), key: 'product' },
            { title: 'Policy Type', opts: getOpts('policy_type'), key: 'policy_type' },
            { title: 'Plan Type', opts: getOpts('plan_type'), key: 'plan_type' },
            { title: 'Sub Product', opts: getOpts('sub_product'), key: 'sub_product' },
            { title: 'Class', opts: getOpts('class_'), key: 'class' },
            { title: 'Sub Class', opts: getOpts('sub_class'), key: 'sub_class' },
            { title: 'Make', opts: getOpts('make'), key: 'make' },
            { title: 'Model', opts: getOpts('model'), key: 'model' },
            { title: 'Fuel Type', opts: getOpts('fuel_type'), key: 'fuel_type' },
            { title: 'Body Type', opts: getOpts('body_type'), key: 'body_type' },
            { title: 'CPA Status', opts: getOpts('cpa_status'), key: 'cpa_status' },
            { title: 'NCB Status', opts: getOpts('ncb_status'), key: 'ncb_status' },
            { title: 'Partner Type', opts: getOpts('partner_type'), key: 'partner_type' },
            { title: 'State', opts: getOpts('state'), key: 'state' },
            { title: 'Zone', opts: getOpts('zone'), key: 'zone' },
            { title: 'Source', opts: getOpts('source'), key: 'source' },
            { title: 'RTO', opts: getOpts('rto'), key: 'rto' },
            { title: 'Effective Date', opts: getOpts('effective_date'), key: 'effective_date' },
            { title: 'Remarks', opts: getOpts('remarks'), key: 'remarks' },
          ].map(({ title, opts, key }) => (
            <div key={key}>
              <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1.5">{title}</p>
              <MultiSelectFilter
                title={title}
                options={opts}
                selectedValues={filters[key] ? (filters[key] as string).split(',').filter(Boolean) : []}
                onChange={(vals) => setFilters(prev => ({ ...prev, [key]: vals.join(',') }))}
              />
            </div>
          ))}

          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Vehicle Age</p>
            <MultiSelectFilter
              title="Vehicle Age"
              options={STATIC_VEHICLE_AGE}
              selectedValues={filters.vehicleAge ? filters.vehicleAge.split(',').filter(Boolean) : []}
              onChange={(vals) => setFilters(prev => ({ ...prev, vehicleAge: vals.join(',') }))}
            />
          </div>

          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Validation</p>
            <MultiSelectFilter
              title="Validation"
              options={getOpts('validation_status').length > 0 ? getOpts('validation_status') : [{ value: 'VALID', count: 0 }, { value: 'WARNING', count: 0 }]}
              selectedValues={filters.validation_status ? filters.validation_status.split(',').filter(Boolean) : []}
              onChange={(vals) => setFilters(prev => ({ ...prev, validation_status: vals.join(',') }))}
            />
          </div>
        </div>

        {/* Apply footer */}
        <div className="p-4 border-t border-[#E5E7EB] dark:border-slate-800 flex-shrink-0">
          <button
            type="button"
            onClick={() => setIsFilterOpen(false)}
            className="w-full py-2.5 rounded-lg bg-[#4F46E5] hover:bg-[#4338CA] text-white text-sm font-semibold transition-colors duration-150 cursor-pointer"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {tableContent}

      {/* History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        uploads={uploads}
        selectedUploadId={selectedUploadId}
        onSelectUpload={onSelectUpload}
        onDeleteUpload={onDeleteUpload}
        isLoading={isUploadsLoading}
        onRefresh={onRefresh || (() => {})}
      />

      {/* Filter Drawer */}
      {filterDrawer}
    </>
  );
};

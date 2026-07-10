import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { ExpandedRuleDetails } from '../components/ExpandedRuleDetails';
import type { FilterOptionsMap } from '../services/api';
import type { FilterOption } from '../components/MultiSelectFilter';
import { MultiSelectFilter } from '../components/MultiSelectFilter';
import { createNonSlabColumns, createSlabColumns } from '../tableColumns/commissionRuleColumns';
import { useEditRuleField } from '../hooks/useEditRuleField';
import type { EditableRuleField, EditableSlabField } from '../types';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import {
  Search,
  Filter,
  ChevronRight,
  ChevronDown,
  ChevronLeft,
  RefreshCw,
  Calendar,
  Maximize2,
  Minimize2,
  X,
  Download,
  FileJson,
  FileSpreadsheet,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

type FiltersState = {
  insurer: string[];
  lob: string[];
  file_type: string[];
  product: string[];
  policy_type: string[];
  plan_type: string[];
  sub_product: string[];
  class: string[];
  sub_class: string[];
  make: string[];
  model: string[];
  fuel_type: string[];
  body_type: string[];
  vehicle_age: string[];
  cpa_status: string[];
  ncb_status: string[];
  partner_type: string[];
  state: string[];
  zone: string[];
  source: string[];
  rto: string[];
  remarks: string[];
  effective_date: string[];
  commission_type: string[];
  validation_status: string[];
};

// commission_type defaults to ['NON_SLAB'] (not []) so the query sent to the
// backend actually matches the visually-active "Non-Slab" tab on first load —
// an empty array applies no filter at all, which was silently returning both
// SLAB and NON_SLAB rows under the "Non-Slab" tab until the user clicked a tab.
const EMPTY_FILTERS: FiltersState = {
  insurer: [], lob: [], file_type: [], product: [], policy_type: [], plan_type: [], sub_product: [],
  class: [], sub_class: [], make: [], model: [], fuel_type: [], body_type: [],
  vehicle_age: [], cpa_status: [], ncb_status: [], partner_type: [], state: [],
  zone: [], source: [], rto: [], remarks: [], effective_date: [], commission_type: ['NON_SLAB'], validation_status: [],
};

const STATIC_VEHICLE_AGE: FilterOption[] = [
  { value: 'Upto 5 yrs', count: 0 },
  { value: '6 - 15 yrs', count: 0 },
  { value: '> 15 yrs', count: 0 },
];

// ─── Component ───────────────────────────────────────────────────────────────

export const CustomiseData: React.FC = () => {
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [filters, setFilters] = useState<FiltersState>(EMPTY_FILTERS);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  // Exit fullscreen on Escape
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && isFullscreen) setIsFullscreen(false); };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
  }, [isFullscreen]);

  // Close export dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setIsExportOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Fetch distinct filter options
  const { data: filterOptions = {}, isLoading: isFiltersLoading } = useQuery<FilterOptionsMap>({
    queryKey: ['filterOptions'],
    queryFn: () => api.getDistinctFilters(),
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
    const parentRuleId = slabRows.find(r => r.slab_id === slabId)?.id ?? slabId;
    editRuleField.mutate({ ruleId: parentRuleId, target: { kind: 'slab', slabId, field }, value });
  };

  // Global search query
  const { data: searchResults, isLoading: isSearchLoading, isFetching } = useQuery({
    queryKey: ['globalSearch', filters, searchQuery, dateFrom, dateTo, page],
    queryFn: () => api.searchRules({
      filters,
      search: searchQuery || undefined,
      effective_date_from: dateFrom || undefined,
      effective_date_to: dateTo || undefined,
      page,
      limit: 50,
    }),
    staleTime: 30_000,
  });

  const records = searchResults?.records || [];
  const metadata = searchResults?.metadata || { total: 0, page: 1, limit: 50, pages: 0 };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
    setPage(1);
  };

  const handleFilterChange = (field: keyof FiltersState, values: string[]) => {
    setFilters(prev => ({ ...prev, [field]: values }));
    setPage(1);
  };

  const resetAllFilters = () => {
    setFilters({
      ...EMPTY_FILTERS,
      commission_type: filters.commission_type,
    });
    setSearchInput('');
    setSearchQuery('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  const activeFilterCount = Object.entries(filters).filter(([k, v]) => k !== 'commission_type' && v.length > 0).length
    + (searchQuery ? 1 : 0)
    + (dateFrom || dateTo ? 1 : 0);

  const hasAnyFilter = activeFilterCount > 0;

  const toggleRowExpanded = (rowId: string) => {
    setExpandedRows(prev => ({ ...prev, [rowId]: !prev[rowId] }));
  };

  const getOpts = (key: string): FilterOption[] => {
    const raw = ((filterOptions as FilterOptionsMap)[key] as FilterOption[]) || [];
    if (key === 'commission_type') {
      return raw.map(opt => ({
        value: opt.value === 'SLAB' ? 'Slab' : (opt.value === 'NON_SLAB' ? 'Non-Slab' : opt.value),
        count: opt.count
      }));
    }
    return raw;
  };

  // ─── Table Columns & Data Switching ─────────────────────────────────────────

  const currentTab = filters.commission_type.includes('SLAB') ? 'SLAB' : 'NON_SLAB';

  const slabRows = useMemo(() => {
    if (currentTab !== 'SLAB') return [];
    const list: any[] = [];
    records.forEach(rule => {
      if (rule.slabs && rule.slabs.length > 0) {
        rule.slabs.forEach((slab: any) => {
          list.push({
            ...rule,
            slab_id: slab.id,
            payin_type: slab.payin_type,
            premium_type: slab.premium_type,
            slab_from: slab.slab_from,
            slab_to: slab.slab_to,
            payin_od: slab.payin_od,
            payout_od: slab.payout_od,
            payin_tp: slab.payin_tp,
            payout_tp: slab.payout_tp,
            payin_net: slab.payin_net,
            payout_net: slab.payout_net,
            payin_reward: null,
            payout_reward: null,
            payin_scheme: null,
            payout_scheme: null,
          });
        });
      } else {
        list.push(rule);
      }
    });
    return list;
  }, [records, currentTab]);

  const tableData = useMemo(() => {
    return currentTab === 'SLAB' ? slabRows : records;
  }, [currentTab, records, slabRows]);

  const nonSlabColumns = useMemo<ColumnDef<any>[]>(
    () => createNonSlabColumns({
      expandedRows,
      toggleRowExpanded,
      onEditRule: handleEditRule,
      onEditSlab: handleEditSlab,
      stateSuggestions,
      productSuggestions,
      includeValidationStatus: true,
      includeSourceFile: true,
    }),
    [expandedRows, stateSuggestions, productSuggestions]
  );

  const slabColumns = useMemo<ColumnDef<any>[]>(
    () => createSlabColumns({
      expandedRows,
      toggleRowExpanded,
      onEditRule: handleEditRule,
      onEditSlab: handleEditSlab,
      stateSuggestions,
      productSuggestions,
      includeSourceFile: true,
    }),
    [expandedRows, stateSuggestions, productSuggestions]
  );

  const columns = useMemo(() => {
    return currentTab === 'SLAB' ? slabColumns : nonSlabColumns;
  }, [currentTab, slabColumns, nonSlabColumns]);

  const table = useReactTable({
    data: tableData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // ─── Filter categories ─────────────────────────────────────────────────────

  const filterGroups = [
    { label: 'LOB', field: 'lob' as keyof FiltersState, dbKey: 'lob' },
    { label: 'File Type', field: 'file_type' as keyof FiltersState, dbKey: 'file_type' },
    { label: 'Insurer', field: 'insurer' as keyof FiltersState, dbKey: 'insurance_company' },
    { label: 'Product', field: 'product' as keyof FiltersState, dbKey: 'product' },
    { label: 'Policy Type', field: 'policy_type' as keyof FiltersState, dbKey: 'policy_type' },
    { label: 'Plan Type', field: 'plan_type' as keyof FiltersState, dbKey: 'plan_type' },
    { label: 'Sub Product', field: 'sub_product' as keyof FiltersState, dbKey: 'sub_product' },
    { label: 'Class', field: 'class' as keyof FiltersState, dbKey: 'class_' },
    { label: 'Sub Class', field: 'sub_class' as keyof FiltersState, dbKey: 'sub_class' },
    { label: 'Make', field: 'make' as keyof FiltersState, dbKey: 'make' },
    { label: 'Model', field: 'model' as keyof FiltersState, dbKey: 'model' },
    { label: 'Fuel Type', field: 'fuel_type' as keyof FiltersState, dbKey: 'fuel_type' },
    { label: 'Body Type', field: 'body_type' as keyof FiltersState, dbKey: 'body_type' },
    { label: 'CPA Status', field: 'cpa_status' as keyof FiltersState, dbKey: 'cpa_status' },
    { label: 'NCB Status', field: 'ncb_status' as keyof FiltersState, dbKey: 'ncb_status' },
    { label: 'Partner Type', field: 'partner_type' as keyof FiltersState, dbKey: 'partner_type' },
    { label: 'State', field: 'state' as keyof FiltersState, dbKey: 'state' },
    { label: 'Zone', field: 'zone' as keyof FiltersState, dbKey: 'zone' },
    { label: 'Source', field: 'source' as keyof FiltersState, dbKey: 'source' },
    { label: 'RTO', field: 'rto' as keyof FiltersState, dbKey: 'rto' },
    { label: 'Remarks', field: 'remarks' as keyof FiltersState, dbKey: 'remarks' },
    { label: 'Effective Date', field: 'effective_date' as keyof FiltersState, dbKey: 'effective_date' },
    { label: 'Validation', field: 'validation_status' as keyof FiltersState, dbKey: 'validation_status' },
  ];

  // ─── JSX ───────────────────────────────────────────────────────────────────

  return (
    <>
      <div className={`flex flex-col h-full bg-white dark:bg-[#0B1220] ${isFullscreen ? 'fixed inset-0 z-[30]' : ''}`}>

        {/* ── TOOLBAR ── */}
        <div className="flex-shrink-0 flex items-center gap-2 px-4 py-2 border-b border-[#E5E7EB] dark:border-[#1F2937] bg-white dark:bg-[#111827] flex-wrap">

          {/* LEFT: date range + total count */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-500">
              <Calendar className="w-3.5 h-3.5" />
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                className="px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-slate-600 dark:text-slate-300 text-xs focus:outline-none focus:border-[#4F46E5]/60 cursor-pointer"
              />
              <span className="text-slate-300 dark:text-slate-700">→</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                className="px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-slate-600 dark:text-slate-300 text-xs focus:outline-none focus:border-[#4F46E5]/60 cursor-pointer"
              />
            </div>

            {metadata.total > 0 && (
              <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300">
                {metadata.total.toLocaleString()} <span className="text-slate-400 dark:text-slate-500">rules</span>
                {(isSearchLoading || isFetching) && <RefreshCw className="w-3 h-3 text-[#4F46E5] dark:text-indigo-400 animate-spin ml-1" />}
              </span>
            )}
          </div>

          {/* CENTER: Search */}
          <div className="order-3 sm:order-none w-full sm:w-auto sm:flex-1 sm:max-w-xl sm:mx-auto">
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
                <button type="button" onClick={() => { setSearchInput(''); setSearchQuery(''); setPage(1); }} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-600 hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </form>
          </div>

          {/* RIGHT: Filters, Clear, Fullscreen, Export */}
          <div className="flex items-center gap-2 flex-shrink-0 ml-auto sm:ml-0">
            <button
              type="button"
              onClick={() => setIsFilterOpen(true)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors duration-150 cursor-pointer ${
                activeFilterCount > 0
                  ? 'bg-[#4F46E5]/10 border-[#4F46E5]/30 text-[#4F46E5] dark:text-indigo-300 hover:bg-[#4F46E5]/15'
                  : 'bg-slate-100 dark:bg-slate-800 border-[#E5E7EB] dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <span className="bg-[#4F46E5] text-white text-xs font-bold px-1.5 py-0.5 rounded-full leading-none">{activeFilterCount}</span>
              )}
            </button>

            {hasAnyFilter && (
              <button type="button" onClick={resetAllFilters} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-red-500 dark:text-red-400 border border-red-200 dark:border-red-500/20 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors cursor-pointer">
                <X className="w-3 h-3" /> Clear
              </button>
            )}

            <button type="button" onClick={() => setIsFullscreen(p => !p)} className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-[#E5E7EB] dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors duration-150 cursor-pointer" title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>

            {/* Export dropdown */}
            <div className="relative" ref={exportRef}>
              <button
                type="button"
                onClick={() => setIsExportOpen(prev => !prev)}
                disabled={records.length === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E5E7EB] dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold transition-colors duration-150 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export</span>
                <ChevronDown className="w-3 h-3" />
              </button>
              {isExportOpen && (
                <div className="absolute right-0 top-full mt-1.5 w-44 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-700 rounded-xl shadow-lg z-20 p-1.5 flex flex-col gap-0.5">
                  <button
                    type="button"
                    onClick={() => { api.exportAsCSV(records, 'Commission_Rules'); setIsExportOpen(false); }}
                    className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" /> CSV
                  </button>
                  <button
                    type="button"
                    onClick={() => { api.exportAsJSON(records, 'Commission_Rules'); setIsExportOpen(false); }}
                    className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer"
                  >
                    <FileJson className="w-3.5 h-3.5" /> JSON
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── DATASET TABS (below toolbar) ── */}
        <div className="flex-shrink-0 flex items-center gap-5 px-4 border-b border-[#E5E7EB] dark:border-[#1F2937] bg-white dark:bg-[#111827]">
          {([
            { key: 'NON_SLAB', label: 'Non-Slab' },
            { key: 'SLAB', label: 'Slab' },
          ] as const).map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => handleFilterChange('commission_type', [key])}
              className={`relative py-2.5 text-sm font-medium transition-colors duration-150 cursor-pointer ${
                currentTab === key
                  ? 'text-[#4F46E5] dark:text-indigo-400'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              {label}
              {currentTab === key && (
                <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-[#4F46E5] dark:bg-indigo-400 rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* ── TABLE ── */}
        <div className="flex-1 overflow-auto min-h-0">
          {isSearchLoading ? (
            <div className="h-full flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-8 h-8 text-[#4F46E5] animate-spin" />
              <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Querying database...</p>
            </div>
          ) : records.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-4 text-center px-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-900 flex items-center justify-center border border-[#E5E7EB] dark:border-slate-800">
                <FileSpreadsheet className="w-8 h-8 text-slate-300 dark:text-slate-700" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-700 dark:text-slate-300">No Rules Found</h3>
                <p className="text-xs text-slate-500 dark:text-slate-500 mt-1 max-w-xs">
                  No commission rules match your filters.{' '}
                  {hasAnyFilter && <button onClick={resetAllFilters} className="text-[#4F46E5] dark:text-indigo-400 hover:underline cursor-pointer">Clear all filters</button>}
                </p>
              </div>
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
                          ${header.column.getCanSort() ? 'cursor-pointer hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/40 transition-colors' : ''}
                          ${idx === 0 ? 'sticky left-0 z-20 bg-slate-50 dark:bg-slate-900' : ''}
                        `}
                      >
                        <div className="flex items-center gap-1.5">
                          {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getCanSort() && (
                            <span className="text-slate-400 dark:text-slate-600">
                              {header.column.getIsSorted() === 'asc' ? <ArrowUp className="w-3 h-3 text-[#4F46E5] dark:text-indigo-400" />
                                : header.column.getIsSorted() === 'desc' ? <ArrowDown className="w-3 h-3 text-[#4F46E5] dark:text-indigo-400" />
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
                          className={`px-4 py-3 whitespace-nowrap text-sm ${idx === 0 ? 'sticky left-0 z-[5] bg-white dark:bg-[#0B1220]' : ''}`}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                    {expandedRows[row.id] && (
                      <ExpandedRuleDetails rule={row.original} colCount={columns.length} />
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* ── PAGINATION ── */}
        <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-t border-[#E5E7EB] dark:border-[#1F2937] bg-white dark:bg-[#111827] select-none">
          <span className="text-xs text-slate-500 dark:text-slate-500">
            Page <span className="font-semibold text-slate-700 dark:text-slate-300">{page}</span> ·{' '}
            <span className="font-semibold text-slate-700 dark:text-slate-300">{records.length}</span> of{' '}
            <span className="font-semibold text-slate-700 dark:text-slate-300">{metadata.total.toLocaleString()}</span> rules
          </span>
          <div className="flex items-center gap-1.5">
            <button type="button" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 px-2">{page} / {metadata.pages || 1}</span>
            <button type="button" onClick={() => setPage(p => Math.min(metadata.pages, p + 1))} disabled={page >= (metadata.pages || 1)}
              className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ── FILTER DRAWER (right side) ── */}
      <div
        onClick={() => setIsFilterOpen(false)}
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px] transition-opacity duration-300 ${isFilterOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
      />
      <div
        className={`fixed right-0 top-0 bottom-0 z-50 w-80 bg-white dark:bg-slate-900 border-l border-[#E5E7EB] dark:border-slate-800 shadow-xl flex flex-col transition-transform duration-300 ease-in-out ${isFilterOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-5 h-14 border-b border-[#E5E7EB] dark:border-slate-800 flex-shrink-0">
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Dynamic Filters</p>
            {activeFilterCount > 0 && <p className="text-xs text-[#4F46E5] dark:text-indigo-400">{activeFilterCount} active</p>}
          </div>
          <div className="flex items-center gap-1">
            {hasAnyFilter && (
              <button type="button" onClick={resetAllFilters} className="px-2.5 py-1 rounded-lg text-xs font-bold text-red-500 dark:text-red-400 border border-red-200 dark:border-red-500/20 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors cursor-pointer">Reset</button>
            )}
            <button type="button" onClick={() => setIsFilterOpen(false)} className="p-1.5 rounded-lg text-slate-400 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Loading skeleton or filter list */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {isFiltersLoading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-9 rounded-lg bg-slate-100 dark:bg-slate-800/40 animate-pulse" />
            ))
          ) : (
            <>
              {filterGroups.map(({ label, field, dbKey }) => (
                <div key={field}>
                  <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">{label}</p>
                  <MultiSelectFilter
                    title={label}
                    options={getOpts(dbKey)}
                    selectedValues={filters[field]}
                    onChange={(vals) => handleFilterChange(field, vals)}
                  />
                </div>
              ))}
              <div>
                <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Vehicle Age</p>
                <MultiSelectFilter
                  title="Vehicle Age"
                  options={STATIC_VEHICLE_AGE}
                  selectedValues={filters.vehicle_age}
                  onChange={(vals) => handleFilterChange('vehicle_age', vals)}
                />
              </div>
            </>
          )}
        </div>

        {/* Apply */}
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
};

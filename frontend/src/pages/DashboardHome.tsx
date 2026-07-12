import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useSidebar } from '../contexts/SidebarContext';
import {
  FileSpreadsheet,
  Layers,
  ListChecks,
  AlertTriangle,
  Building2,
  History,
  RefreshCw,
  Menu,
  Moon,
  Sun,
  CheckCircle,
} from 'lucide-react';

const KPI_CARDS = [
  { key: 'total_uploads', label: 'Total Uploads', icon: FileSpreadsheet, color: 'text-[#4F46E5] dark:text-indigo-400', bg: 'bg-[#4F46E5]/10 dark:bg-indigo-500/10' },
  { key: 'total_rules', label: 'Total Rules', icon: ListChecks, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
  { key: 'slab_rules', label: 'Slab Rules', icon: Layers, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-500/10' },
  { key: 'non_slab_rules', label: 'Non-Slab Rules', icon: ListChecks, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-500/10' },
  { key: 'warning_rules', label: 'Validation Warnings', icon: AlertTriangle, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-500/10' },
] as const;

export const DashboardHome: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { openMobileSidebar } = useSidebar();

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['dashboardSummary'],
    queryFn: api.getDashboardSummary,
    staleTime: 30_000,
  });

  const maxInsurerCount = Math.max(1, ...(data?.insurer_breakdown || []).map(i => i.count));

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#0B1220] overflow-y-auto">
      {/* ── TOOLBAR ── */}
      <div className="flex-shrink-0 flex items-center justify-between gap-2 px-4 py-2 border-b border-[#E5E7EB] dark:border-[#1F2937] bg-white dark:bg-[#111827]">
        <div className="flex items-center gap-2 min-w-0">
          <button
            type="button"
            onClick={openMobileSidebar}
            className="md:hidden p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer flex-shrink-0"
            title="Open menu"
          >
            <Menu className="w-4.5 h-4.5" />
          </button>
          <h1 className="text-sm font-bold text-slate-800 dark:text-slate-100">Dashboard Overview</h1>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            type="button"
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-[#E5E7EB] dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors duration-150 cursor-pointer"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </button>
          <button
            type="button"
            onClick={() => refetch()}
            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-[#E5E7EB] dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors duration-150 cursor-pointer"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex-1 p-4 md:p-6 flex flex-col gap-6">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <RefreshCw className="w-8 h-8 text-[#4F46E5] animate-spin" />
          </div>
        ) : (
          <>
            {/* ── KPI CARDS ── */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {KPI_CARDS.map(({ key, label, icon: Icon, color, bg }) => (
                <div
                  key={key}
                  className="flex flex-col gap-2 p-4 rounded-2xl border border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-[#111827]"
                >
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${bg}`}>
                    <Icon className={`w-4.5 h-4.5 ${color}`} />
                  </div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {(data?.[key] ?? 0).toLocaleString()}
                  </p>
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* ── PER-INSURER BREAKDOWN ── */}
              <div className="rounded-2xl border border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-[#111827] p-4 flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-[#4F46E5] dark:text-indigo-400" />
                  <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">Rules by Insurer</h2>
                </div>
                {!data?.insurer_breakdown || data.insurer_breakdown.length === 0 ? (
                  <p className="text-xs text-slate-400 dark:text-slate-600">No data yet — upload a grid to get started.</p>
                ) : (
                  <div className="flex flex-col gap-2.5">
                    {data.insurer_breakdown.map(({ insurer, count }) => (
                      <div key={insurer} className="flex items-center gap-3">
                        <span className="text-xs font-medium text-slate-600 dark:text-slate-300 w-32 truncate flex-shrink-0" title={insurer}>
                          {insurer}
                        </span>
                        <div className="flex-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[#4F46E5] dark:bg-indigo-500"
                            style={{ width: `${(count / maxInsurerCount) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 w-14 text-right flex-shrink-0">
                          {count.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* ── RECENT UPLOADS ── */}
              <div className="rounded-2xl border border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-[#111827] p-4 flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-[#4F46E5] dark:text-indigo-400" />
                  <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">Recent Uploads</h2>
                </div>
                {!data?.recent_uploads || data.recent_uploads.length === 0 ? (
                  <p className="text-xs text-slate-400 dark:text-slate-600">No uploads yet.</p>
                ) : (
                  <div className="flex flex-col divide-y divide-[#E5E7EB]/70 dark:divide-slate-800/60">
                    {data.recent_uploads.map(u => (
                      <div key={u.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate" title={u.filename}>
                            {u.filename}
                          </p>
                          <p className="text-[11px] text-slate-400 dark:text-slate-500">
                            {u.company || 'Unknown Insurer'} · {u.total_records.toLocaleString()} rules
                          </p>
                        </div>
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold flex-shrink-0 ${
                            u.status === 'COMPLETED'
                              ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                              : u.status === 'FAILED'
                              ? 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400'
                              : 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400'
                          }`}
                        >
                          {u.status === 'COMPLETED' && <CheckCircle className="w-3 h-3" />}
                          {u.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

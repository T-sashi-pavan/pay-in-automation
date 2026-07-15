import React, { useEffect, useMemo, useState } from 'react';
import {
  X, RefreshCw, FileText, CheckCircle2, Clock, AlertCircle, Trash2, Search, ArrowUpDown,
} from 'lucide-react';
import type { UploadHistory } from '../types';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  uploads: UploadHistory[];
  selectedUploadId: number | null;
  onSelectUpload: (id: number) => void;
  onDeleteUpload: (id: number) => void;
  onRenameUpload: (id: number, filename: string) => void;
  isLoading: boolean;
  onRefresh: () => void;
}

type SortMode = 'recent' | 'oldest' | 'insurer';

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  uploads,
  selectedUploadId,
  onSelectUpload,
  onDeleteUpload,
  onRenameUpload,
  isLoading,
  onRefresh,
}) => {
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('recent');

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  const handleSelectAndClose = (id: number) => {
    onSelectUpload(id);
    onClose();
  };

  const visibleUploads = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    let list = uploads;
    if (q) {
      list = list.filter(u =>
        u.filename?.toLowerCase().includes(q) || u.company?.toLowerCase().includes(q)
      );
    }
    const sorted = [...list];
    if (sortMode === 'recent') {
      sorted.sort((a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime());
    } else if (sortMode === 'oldest') {
      sorted.sort((a, b) => new Date(a.uploaded_at).getTime() - new Date(b.uploaded_at).getTime());
    } else {
      sorted.sort((a, b) => (a.company || '').localeCompare(b.company || ''));
    }
    return sorted;
  }, [uploads, searchQuery, sortMode]);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px] transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      />

      {/* Drawer Panel */}
      <div
        className={`fixed left-0 top-0 bottom-0 z-50 w-80 bg-white dark:bg-slate-900 border-r border-[#E5E7EB] dark:border-slate-800 shadow-xl flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 h-14 border-b border-[#E5E7EB] dark:border-slate-800 flex-shrink-0">
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Upload History</p>
            <p className="text-xs text-slate-400 dark:text-slate-500">{uploads.length} file{uploads.length !== 1 ? 's' : ''} uploaded</p>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onRefresh}
              title="Refresh"
              className="p-1.5 rounded-lg text-slate-400 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search + Sort */}
        <div className="px-4 py-3 border-b border-[#E5E7EB] dark:border-slate-800 flex-shrink-0 flex flex-col gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search uploads..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-[#E5E7EB] dark:border-slate-700 text-slate-700 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:border-[#4F46E5]/60 focus:ring-1 focus:ring-[#4F46E5]/20 text-xs transition-colors"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <ArrowUpDown className="w-3 h-3 text-slate-400 dark:text-slate-500 flex-shrink-0" />
            {([
              { key: 'recent', label: 'Recent' },
              { key: 'oldest', label: 'Oldest' },
              { key: 'insurer', label: 'Insurer' },
            ] as const).map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setSortMode(key)}
                className={`px-2 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                  sortMode === key
                    ? 'bg-[#4F46E5]/10 text-[#4F46E5] dark:text-indigo-300'
                    : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Scrollable History List */}
        <div className="flex-1 overflow-y-auto p-2">
          {isLoading ? (
            <div className="flex flex-col gap-2 p-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800/40 animate-pulse" />
              ))}
            </div>
          ) : visibleUploads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 px-4 text-center">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                <FileText className="w-6 h-6 text-slate-400 dark:text-slate-600" />
              </div>
              <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
                {uploads.length === 0 ? 'No uploads yet' : 'No uploads match your search'}
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-600 leading-relaxed">
                {uploads.length === 0
                  ? 'Upload an insurer commission grid to start extracting rules.'
                  : 'Try a different search term.'}
              </p>
            </div>
          ) : (
            visibleUploads.map((u) => {
              const isSelected = u.id === selectedUploadId;
              const d = new Date(u.uploaded_at);
              const dateStr = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
              const timeStr = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });

              return (
                <div
                  key={u.id}
                  onClick={() => handleSelectAndClose(u.id)}
                  className={`group relative flex items-start gap-3 px-3.5 py-3.5 rounded-xl cursor-pointer transition-colors duration-150 border mb-1 ${
                    isSelected
                      ? 'bg-[#4F46E5]/10 border-[#4F46E5]/30'
                      : 'border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:border-slate-200 dark:hover:border-slate-700/30'
                  }`}
                >
                  <div className="mt-0.5 flex-shrink-0">
                    {u.status === 'COMPLETED' && <CheckCircle2 className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />}
                    {u.status === 'PROCESSING' && <Clock className="w-4 h-4 text-amber-500 dark:text-amber-400 animate-pulse" />}
                    {u.status === 'FAILED' && <AlertCircle className="w-4 h-4 text-red-500 dark:text-red-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-bold uppercase tracking-wide truncate ${isSelected ? 'text-[#4F46E5] dark:text-indigo-300' : 'text-slate-700 dark:text-slate-300'}`}>
                      {u.company || 'N/A'}
                    </p>
                    {editingId === u.id ? (
                      <div className="flex items-center gap-1.5 mt-1" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="flex-1 px-2 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:border-[#4F46E5]"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              if (editName.trim()) {
                                onRenameUpload(u.id, editName.trim());
                                setEditingId(null);
                              }
                            } else if (e.key === 'Escape') {
                              setEditingId(null);
                            }
                          }}
                        />
                        <button
                          type="button"
                          onClick={() => {
                            if (editName.trim()) {
                              onRenameUpload(u.id, editName.trim());
                              setEditingId(null);
                            }
                          }}
                          className="p-1 rounded hover:bg-emerald-50 dark:hover:bg-emerald-500/10 text-emerald-600 cursor-pointer"
                          title="Save"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-500/10 text-red-600 cursor-pointer"
                          title="Cancel"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 dark:text-slate-500 truncate mt-0.5">{u.filename}</p>
                    )}
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs text-slate-400 dark:text-slate-600">{dateStr}, {timeStr}</span>
                      {u.total_records > 0 && (
                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded-md ${
                          isSelected ? 'bg-[#4F46E5]/20 text-[#4F46E5] dark:text-indigo-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                        }`}>
                          {u.total_records.toLocaleString()} rules
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Action buttons (Rename & Delete) — visible on hover */}
                  {editingId !== u.id && (
                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 flex-shrink-0 mt-0.5">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingId(u.id);
                          setEditName(u.filename || '');
                        }}
                        className="p-1.5 rounded-lg text-slate-400 dark:text-slate-600 hover:text-[#4F46E5] dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer"
                        title="Rename file"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(u.id); }}
                        className="p-1.5 rounded-lg text-slate-400 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all cursor-pointer"
                        title="Delete upload"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Delete confirmation modal */}
      {deleteConfirmId !== null && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-700 rounded-2xl p-6 w-80 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-xl bg-red-50 dark:bg-red-500/10">
                <AlertCircle className="w-5 h-5 text-red-500 dark:text-red-400" />
              </div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Confirm Deletion</h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-5">
              This will permanently delete the upload and all extracted rules. This action cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => setDeleteConfirmId(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => { onDeleteUpload(deleteConfirmId!); setDeleteConfirmId(null); }}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-red-600 hover:bg-red-500 text-white transition-colors cursor-pointer"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

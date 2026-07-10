import React, { useEffect, useState } from 'react';
import { X, RefreshCw, AlertCircle } from 'lucide-react';
import type { MasterListItem } from '../types';

export type EditFieldType = 'text' | 'number' | 'date';

interface EditFieldModalProps {
  isOpen: boolean;
  label: string;
  value: string | number | null;
  fieldType: EditFieldType;
  suggestions?: MasterListItem[];
  onSave: (value: string) => void | Promise<void>;
  onClose: () => void;
}

export const EditFieldModal: React.FC<EditFieldModalProps> = ({
  isOpen, label, value, fieldType, suggestions, onSave, onClose,
}) => {
  const [draft, setDraft] = useState(value !== null && value !== undefined ? String(value) : '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setDraft(value !== null && value !== undefined ? String(value) : '');
      setError(null);
    }
  }, [isOpen, value]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape' && !saving) onClose(); };
    if (isOpen) document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, saving, onClose]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(draft);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Unable to update record.');
    } finally {
      setSaving(false);
    }
  };

  const datalistId = suggestions && suggestions.length > 0 ? `edit-field-suggestions-${label.replace(/\s+/g, '-')}` : undefined;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-700 rounded-2xl w-full max-w-sm shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E7EB] dark:border-slate-800">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Edit {label}</h3>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4 flex flex-col gap-2">
          <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Current Value
          </label>
          <input
            type={fieldType === 'number' ? 'number' : fieldType === 'date' ? 'date' : 'text'}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !saving) handleSave(); }}
            list={datalistId}
            autoFocus
            step={fieldType === 'number' ? 'any' : undefined}
            className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-[#E5E7EB] dark:border-slate-700 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:border-[#4F46E5]/60 focus:ring-1 focus:ring-[#4F46E5]/20 transition-colors"
          />
          {datalistId && (
            <datalist id={datalistId}>
              {suggestions!.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
            </datalist>
          )}
          {error && (
            <p className="flex items-center gap-1.5 text-xs font-medium text-red-600 dark:text-red-400">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> {error}
            </p>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-[#E5E7EB] dark:border-slate-800">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-[#4F46E5] hover:bg-[#4338CA] text-white transition-colors cursor-pointer disabled:opacity-60"
          >
            {saving && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

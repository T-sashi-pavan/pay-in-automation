import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Search, X, Check } from 'lucide-react';

export interface FilterOption {
  value: string;
  count: number;
}

interface MultiSelectFilterProps {
  title: string;
  options: FilterOption[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  isSingleSelect?: boolean;
}

export const MultiSelectFilter: React.FC<MultiSelectFilterProps> = ({
  title,
  options,
  selectedValues,
  onChange,
  isSingleSelect = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Handle clicking outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggleOption = (value: string) => {
    if (isSingleSelect) {
      onChange(selectedValues.includes(value) ? [] : [value]);
    } else {
      if (selectedValues.includes(value)) {
        onChange(selectedValues.filter((v) => v !== value));
      } else {
        onChange([...selectedValues, value]);
      }
    }
  };

  const handleSelectAll = () => {
    if (isSingleSelect) return;
    onChange(filteredOptions.map(o => o.value));
  };

  const handleClear = () => onChange([]);

  const filteredOptions = options.filter((opt) =>
    opt.value.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalCount = options.reduce((sum, o) => sum + o.count, 0);

  return (
    <div className="relative inline-block text-left w-full" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center justify-between gap-1.5 px-3 py-2 rounded-lg border text-xs font-semibold transition-colors duration-150 cursor-pointer w-full text-left ${
          selectedValues.length > 0
            ? 'bg-[#4F46E5]/10 text-[#4F46E5] dark:text-indigo-400 border-[#4F46E5]/30 hover:bg-[#4F46E5]/15'
            : 'bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 border-[#E5E7EB] dark:border-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-800/90 hover:text-slate-900 dark:hover:text-slate-100'
        }`}
      >
        <span className="truncate flex-1 min-w-0">
          {selectedValues.length > 0
            ? (
              <span className="flex items-center gap-1.5">
                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-[#4F46E5] text-white text-3xs font-black flex-shrink-0">
                  {selectedValues.length}
                </span>
                <span className="truncate">{title}</span>
              </span>
            )
            : (
              <span className="flex items-center justify-between w-full gap-1">
                <span>{title}</span>
                {options.length > 0 && (
                  <span className="text-slate-400 dark:text-slate-500 text-3xs font-medium ml-auto mr-1">{options.length}</span>
                )}
              </span>
            )
          }
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 dark:text-slate-500 flex-shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-1.5 w-64 rounded-xl bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-700/60 shadow-lg z-[100] p-2 flex flex-col gap-2 animate-in fade-in slide-in-from-top-1 duration-150">
          {/* Header with total count */}
          <div className="flex items-center justify-between px-1 pb-1 border-b border-[#E5E7EB] dark:border-slate-800">
            <span className="text-3xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{title}</span>
            <span className="text-3xs text-slate-400 dark:text-slate-500">{totalCount.toLocaleString()} total rows</span>
          </div>

          {/* Search Box */}
          <div className="relative flex items-center">
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
            <input
              type="text"
              placeholder="Search options..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-7 py-1.5 rounded-md bg-slate-50 dark:bg-slate-950 border border-[#E5E7EB] dark:border-slate-800 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-[#4F46E5] focus:ring-1 focus:ring-[#4F46E5]/20"
              autoFocus
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Action Buttons */}
          {!isSingleSelect && (
            <div className="flex items-center justify-between border-b border-[#E5E7EB] dark:border-slate-800 pb-1.5 px-1 text-3xs font-bold text-slate-500 dark:text-slate-400">
              <button
                type="button"
                onClick={handleSelectAll}
                className="hover:text-[#4F46E5] dark:hover:text-indigo-400 transition-colors cursor-pointer"
              >
                Select All ({filteredOptions.length})
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="hover:text-red-500 dark:hover:text-red-400 transition-colors cursor-pointer"
              >
                Clear
              </button>
            </div>
          )}

          {/* Options List */}
          <div className="max-h-52 overflow-y-auto flex flex-col gap-0.5 pr-0.5">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt) => {
                const isSelected = selectedValues.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleToggleOption(opt.value)}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800/60 text-left text-xs text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors cursor-pointer w-full group"
                  >
                    <div
                      className={`w-3.5 h-3.5 rounded flex items-center justify-center border transition-colors duration-150 flex-shrink-0 ${
                        isSelected
                          ? 'bg-[#4F46E5] border-[#4F46E5] text-white'
                          : 'border-[#E5E7EB] dark:border-slate-700 bg-white dark:bg-slate-950 group-hover:border-slate-300 dark:group-hover:border-slate-500'
                      }`}
                    >
                      {isSelected && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                    </div>
                    <span className="truncate flex-1 text-left">{opt.value}</span>
                    <span className={`ml-auto text-3xs font-bold px-1.5 py-0.5 rounded-full flex-shrink-0 ${
                      isSelected
                        ? 'bg-[#4F46E5]/20 text-[#4F46E5] dark:text-indigo-400'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 group-hover:text-slate-500 dark:group-hover:text-slate-400'
                    }`}>
                      {opt.count.toLocaleString()}
                    </span>
                  </button>
                );
              })
            ) : (
              <div className="text-center py-5 text-xs text-slate-400 dark:text-slate-500">
                {options.length === 0 ? 'No data in database' : 'No options match search.'}
              </div>
            )}
          </div>

          {/* Footer Apply/Close */}
          <div className="flex items-center justify-between gap-1.5 border-t border-[#E5E7EB] dark:border-slate-800 pt-1.5 px-0.5">
            {selectedValues.length > 0 && (
              <span className="text-3xs text-[#4F46E5] dark:text-indigo-400 font-medium">{selectedValues.length} selected</span>
            )}
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="ml-auto px-3 py-1 rounded bg-[#4F46E5] hover:bg-[#4338CA] text-white text-3xs font-bold transition-colors cursor-pointer"
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

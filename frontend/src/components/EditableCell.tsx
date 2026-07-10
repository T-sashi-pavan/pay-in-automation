import React, { useState } from 'react';
import { Pencil } from 'lucide-react';
import { EditFieldModal, type EditFieldType } from './EditFieldModal';
import type { MasterListItem } from '../types';

interface EditableCellProps {
  label: string;
  value: string | number | null;
  displayValue?: React.ReactNode;
  fieldType?: EditFieldType;
  suggestions?: MasterListItem[];
  onSave: (value: string) => void | Promise<void>;
  disabled?: boolean;
  className?: string;
}

export const EditableCell: React.FC<EditableCellProps> = ({
  label, value, displayValue, fieldType = 'text', suggestions, onSave, disabled, className,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div
        className={`group/cell relative flex items-center gap-1.5 -mx-1 px-1 rounded ${disabled ? '' : 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/60'} ${className || ''}`}
        onClick={() => { if (!disabled) setIsOpen(true); }}
      >
        <span className="truncate">{displayValue ?? (value ?? <span className="text-slate-300 dark:text-slate-700">N/A</span>)}</span>
        {!disabled && (
          <Pencil className="w-3 h-3 flex-shrink-0 text-slate-400 dark:text-slate-500 opacity-0 group-hover/cell:opacity-100 transition-opacity" />
        )}
      </div>
      <EditFieldModal
        isOpen={isOpen}
        label={label}
        value={value}
        fieldType={fieldType}
        suggestions={suggestions}
        onSave={onSave}
        onClose={() => setIsOpen(false)}
      />
    </>
  );
};

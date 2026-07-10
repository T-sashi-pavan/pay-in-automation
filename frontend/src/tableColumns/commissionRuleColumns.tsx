import { ChevronRight, ChevronDown, CheckCircle, AlertTriangle } from 'lucide-react';
import type { ColumnDef } from '@tanstack/react-table';
import type { EditableRuleField, EditableSlabField, MasterListItem } from '../types';
import { EditableCell } from '../components/EditableCell';
import type { EditFieldType } from '../components/EditFieldModal';

export interface ColumnFactoryOptions {
  expandedRows: Record<string, boolean>;
  toggleRowExpanded: (rowId: string) => void;
  onEditRule: (ruleId: number, field: EditableRuleField, value: string) => void;
  /** Slab-tab rate/boundary cells live on SlabDetail, not CommissionRule — routed separately. */
  onEditSlab: (slabId: number, field: EditableSlabField, value: string) => void;
  stateSuggestions?: MasterListItem[];
  productSuggestions?: MasterListItem[];
  /** CustomiseData shows these two extra columns; Dashboard doesn't. */
  includeValidationStatus?: boolean;
  includeSourceFile?: boolean;
}

const expanderColumn = (opts: ColumnFactoryOptions): ColumnDef<any> => ({
  id: 'expander',
  enableSorting: false,
  enableHiding: false,
  header: () => null,
  cell: ({ row }) => (
    <button
      type="button"
      onClick={() => opts.toggleRowExpanded(row.id)}
      className="flex items-center justify-center w-7 h-7 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
    >
      {opts.expandedRows[row.id] ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
    </button>
  ),
});

function textCol(
  accessorKey: string,
  header: string,
  field: EditableRuleField,
  opts: ColumnFactoryOptions,
  valueClassName = 'text-slate-500 dark:text-slate-400',
  labelKey?: string,
  suggestions?: MasterListItem[],
  fieldType: EditFieldType = 'text',
): ColumnDef<any> {
  return {
    accessorKey,
    header,
    cell: (info: any) => {
      const raw = (info.getValue() ?? null) as string | null;
      const label = labelKey ? ((info.row.original as any)[labelKey] as string | null) : null;
      return (
        <EditableCell
          label={header}
          value={raw}
          fieldType={fieldType}
          suggestions={suggestions}
          displayValue={<span className={valueClassName}>{(label ?? raw) || 'N/A'}</span>}
          onSave={(v) => opts.onEditRule(info.row.original.id, field, v)}
        />
      );
    },
  };
}

/** Editable cell for a value that lives on the SlabDetail row (Slab tab only), keyed by `slab_id` on the flattened row. */
function slabTextCol(accessorKey: string, header: string, field: EditableSlabField, opts: ColumnFactoryOptions, valueClassName = 'text-slate-700 dark:text-slate-300', fieldType: EditFieldType = 'text'): ColumnDef<any> {
  return {
    accessorKey,
    header,
    cell: (info: any) => {
      const raw = (info.getValue() ?? null) as string | number | null;
      const slabId = info.row.original.slab_id as number | undefined;
      return (
        <EditableCell
          label={header}
          value={raw}
          fieldType={fieldType}
          disabled={!slabId}
          displayValue={<span className={valueClassName}>{raw !== null && raw !== undefined && raw !== '' ? String(raw) : 'N/A'}</span>}
          onSave={(v) => { if (slabId) opts.onEditSlab(slabId, field, v); }}
        />
      );
    },
  };
}

function slabRateCol(accessorKey: string, header: string, field: EditableSlabField, opts: ColumnFactoryOptions, direction: 'in' | 'out'): ColumnDef<any> {
  const colorClass = direction === 'in' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400';
  return {
    accessorKey,
    header,
    cell: (info: any) => {
      const raw = (info.getValue() ?? null) as number | null;
      const slabId = info.row.original.slab_id as number | undefined;
      const display = <span className={`${colorClass} font-mono`}>{raw !== null ? `${raw}%` : '-'}</span>;
      // Pay-Out is always 80% of Pay-In, computed server-side — not independently editable.
      if (direction === 'out') return display;
      return (
        <EditableCell
          label={header}
          value={raw}
          fieldType="number"
          disabled={!slabId}
          displayValue={display}
          onSave={(v) => { if (slabId) opts.onEditSlab(slabId, field, v); }}
        />
      );
    },
  };
}

/** Slab_from/slab_to are premium/volume boundaries, not percentages — plain numeric formatting. */
function slabBoundCol(accessorKey: 'slab_from' | 'slab_to', header: string, opts: ColumnFactoryOptions, infinitySymbol: string): ColumnDef<any> {
  return {
    accessorKey,
    header,
    cell: (info: any) => {
      const raw = (info.getValue() ?? null) as number | null;
      const slabId = info.row.original.slab_id as number | undefined;
      return (
        <EditableCell
          label={header}
          value={raw}
          fieldType="number"
          disabled={!slabId}
          displayValue={<span className="text-slate-700 dark:text-slate-300 font-mono font-bold">{raw !== null ? Number(raw).toLocaleString() : infinitySymbol}</span>}
          onSave={(v) => { if (slabId) opts.onEditSlab(slabId, accessorKey, v); }}
        />
      );
    },
  };
}

function rateCol(accessorKey: string, header: string, field: EditableRuleField, opts: ColumnFactoryOptions, direction: 'in' | 'out'): ColumnDef<any> {
  const colorClass = direction === 'in' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400';
  return {
    accessorKey,
    header,
    cell: (info: any) => {
      const raw = (info.getValue() ?? null) as number | null;
      const display = <span className={`${colorClass} font-mono`}>{raw !== null ? `${raw}%` : '-'}</span>;
      // Pay-Out is always 80% of Pay-In, computed server-side — not independently editable.
      if (direction === 'out') return display;
      return (
        <EditableCell
          label={header}
          value={raw}
          fieldType="number"
          displayValue={display}
          onSave={(v) => opts.onEditRule(info.row.original.id, field, v)}
        />
      );
    },
  };
}

const vehicleAgeColumn: ColumnDef<any> = {
  id: 'vehicle_age',
  header: 'Vehicle Age',
  enableSorting: false,
  cell: ({ row }) => {
    const from = row.original.vehicle_age_from;
    const to = row.original.vehicle_age_to;
    if (from === null && to === null) return <span className="text-slate-400 dark:text-slate-600">N/A</span>;
    if (from !== null && to === null) return <span className="text-slate-500 dark:text-slate-400">&gt; {from} yrs</span>;
    if (from === null && to !== null) return <span className="text-slate-500 dark:text-slate-400">Upto {to} yrs</span>;
    return <span className="text-slate-500 dark:text-slate-400">{from} – {to} yrs</span>;
  },
};

const slabConfigColumn: ColumnDef<any> = {
  accessorKey: 'slab_configuration',
  header: 'Slab Config',
  cell: ({ row }) => (
    <span className="text-xs font-semibold text-slate-500 dark:text-slate-500">
      {row.original.slab_configuration ? 'Yes' : 'No'}
    </span>
  ),
};

/** Toggling this triggers the backend's NON_SLAB<->SLAB cascade (moves rates to/from slab_details). */
function commissionTypeColumn(opts: ColumnFactoryOptions): ColumnDef<any> {
  return {
    accessorKey: 'commission_type',
    header: 'Commission Type',
    cell: (info) => {
      const raw = info.getValue() as string;
      return (
        <EditableCell
          label="Commission Type (SLAB or NON_SLAB)"
          value={raw}
          displayValue={
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              raw === 'SLAB'
                ? 'bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400'
                : 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400'
            }`}>
              {raw}
            </span>
          }
          onSave={(v) => opts.onEditRule(info.row.original.id, 'commission_type', v.trim().toUpperCase())}
        />
      );
    },
  };
}

const validationStatusColumn: ColumnDef<any> = {
  accessorKey: 'validation_status',
  header: 'Status',
  cell: ({ row }) => {
    const status = row.original.validation_status;
    return status === 'VALID' ? (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
        <CheckCircle className="w-3 h-3" />Valid
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20">
        <AlertTriangle className="w-3 h-3" />Warning
      </span>
    );
  },
};

const sourceFileColumn: ColumnDef<any> = {
  accessorKey: 'upload_filename',
  header: 'Source File',
  cell: (info) => (
    <span className="text-[#4F46E5] dark:text-indigo-400 max-w-[140px] truncate inline-block font-medium text-xs" title={info.getValue() as string}>
      {(info.getValue() as string) || 'N/A'}
    </span>
  ),
};

export function createNonSlabColumns(opts: ColumnFactoryOptions): ColumnDef<any>[] {
  const cols: ColumnDef<any>[] = [
    expanderColumn(opts),
    textCol('lob', 'LOB', 'lob', opts, 'font-semibold text-slate-700 dark:text-slate-300'),
    textCol('file_type', 'File Type', 'file_type', opts),
    textCol('insurance_company', 'Insurer', 'insurance_company', opts, 'font-bold text-slate-900 dark:text-slate-100'),
    textCol('product', 'Product', 'product', opts, 'text-slate-700 dark:text-slate-300', 'product_label', opts.productSuggestions),
    textCol('policy_type', 'Policy Type', 'policy_type', opts),
    textCol('plan_type', 'Plan Type', 'plan_type', opts),
    textCol('sub_product', 'Sub Product', 'sub_product', opts),
    textCol('class', 'Class', 'class', opts),
    textCol('sub_class', 'Sub Class', 'sub_class', opts, 'text-slate-500 dark:text-slate-400 font-mono'),
    vehicleAgeColumn,
    textCol('state', 'State', 'state', opts, 'text-slate-700 dark:text-slate-300 font-medium', 'state_label', opts.stateSuggestions),
    textCol('effective_date', 'Effective Date', 'effective_date', opts, 'text-slate-500 text-xs font-mono', undefined, undefined, 'date'),
    rateCol('payin_od', 'Pay-In OD', 'payin_od', opts, 'in'),
    rateCol('payout_od', 'Pay-Out OD', 'payout_od', opts, 'out'),
    rateCol('payin_tp', 'Pay-In TP', 'payin_tp', opts, 'in'),
    rateCol('payout_tp', 'Pay-Out TP', 'payout_tp', opts, 'out'),
    rateCol('payin_net', 'Pay-In Net', 'payin_net', opts, 'in'),
    rateCol('payout_net', 'Pay-Out Net', 'payout_net', opts, 'out'),
    rateCol('payin_reward', 'Pay-In Reward', 'payin_reward', opts, 'in'),
    rateCol('payout_reward', 'Pay-Out Reward', 'payout_reward', opts, 'out'),
    rateCol('payin_scheme', 'Pay-In Scheme', 'payin_scheme', opts, 'in'),
    rateCol('payout_scheme', 'Pay-Out Scheme', 'payout_scheme', opts, 'out'),
    commissionTypeColumn(opts),
    slabConfigColumn,
    textCol('remarks', 'Remarks', 'remarks', opts, 'text-slate-500 dark:text-slate-500 text-xs'),
  ];
  if (opts.includeValidationStatus) cols.push(validationStatusColumn);
  if (opts.includeSourceFile) cols.push(sourceFileColumn);
  return cols;
}

export function createSlabColumns(opts: ColumnFactoryOptions): ColumnDef<any>[] {
  const cols: ColumnDef<any>[] = [
    expanderColumn(opts),
    textCol('lob', 'LOB', 'lob', opts, 'font-semibold text-slate-700 dark:text-slate-300'),
    textCol('file_type', 'File Type', 'file_type', opts),
    textCol('insurance_company', 'Insurer', 'insurance_company', opts, 'font-bold text-slate-900 dark:text-slate-100'),
    textCol('product', 'Product', 'product', opts, 'text-slate-700 dark:text-slate-300', 'product_label', opts.productSuggestions),
    textCol('policy_type', 'Policy Type', 'policy_type', opts),
    textCol('plan_type', 'Plan Type', 'plan_type', opts),
    textCol('sub_product', 'Sub Product', 'sub_product', opts),
    textCol('class', 'Class', 'class', opts),
    textCol('sub_class', 'Sub Class', 'sub_class', opts, 'text-slate-500 dark:text-slate-400 font-mono'),
    vehicleAgeColumn,
    textCol('state', 'State', 'state', opts, 'text-slate-700 dark:text-slate-300 font-medium', 'state_label', opts.stateSuggestions),
    textCol('effective_date', 'Effective Date', 'effective_date', opts, 'text-slate-500 text-xs font-mono', undefined, undefined, 'date'),
    slabTextCol('payin_type', 'Pay-In Type', 'payin_type', opts, 'font-semibold text-[#4F46E5] dark:text-indigo-300'),
    slabTextCol('premium_type', 'Premium Type', 'premium_type', opts),
    slabBoundCol('slab_from', 'Slab From', opts, '-'),
    slabBoundCol('slab_to', 'Slab Upto', opts, '∞'),
    slabRateCol('payin_od', 'Pay-In OD', 'payin_od', opts, 'in'),
    slabRateCol('payout_od', 'Pay-Out OD', 'payout_od', opts, 'out'),
    slabRateCol('payin_tp', 'Pay-In TP', 'payin_tp', opts, 'in'),
    slabRateCol('payout_tp', 'Pay-Out TP', 'payout_tp', opts, 'out'),
    slabRateCol('payin_net', 'Pay-In Net', 'payin_net', opts, 'in'),
    slabRateCol('payout_net', 'Pay-Out Net', 'payout_net', opts, 'out'),
    commissionTypeColumn(opts),
    textCol('remarks', 'Remarks', 'remarks', opts, 'text-slate-500 dark:text-slate-500 text-xs'),
  ];
  if (opts.includeSourceFile) cols.push(sourceFileColumn);
  return cols;
}

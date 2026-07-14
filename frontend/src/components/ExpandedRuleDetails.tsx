import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import type { CommissionRule, EditableSlabField } from '../types';
import { EditableCell } from './EditableCell';
import {
  Building2,
  Percent,
  FileSpreadsheet,
  Layers,
  Info,
  AlertTriangle,
  ClipboardList,
  Code,
  ChevronDown,
  ChevronRight,
  X,
} from 'lucide-react';

interface ExpandedRuleDetailsProps {
  rule: CommissionRule;
  colCount: number;
  /** Tier-level editing lives here now — the Slab tab shows one row per rule, not one per tier. */
  onEditSlab?: (slabId: number, field: EditableSlabField, value: string) => void;
  /** Closes the panel — required now that it renders as a modal overlay instead of an inline expanded row. */
  onClose: () => void;
}

export const ExpandedRuleDetails: React.FC<ExpandedRuleDetailsProps> = ({ rule, colCount: _colCount, onEditSlab, onClose }) => {
  const commissionType = rule.commissionType || rule.commission_type || 'NON_SLAB';
  const slabConfiguration = rule.slabConfiguration !== undefined ? rule.slabConfiguration : (rule.slab_configuration || false);

  // Default to whichever tab actually has data for this rule — a SLAB rule
  // used to always open on "Non-Slab Details" regardless of its own type.
  const [activeTab, setActiveTab] = useState<'non-slab' | 'slab'>(commissionType === 'SLAB' ? 'slab' : 'non-slab');
  const [showRawJson, setShowRawJson] = useState(false);

  const defaultedFields = rule._defaulted_fields || [];
  const isDefaulted = (field: string) => defaultedFields.includes(field);
  const DEFAULTED_TITLE = 'Default value — not extracted from the source file';

  const businessFields = [
    { label: 'LOB', value: rule.lob, field: 'lob' },
    { label: 'File Type', value: rule.file_type, field: 'file_type' },
    { label: 'Insurance Company', value: rule.insurance_company, field: 'insurance_company' },
    { label: 'Product', value: rule.product, field: 'product' },
    { label: 'Policy Type', value: rule.policy_type, field: 'policy_type' },
    { label: 'Plan Type', value: rule.plan_type, field: 'plan_type' },
    { label: 'Sub Product', value: rule.sub_product, field: 'sub_product' },
    { label: 'Class', value: rule.class, field: 'class' },
    { label: 'Sub Class', value: rule.sub_class, field: 'sub_class' },
    { label: 'Make', value: rule.make, field: 'make' },
    { label: 'Model', value: rule.model, field: 'model' },
    { label: 'Fuel Type', value: rule.fuel_type, field: 'fuel_type' },
    { label: 'Body Type', value: rule.body_type, field: 'body_type' },
    { label: 'Vehicle Age From', value: rule.vehicle_age_from !== null ? `${rule.vehicle_age_from} yrs` : null, field: 'vehicle_age_from' },
    { label: 'Vehicle Age To', value: rule.vehicle_age_to !== null ? `${rule.vehicle_age_to} yrs` : null, field: 'vehicle_age_to' },
    { label: 'CPA Status', value: rule.cpa_status, field: 'cpa_status' },
    { label: 'NCB Status', value: rule.ncb_status, field: 'ncb_status' },
    { label: 'Partner Type', value: rule.partner_type, field: 'partner_type' },
    { label: 'State', value: rule.state, field: 'state' },
    { label: 'Zone', value: rule.zone, field: 'zone' },
    { label: 'Source', value: rule.source, field: 'source' },
    { label: 'RTO', value: rule.rto, field: 'rto' },
    { label: 'Effective Date', value: rule.effective_date, field: 'effective_date' },
    { label: 'Remarks', value: rule.remarks, field: 'remarks' }
  ];

  const formatPercentage = (val: number | null) => {
    return val !== null && val !== undefined ? `${val}%` : '-';
  };

  const modal = (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      {/* Backdrop — fixed positioning means this panel is always centered on
          the actual viewport, completely independent of the table's own
          width/scroll state (the old sticky-in-table-cell approach was
          unreliable and still required shrinking the window in practice). */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-5xl max-h-[90vh] flex flex-col rounded-2xl border border-[#E5E7EB] dark:border-slate-800/80 bg-white dark:bg-slate-950 overflow-hidden shadow-2xl">

        {/* Tabs Navigation */}
        <div className="flex-shrink-0 flex items-center justify-between border-b border-[#E5E7EB] dark:border-slate-800/80 bg-slate-50 dark:bg-slate-900/30 px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="relative group inline-block">
              <button
                type="button"
                onClick={() => commissionType !== 'SLAB' && setActiveTab('non-slab')}
                disabled={commissionType === 'SLAB'}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors duration-150 ${
                  commissionType === 'SLAB'
                    ? 'bg-slate-50 dark:bg-slate-900/40 text-slate-300 dark:text-slate-600 border border-[#E5E7EB] dark:border-slate-900 cursor-not-allowed'
                    : activeTab === 'non-slab'
                    ? 'bg-[#4F46E5] text-white cursor-pointer'
                    : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700/80 text-slate-600 dark:text-slate-300 border border-[#E5E7EB] dark:border-slate-700/60 cursor-pointer'
                }`}
                title={commissionType === 'SLAB' ? 'This rule uses slab-based commission — no flat rates configured' : ''}
              >
                <ClipboardList className="w-3.5 h-3.5" />
                Non-Slab Details
              </button>

              {commissionType === 'SLAB' && (
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 scale-0 group-hover:scale-100 transition-all duration-100 origin-bottom bg-slate-900 dark:bg-slate-950 text-slate-300 dark:text-slate-400 text-[10px] py-1.5 px-3 rounded-lg border border-slate-800 whitespace-nowrap z-30 pointer-events-none shadow-lg">
                  This rule uses slab-based commission — no flat rates configured
                </div>
              )}
            </div>

            <div className="relative group inline-block">
              <button
                type="button"
                onClick={() => commissionType === 'SLAB' && setActiveTab('slab')}
                disabled={commissionType !== 'SLAB'}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors duration-150 ${
                  commissionType !== 'SLAB'
                    ? 'bg-slate-50 dark:bg-slate-900/40 text-slate-300 dark:text-slate-600 border border-[#E5E7EB] dark:border-slate-900 cursor-not-allowed'
                    : activeTab === 'slab'
                    ? 'bg-[#4F46E5] text-white cursor-pointer'
                    : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700/80 text-slate-600 dark:text-slate-300 border border-[#E5E7EB] dark:border-slate-700/60 cursor-pointer'
                }`}
                title={commissionType !== 'SLAB' ? 'No slab configuration available' : ''}
              >
                <Layers className="w-3.5 h-3.5" />
                Slab Details
              </button>

              {commissionType !== 'SLAB' && (
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 scale-0 group-hover:scale-100 transition-all duration-100 origin-bottom bg-slate-900 dark:bg-slate-950 text-slate-300 dark:text-slate-400 text-[10px] py-1.5 px-3 rounded-lg border border-slate-800 whitespace-nowrap z-30 pointer-events-none shadow-lg">
                  No slab configuration available
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-extrabold px-3 py-1 rounded-full uppercase tracking-widest ${
              commissionType === 'SLAB'
                ? 'bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-500/25'
                : 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500/25'
            }`}>
              {commissionType === 'SLAB' ? 'Slab' : 'Non-Slab'} Structure
            </span>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 dark:text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto">

            {/* NON-SLAB TAB CONTENT */}
            {activeTab === 'non-slab' && (
              <div className="space-y-6">
                
                {/* Business Details Grid */}
                <div>
                  <h4 className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-4">
                    <Building2 className="w-3.5 h-3.5 text-[#4F46E5] dark:text-indigo-400" />
                    Business Details
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {businessFields.map((f, i) => {
                      const defaulted = isDefaulted(f.field);
                      return (
                        <div key={i} className="bg-slate-50 dark:bg-slate-900/20 border border-[#E5E7EB] dark:border-slate-900/60 rounded-xl p-3 flex flex-col justify-center">
                          <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">{f.label}</span>
                          <span
                            className={`text-xs font-semibold mt-1 truncate ${defaulted ? 'text-amber-600 dark:text-amber-400 italic' : 'text-slate-800 dark:text-slate-200'}`}
                            title={defaulted ? DEFAULTED_TITLE : (f.value?.toString() || '')}
                          >
                            {f.value !== null && f.value !== undefined && f.value !== '' ? String(f.value) : <span className="text-slate-300 dark:text-slate-700 italic">None</span>}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Commission Details Grid */}
                <div className="border-t border-[#E5E7EB] dark:border-slate-900 pt-6">
                  <h4 className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-4">
                    <Percent className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
                    Commission Details
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
                    {[
                      { label: 'Pay-In OD', val: rule.payin_od },
                      { label: 'Pay-Out OD', val: rule.payout_od },
                      { label: 'Pay-In TP', val: rule.payin_tp },
                      { label: 'Pay-Out TP', val: rule.payout_tp },
                      { label: 'Pay-In Net', val: rule.payin_net },
                      { label: 'Pay-Out Net', val: rule.payout_net },
                      { label: 'Pay-In Reward', val: rule.payin_reward },
                      { label: 'Pay-Out Reward', val: rule.payout_reward },
                      { label: 'Pay-In Scheme', val: rule.payin_scheme },
                      { label: 'Pay-Out Scheme', val: rule.payout_scheme }
                    ].map((c, i) => (
                      <div key={i} className="bg-slate-50 dark:bg-slate-900/30 border border-[#E5E7EB] dark:border-slate-900/60 rounded-xl p-3 flex flex-col items-center justify-center text-center">
                        <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">{c.label}</span>
                        <span className={`text-sm font-black mt-1 ${i % 2 === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                          {formatPercentage(c.val)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Slab Configuration Alert */}
                <div className="border-t border-[#E5E7EB] dark:border-slate-900 pt-6 flex items-center gap-3 text-xs bg-slate-50 dark:bg-slate-900/20 border border-[#E5E7EB] dark:border-slate-900 p-4 rounded-xl">
                  <Info className="w-4 h-4 text-[#4F46E5] dark:text-indigo-400 flex-shrink-0" />
                  <div className="text-slate-500 dark:text-slate-400">
                    <span className="font-bold text-slate-700 dark:text-slate-300">Slab Configuration:</span>{' '}
                    {slabConfiguration ? 'Enabled for this record. Use the Slab Details tab above to view individual slab structures.' : 'Disabled. This rule represents a standard non-slab commission schedule.'}
                  </div>
                </div>

              </div>
            )}

            {/* SLAB TAB CONTENT */}
            {activeTab === 'slab' && (
              <div className="space-y-6">
                
                {/* Business Details Grid */}
                <div>
                  <h4 className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-4">
                    <Building2 className="w-3.5 h-3.5 text-[#4F46E5] dark:text-indigo-400" />
                    Business Details
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {businessFields.map((f, i) => {
                      const defaulted = isDefaulted(f.field);
                      return (
                        <div key={i} className="bg-slate-50 dark:bg-slate-900/20 border border-[#E5E7EB] dark:border-slate-900/60 rounded-xl p-3 flex flex-col justify-center">
                          <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">{f.label}</span>
                          <span
                            className={`text-xs font-semibold mt-1 truncate ${defaulted ? 'text-amber-600 dark:text-amber-400 italic' : 'text-slate-800 dark:text-slate-200'}`}
                            title={defaulted ? DEFAULTED_TITLE : (f.value?.toString() || '')}
                          >
                            {f.value !== null && f.value !== undefined && f.value !== '' ? String(f.value) : <span className="text-slate-300 dark:text-slate-700 italic">None</span>}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Slabs Table */}
                <div className="border-t border-[#E5E7EB] dark:border-slate-900 pt-6">
                  <h4 className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-4">
                    <FileSpreadsheet className="w-3.5 h-3.5 text-[#4F46E5] dark:text-indigo-400" />
                    Slab Table Configuration
                  </h4>
                  {slabConfiguration && rule.slabs?.length > 0 ? (
                    <div className="overflow-x-auto rounded-xl border border-[#E5E7EB] dark:border-slate-800 bg-slate-50 dark:bg-slate-900/10">
                      <table className="min-w-full divide-y divide-[#E5E7EB] dark:divide-slate-800">
                        <thead className="bg-slate-100 dark:bg-slate-900/40">
                          <tr>
                            <th className="px-4 py-2.5 text-left text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider whitespace-nowrap">Tier</th>
                            {['Pay-In Type', 'Premium Type', 'Pay-In Slab From', 'Pay-In Slab Upto', 'Pay-In OD', 'Payout OD', 'Pay-In TP', 'Payout TP', 'Pay-In Net', 'Payout Net'].map(h => (
                              <th key={h} className="px-4 py-2.5 text-left text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E5E7EB]/70 dark:divide-slate-800/40">
                          {rule.slabs.map((slab, tierIdx) => {
                            const editSlab = (field: EditableSlabField, value: string) => onEditSlab?.(slab.id, field, value);
                            return (
                              <tr key={slab.id} className="hover:bg-slate-100 dark:hover:bg-slate-900/20 transition-colors">
                                <td className="px-4 py-2.5">
                                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#4F46E5]/10 dark:bg-indigo-500/10 text-[#4F46E5] dark:text-indigo-300 text-xs font-extrabold">
                                    {tierIdx + 1}
                                  </span>
                                </td>
                                {(() => {
                                  const slabDefaulted = slab._defaulted_fields || [];
                                  const cellCls = (field: string, base: string) =>
                                    slabDefaulted.includes(field) ? 'text-amber-600 dark:text-amber-400 italic' : base;
                                  const cellTitle = (field: string) => slabDefaulted.includes(field) ? DEFAULTED_TITLE : undefined;
                                  return (
                                    <>
                                      <td className="px-4 py-2.5 text-xs font-bold text-[#4F46E5] dark:text-indigo-300">
                                        <EditableCell label="Pay-In Type" value={slab.payin_type} displayValue={<span className={cellCls('payin_type', '')} title={cellTitle('payin_type')}>{slab.payin_type || 'N/A'}</span>} onSave={(v) => editSlab('payin_type', v)} disabled={!onEditSlab} />
                                      </td>
                                      <td className="px-4 py-2.5 text-xs text-slate-700 dark:text-slate-300">
                                        <EditableCell label="Premium Type" value={slab.premium_type} displayValue={<span className={cellCls('premium_type', '')} title={cellTitle('premium_type')}>{slab.premium_type || 'N/A'}</span>} onSave={(v) => editSlab('premium_type', v)} disabled={!onEditSlab} />
                                      </td>
                                      <td className="px-4 py-2.5 text-xs text-slate-800 dark:text-slate-200 font-mono">
                                        <EditableCell label="Pay-In Slab From" value={slab.slab_from} fieldType="number" displayValue={<span className={cellCls('slab_from', '')} title={cellTitle('slab_from')}>{slab.slab_from !== null ? slab.slab_from.toLocaleString() : '0'}</span>} onSave={(v) => editSlab('slab_from', v)} disabled={!onEditSlab} />
                                      </td>
                                      <td className="px-4 py-2.5 text-xs text-slate-800 dark:text-slate-200 font-mono">
                                        <EditableCell label="Pay-In Slab Upto" value={slab.slab_to} fieldType="number" displayValue={<span className={cellCls('slab_to', '')} title={cellTitle('slab_to')}>{slab.slab_to !== null ? slab.slab_to.toLocaleString() : '∞'}</span>} onSave={(v) => editSlab('slab_to', v)} disabled={!onEditSlab} />
                                      </td>
                                    </>
                                  );
                                })()}
                                <td className="px-4 py-2.5 text-xs font-bold text-right text-emerald-600 dark:text-emerald-400">
                                  <EditableCell label="Pay-In OD" value={slab.payin_od} fieldType="number" displayValue={<span>{formatPercentage(slab.payin_od)}</span>} onSave={(v) => editSlab('payin_od', v)} disabled={!onEditSlab} className="justify-end" />
                                </td>
                                <td className="px-4 py-2.5 text-xs font-bold text-right text-amber-600 dark:text-amber-400">{formatPercentage(slab.payout_od)}</td>
                                <td className="px-4 py-2.5 text-xs font-bold text-right text-emerald-600 dark:text-emerald-400">
                                  <EditableCell label="Pay-In TP" value={slab.payin_tp} fieldType="number" displayValue={<span>{formatPercentage(slab.payin_tp)}</span>} onSave={(v) => editSlab('payin_tp', v)} disabled={!onEditSlab} className="justify-end" />
                                </td>
                                <td className="px-4 py-2.5 text-xs font-bold text-right text-amber-600 dark:text-amber-400">{formatPercentage(slab.payout_tp)}</td>
                                <td className="px-4 py-2.5 text-xs font-bold text-right text-emerald-600 dark:text-emerald-400">
                                  <EditableCell label="Pay-In Net" value={slab.payin_net} fieldType="number" displayValue={<span>{formatPercentage(slab.payin_net)}</span>} onSave={(v) => editSlab('payin_net', v)} disabled={!onEditSlab} className="justify-end" />
                                </td>
                                <td className="px-4 py-2.5 text-xs font-bold text-right text-amber-600 dark:text-amber-400">{formatPercentage(slab.payout_net)}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center p-8 bg-slate-50 dark:bg-slate-900/25 border border-[#E5E7EB] dark:border-slate-900 rounded-xl text-center">
                      <AlertTriangle className="w-6 h-6 text-amber-500/75 mb-2" />
                      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">No slab configuration available.</p>
                    </div>
                  )}
                </div>

              </div>
            )}

            {/* Warnings Section (always visible at bottom if present) */}
            {rule.warnings && rule.warnings.length > 0 && (
              <div className="mt-6 px-4 py-3 border-t border-amber-200 dark:border-amber-500/10 bg-amber-50 dark:bg-amber-500/5 rounded-xl">
                <p className="text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> Validation Warnings ({rule.warnings.length})
                </p>
                <ul className="list-disc list-inside space-y-0.5">
                  {rule.warnings.map((w, i) => <li key={i} className="text-xs text-slate-500 dark:text-slate-400">{w}</li>)}
                </ul>
              </div>
            )}

            {/* Raw Parsed Data (optional JSON preview of what the extractor read from the sheet) */}
            {rule.raw_json && Object.keys(rule.raw_json).length > 0 && (
              <div className="mt-6 border-t border-[#E5E7EB] dark:border-slate-900 pt-6">
                <button
                  type="button"
                  onClick={() => setShowRawJson(prev => !prev)}
                  className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
                >
                  {showRawJson ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  <Code className="w-3.5 h-3.5 text-[#4F46E5] dark:text-indigo-400" />
                  Raw Parsed Data
                </button>
                {showRawJson && (
                  <pre className="mt-3 p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-[#E5E7EB] dark:border-slate-800 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400 overflow-x-auto max-h-80 overflow-y-auto">
                    {JSON.stringify(rule.raw_json, null, 2)}
                  </pre>
                )}
              </div>
            )}

          </div>

        </div>
      </div>
  );

  return createPortal(modal, document.body);
};

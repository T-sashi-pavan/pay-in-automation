import React, { useState } from 'react';
import type { CommissionRule } from '../types';
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
} from 'lucide-react';

interface ExpandedRuleDetailsProps {
  rule: CommissionRule;
  colCount: number;
}

export const ExpandedRuleDetails: React.FC<ExpandedRuleDetailsProps> = ({ rule, colCount }) => {
  const [activeTab, setActiveTab] = useState<'non-slab' | 'slab'>('non-slab');
  const [showRawJson, setShowRawJson] = useState(false);

  const commissionType = rule.commissionType || rule.commission_type || 'NON_SLAB';
  const slabConfiguration = rule.slabConfiguration !== undefined ? rule.slabConfiguration : (rule.slab_configuration || false);

  const businessFields = [
    { label: 'LOB', value: rule.lob },
    { label: 'File Type', value: rule.file_type },
    { label: 'Insurance Company', value: rule.insurance_company },
    { label: 'Product', value: rule.product },
    { label: 'Policy Type', value: rule.policy_type },
    { label: 'Plan Type', value: rule.plan_type },
    { label: 'Sub Product', value: rule.sub_product },
    { label: 'Class', value: rule.class },
    { label: 'Sub Class', value: rule.sub_class },
    { label: 'Make', value: rule.make },
    { label: 'Model', value: rule.model },
    { label: 'Fuel Type', value: rule.fuel_type },
    { label: 'Body Type', value: rule.body_type },
    { label: 'Vehicle Age From', value: rule.vehicle_age_from !== null ? `${rule.vehicle_age_from} yrs` : null },
    { label: 'Vehicle Age To', value: rule.vehicle_age_to !== null ? `${rule.vehicle_age_to} yrs` : null },
    { label: 'CPA Status', value: rule.cpa_status },
    { label: 'NCB Status', value: rule.ncb_status },
    { label: 'Partner Type', value: rule.partner_type },
    { label: 'State', value: rule.state },
    { label: 'Zone', value: rule.zone },
    { label: 'Source', value: rule.source },
    { label: 'RTO', value: rule.rto },
    { label: 'Effective Date', value: rule.effective_date },
    { label: 'Remarks', value: rule.remarks }
  ];

  const formatPercentage = (val: number | null) => {
    return val !== null && val !== undefined ? `${val}%` : '-';
  };

  return (
    <tr>
      <td colSpan={colCount} className="p-0 bg-slate-50 dark:bg-slate-900/40 border-y border-[#E5E7EB] dark:border-slate-800">
        {/*
          Sticky-left + viewport-relative width: the parent row can be very
          wide (20+ columns, horizontally scrollable), so a centered fixed
          width box here would render off in the middle of that scroll area
          — invisible until the user scrolled sideways and often requiring
          the window to be shrunk to bring it into view. Pinning this panel
          to the left edge of whatever's currently visible, sized to the
          viewport instead of the table, means it's always fully visible
          immediately on expand.
        */}
        <div className="sticky left-0 w-[calc(100vw-4rem)] max-w-5xl m-4 rounded-2xl border border-[#E5E7EB] dark:border-slate-800/80 bg-white dark:bg-slate-950/90 overflow-hidden shadow-sm">

          {/* Tabs Navigation */}
          <div className="flex items-center justify-between border-b border-[#E5E7EB] dark:border-slate-800/80 bg-slate-50 dark:bg-slate-900/30 px-6 py-3">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setActiveTab('non-slab')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors duration-150 cursor-pointer ${
                  activeTab === 'non-slab'
                    ? 'bg-[#4F46E5] text-white'
                    : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700/80 text-slate-600 dark:text-slate-300 border border-[#E5E7EB] dark:border-slate-700/60'
                }`}
              >
                <ClipboardList className="w-3.5 h-3.5" />
                Non-Slab Details
              </button>

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
            </div>
          </div>

          <div className="p-6">
            
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
                    {businessFields.map((f, i) => (
                      <div key={i} className="bg-slate-50 dark:bg-slate-900/20 border border-[#E5E7EB] dark:border-slate-900/60 rounded-xl p-3 flex flex-col justify-center">
                        <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">{f.label}</span>
                        <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 mt-1 truncate" title={f.value?.toString() || ''}>
                          {f.value !== null && f.value !== undefined && f.value !== '' ? String(f.value) : <span className="text-slate-300 dark:text-slate-700 italic">None</span>}
                        </span>
                      </div>
                    ))}
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
                    {businessFields.map((f, i) => (
                      <div key={i} className="bg-slate-50 dark:bg-slate-900/20 border border-[#E5E7EB] dark:border-slate-900/60 rounded-xl p-3 flex flex-col justify-center">
                        <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">{f.label}</span>
                        <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 mt-1 truncate" title={f.value?.toString() || ''}>
                          {f.value !== null && f.value !== undefined && f.value !== '' ? String(f.value) : <span className="text-slate-300 dark:text-slate-700 italic">None</span>}
                        </span>
                      </div>
                    ))}
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
                            {['Pay-In Type', 'Premium Type', 'Pay-In Slab From', 'Pay-In Slab Upto', 'Pay-In OD', 'Payout OD', 'Pay-In TP', 'Payout TP', 'Pay-In Net', 'Payout Net'].map(h => (
                              <th key={h} className="px-4 py-2.5 text-left text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#E5E7EB]/70 dark:divide-slate-800/40">
                          {rule.slabs.map((slab) => (
                            <tr key={slab.id} className="hover:bg-slate-100 dark:hover:bg-slate-900/20 transition-colors">
                              <td className="px-4 py-2.5 text-xs font-bold text-[#4F46E5] dark:text-indigo-300">{slab.payin_type || 'N/A'}</td>
                              <td className="px-4 py-2.5 text-xs text-slate-700 dark:text-slate-300">{slab.premium_type || 'N/A'}</td>
                              <td className="px-4 py-2.5 text-xs text-slate-800 dark:text-slate-200 font-mono">{slab.slab_from !== null ? slab.slab_from.toLocaleString() : '0'}</td>
                              <td className="px-4 py-2.5 text-xs text-slate-800 dark:text-slate-200 font-mono">{slab.slab_to !== null ? slab.slab_to.toLocaleString() : '∞'}</td>
                              {[slab.payin_od, slab.payout_od, slab.payin_tp, slab.payout_tp, slab.payin_net, slab.payout_net].map((v, i) => (
                                <td key={i} className={`px-4 py-2.5 text-xs font-bold text-right ${i % 2 === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                                  {formatPercentage(v)}
                                </td>
                              ))}
                            </tr>
                          ))}
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
      </td>
    </tr>
  );
};

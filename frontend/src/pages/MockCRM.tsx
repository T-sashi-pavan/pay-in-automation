import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export const MockCRM: React.FC = () => {
  const [slabType, setSlabType] = useState<'NON_SLAB' | 'SLAB'>('NON_SLAB');
  const [submitted, setSubmitted] = useState<boolean>(false);

  // Retrieve upload_id from query params to fetch unique dataset constraints
  const searchParams = new URLSearchParams(window.location.search);
  const uploadId = searchParams.get('upload_id');

  const { data: uniqueValues } = useQuery<Record<string, string[]>>({
    queryKey: ['mockCrmUniqueValues', uploadId],
    queryFn: async () => {
      if (!uploadId) return {};
      const data = await api.getUniqueValues(Number(uploadId));
      return data;
    },
    enabled: !!uploadId
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
    }, 4000);
  };

  // Helper to dynamically render dataset options alongside defaults
  const renderOptions = (fieldName: string, defaultOpts: string[]) => {
    const customOpts = uniqueValues?.[fieldName] || [];
    const allOpts = Array.from(new Set([...defaultOpts, ...customOpts]));
    return allOpts.map(val => (
      <option key={val} value={val}>{val}</option>
    ));
  };

  return (
    <div className="min-h-screen bg-slate-900/10 dark:bg-slate-950 p-4 flex items-center justify-center">
      <div className="w-full max-w-4xl bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {/* Header - Sleek Indigo/Slate Gradient */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white px-6 py-3.5 flex items-center justify-between border-b border-indigo-500/20">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
            <h2 className="text-sm font-bold tracking-wide">Add Pay In (CRM Sandbox)</h2>
          </div>
          <div className="text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-full font-semibold">
            Broker Portal Simulation
          </div>
        </div>

        {submitted ? (
          <div id="success_message" className="p-12 text-center flex flex-col items-center justify-center gap-4 animate-in fade-in zoom-in duration-300">
            <div className="w-14 h-14 rounded-full bg-emerald-500 flex items-center justify-center text-white text-2xl font-extrabold shadow-lg shadow-emerald-500/20">
              ✓
            </div>
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Form Submitted Successfully</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">The record has been processed and committed to the CRM database simulation.</p>
          </div>
        ) : (
          <form id="crm-entry-form" onSubmit={handleSubmit} className="p-5 space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3.5">
              {/* Row 1 */}
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">LOB</label>
                <select id="lob" name="lob" disabled className="w-full h-8 px-2.5 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold text-slate-500 cursor-not-allowed">
                  <option value="Motor">Motor</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">File Type</label>
                <select id="file_type" name="file_type" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('file_type', ['New', 'Rollover', 'Used', 'ALL'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Insurance Company</label>
                <select id="insurance_company" name="insurance_company" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('insurance_company', ['Tata', 'Go Digit', 'Shriram', 'Cholamandalam'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Product</label>
                <select id="product" name="product" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('product', ['Private Car', 'GCV', 'PCV', 'Two Wheeler'])}
                </select>
              </div>

              {/* Row 2 */}
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Policy Type</label>
                <select id="policy_type" name="policy_type" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('policy_type', ['Comprehensive', 'Third Party', 'OD Only'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Plan Type</label>
                <select id="plan_type" name="plan_type" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('plan_type', ['1 Yr OD + 1 Yr TP', '1 Yr OD + 3 Yr TP', '3 Yr OD + 3 Yr TP', 'ALL'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Sub-Product</label>
                <select id="sub_product" name="sub_product" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('sub_product', ['NA', 'Other'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Class</label>
                <select id="class_" name="class_" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('class_', ['NA', 'Class A'])}
                </select>
              </div>

              {/* Row 3 */}
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Sub-Class</label>
                <select id="sub_class" name="sub_class" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('sub_class', ['NA', 'Passenger'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Make</label>
                <select id="make" name="make" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('make', ['ANY', 'Maruti', 'Hyundai', 'Tata'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Model</label>
                <select id="model" name="model" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('model', ['ANY', 'Swift', 'i20', 'Nexon'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Fuel Type</label>
                <select id="fuel_type" name="fuel_type" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('fuel_type', ['Petrol', 'Diesel', 'CNG', 'ALL'])}
                </select>
              </div>

              {/* Row 4 */}
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">CPA Status</label>
                <select id="cpa_status" name="cpa_status" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('cpa_status', ['Select CPA', 'Yes', 'No', 'ALL'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">NCB Status</label>
                <select id="ncb_status" name="ncb_status" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('ncb_status', ['Select NCB', 'Yes', 'No', 'ALL'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Vehicle Age From</label>
                <input id="vehicle_age_from" type="number" name="vehicle_age_from" placeholder="0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Vehicle Age To</label>
                <input id="vehicle_age_to" type="number" name="vehicle_age_to" placeholder="99" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>

              {/* Row 5 */}
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Slab Type</label>
                <select id="slab_type" name="slab_type" value={slabType} onChange={(e) => setSlabType(e.target.value as any)} className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="NON_SLAB">Non-Slab</option>
                  <option value="SLAB">Slab</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Source</label>
                <select id="source" name="source" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('source', ['Select Source', 'Direct', 'Broker', 'Agent'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Zone</label>
                <select id="zone" name="zone" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('zone', ['Select Zone', 'A', 'B', 'C', 'ALL'])}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">RTO</label>
                <select id="rto" name="rto" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  {renderOptions('rto', ['Select RTO', 'MH12', 'DL01', 'KA01'])}
                </select>
              </div>

              {/* Row 6 */}
              <div className="md:col-span-2">
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayIn Remark</label>
                <input id="payin_remark" type="text" name="payin_remark" placeholder="Enter remarks" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Effective Date</label>
                <input id="effective_date" type="text" name="effective_date" placeholder="YYYY-MM-DD" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Extra Remark</label>
                <input id="extra_remark" type="text" name="extra_remark" placeholder="Enter extra remark" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
            </div>

            {/* Non-Slab Rate Fields */}
            {slabType === 'NON_SLAB' && (
              <div className="border-t border-slate-200 dark:border-slate-800 pt-5 space-y-3.5">
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-205 uppercase tracking-wide">Rate Structure</h4>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3.5">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">Premium Type</label>
                    <select id="premium_type" name="premium_type" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                      <option value="OD">OD</option>
                      <option value="TP">TP</option>
                      <option value="NET">NET</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayIn OD (%)</label>
                    <input id="payin_od" type="text" name="payin_od" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayIn TP (%)</label>
                    <input id="payin_tp" type="text" name="payin_tp" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayIn NET (%)</label>
                    <input id="payin_net" type="text" name="payin_net" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayOut OD (%)</label>
                    <input id="payout_od" type="text" name="payout_od" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayOut TP (%)</label>
                    <input id="payout_tp" type="text" name="payout_tp" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayOut NET (%)</label>
                    <input id="payout_net" type="text" name="payout_net" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayIn Reward (%)</label>
                    <input id="payin_reward" type="text" name="payin_reward" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">PayIn Scheme (%)</label>
                    <input id="payin_scheme" type="text" name="payin_scheme" placeholder="0.0" className="w-full h-8 px-2.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                </div>
              </div>
            )}

            {/* Slab Grid Fields */}
            {slabType === 'SLAB' && (
              <div className="border-t border-slate-200 dark:border-slate-800 pt-5 space-y-3.5">
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-205 uppercase tracking-wide">Slab Tiers Grid</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 text-[10px] uppercase text-slate-400 font-bold tracking-wider">
                        <th className="py-2 pr-2">From</th>
                        <th className="py-2 px-2">To</th>
                        <th className="py-2 px-2">PayIn OD (%)</th>
                        <th className="py-2 px-2">PayIn TP (%)</th>
                        <th className="py-2 pl-2">PayIn Net (%)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[0, 1, 2].map((idx) => (
                        <tr key={idx} className="border-b border-slate-100 dark:border-slate-800/40">
                          <td className="py-2 pr-2">
                            <input id={`slab_from_${idx}`} type="text" placeholder="0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 px-2">
                            <input id={`slab_to_${idx}`} type="text" placeholder="MAX" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 px-2">
                            <input id={`slab_payin_od_${idx}`} type="text" placeholder="0.0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 px-2">
                            <input id={`slab_payin_tp_${idx}`} type="text" placeholder="0.0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 pl-2">
                            <input id={`slab_payin_net_${idx}`} type="text" placeholder="0.0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-855 dark:text-slate-200 focus:outline-none" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="border-t border-slate-200 dark:border-slate-800 pt-4 flex justify-end gap-3">
              <button type="button" className="px-4 py-1.5 text-xs font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                Cancel
              </button>
              <button id="submit_crm_form" type="submit" className="px-5 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded shadow cursor-pointer">
                Submit
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
export default MockCRM;

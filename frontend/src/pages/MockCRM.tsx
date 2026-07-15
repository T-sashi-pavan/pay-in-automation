import React, { useState } from 'react';

export const MockCRM: React.FC = () => {
  const [slabType, setSlabType] = useState<'NON_SLAB' | 'SLAB'>('NON_SLAB');
  const [submitted, setSubmitted] = useState<boolean>(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      // Clear after 3 seconds for repeat tests if needed
      setSubmitted(false);
    }, 4000);
  };

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 p-6 flex items-center justify-center">
      <div className="w-full max-w-4xl bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {/* Header */}
        <div className="bg-[#E25C34] text-white px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-wide">Add Pay In (CRM Sandbox)</h2>
          <div className="text-xs bg-white/20 px-2.5 py-1 rounded-full font-medium">OPP Insurance Brokers</div>
        </div>

        {submitted ? (
          <div id="success_message" className="p-12 text-center flex flex-col items-center justify-center gap-4 animate-in fade-in zoom-in duration-300">
            <div className="w-16 h-16 rounded-full bg-emerald-500 flex items-center justify-center text-white text-3xl font-extrabold shadow-lg shadow-emerald-500/20">
              ✓
            </div>
            <h3 className="text-xl font-bold text-slate-800 dark:text-slate-100">Form Submitted Successfully</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">The record has been processed and committed to the CRM simulation database.</p>
          </div>
        ) : (
          <form id="crm-entry-form" onSubmit={handleSubmit} className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Row 1 */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">LOB</label>
                <select id="lob" name="lob" disabled className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold text-slate-600 dark:text-slate-400 focus:outline-none">
                  <option value="Motor">Motor</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">File Type</label>
                <select id="file_type" name="file_type" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="New">New</option>
                  <option value="Rollover">Rollover</option>
                  <option value="Used">Used</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Insurance Company</label>
                <select id="insurance_company" name="insurance_company" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Tata">Tata</option>
                  <option value="Go Digit">Go Digit</option>
                  <option value="Shriram">Shriram</option>
                  <option value="Cholamandalam">Cholamandalam</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Product</label>
                <select id="product" name="product" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Private Car">Private Car</option>
                  <option value="GCV">GCV</option>
                  <option value="PCV">PCV</option>
                  <option value="Two Wheeler">Two Wheeler</option>
                </select>
              </div>

              {/* Row 2 */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Policy Type</label>
                <select id="policy_type" name="policy_type" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Comprehensive">Comprehensive</option>
                  <option value="Third Party">Third Party</option>
                  <option value="OD Only">OD Only</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Plan Type</label>
                <select id="plan_type" name="plan_type" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="1 Yr OD + 1 Yr TP">1 Yr OD + 1 Yr TP</option>
                  <option value="1 Yr OD + 3 Yr TP">1 Yr OD + 3 Yr TP</option>
                  <option value="3 Yr OD + 3 Yr TP">3 Yr OD + 3 Yr TP</option>
                  <option value="ALL">ALL</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Sub-Product</label>
                <select id="sub_product" name="sub_product" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="NA">NA</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Class</label>
                <select id="class_" name="class_" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="NA">NA</option>
                  <option value="Class A">Class A</option>
                </select>
              </div>

              {/* Row 3 */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Sub-Class</label>
                <select id="sub_class" name="sub_class" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="NA">NA</option>
                  <option value="Passenger">Passenger</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Make</label>
                <select id="make" name="make" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="ANY">ANY</option>
                  <option value="Maruti">Maruti</option>
                  <option value="Hyundai">Hyundai</option>
                  <option value="Tata">Tata</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Model</label>
                <select id="model" name="model" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="ANY">ANY</option>
                  <option value="Swift">Swift</option>
                  <option value="i20">i20</option>
                  <option value="Nexon">Nexon</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Fuel Type</label>
                <select id="fuel_type" name="fuel_type" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Petrol">Petrol</option>
                  <option value="Diesel">Diesel</option>
                  <option value="CNG">CNG</option>
                </select>
              </div>

              {/* Row 4 */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">CPA Status</label>
                <select id="cpa_status" name="cpa_status" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Select CPA">Select CPA</option>
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">NCB Status</label>
                <select id="ncb_status" name="ncb_status" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Select NCB">Select NCB</option>
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Vehicle Age From</label>
                <input id="vehicle_age_from" type="number" name="vehicle_age_from" placeholder="0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Vehicle Age To</label>
                <input id="vehicle_age_to" type="number" name="vehicle_age_to" placeholder="99" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>

              {/* Row 5 */}
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Slab Type</label>
                <select id="slab_type" name="slab_type" value={slabType} onChange={(e) => setSlabType(e.target.value as any)} className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="NON_SLAB">Non-Slab</option>
                  <option value="SLAB">Slab</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Source</label>
                <select id="source" name="source" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Select Source">Select Source</option>
                  <option value="Direct">Direct</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Zone</label>
                <select id="zone" name="zone" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Select Zone">Select Zone</option>
                  <option value="A">Zone A</option>
                  <option value="B">Zone B</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">RTO</label>
                <select id="rto" name="rto" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                  <option value="Select RTO">Select RTO</option>
                  <option value="MH12">MH12</option>
                  <option value="DL01">DL01</option>
                </select>
              </div>

              {/* Row 6 */}
              <div className="md:col-span-2">
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayIn Remark</label>
                <input id="payin_remark" type="text" name="payin_remark" placeholder="Enter remarks" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Effective Date</label>
                <input id="effective_date" type="text" name="effective_date" placeholder="YYYY-MM-DD" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Extra Remark</label>
                <input id="extra_remark" type="text" name="extra_remark" placeholder="Enter extra remark" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
            </div>

            {/* Non-Slab Rate Fields */}
            {slabType === 'NON_SLAB' && (
              <div className="border-t border-slate-200 dark:border-slate-800 pt-6 space-y-4">
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">Rate Structure</h4>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Premium Type</label>
                    <select id="premium_type" name="premium_type" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500">
                      <option value="OD">OD</option>
                      <option value="TP">TP</option>
                      <option value="NET">NET</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayIn OD (%)</label>
                    <input id="payin_od" type="text" name="payin_od" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayIn TP (%)</label>
                    <input id="payin_tp" type="text" name="payin_tp" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayIn NET (%)</label>
                    <input id="payin_net" type="text" name="payin_net" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayOut OD (%)</label>
                    <input id="payout_od" type="text" name="payout_od" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayOut TP (%)</label>
                    <input id="payout_tp" type="text" name="payout_tp" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayOut NET (%)</label>
                    <input id="payout_net" type="text" name="payout_net" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayIn Reward (%)</label>
                    <input id="payin_reward" type="text" name="payin_reward" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">PayIn Scheme (%)</label>
                    <input id="payin_scheme" type="text" name="payin_scheme" placeholder="0.0" className="w-full h-9 px-3 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500" />
                  </div>
                </div>
              </div>
            )}

            {/* Slab Grid Fields */}
            {slabType === 'SLAB' && (
              <div className="border-t border-slate-200 dark:border-slate-800 pt-6 space-y-4">
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">Slab Tiers Grid</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] uppercase text-slate-500 font-bold">
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
                            <input id={`slab_from_${idx}`} type="text" placeholder="0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 px-2">
                            <input id={`slab_to_${idx}`} type="text" placeholder="MAX" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 px-2">
                            <input id={`slab_payin_od_${idx}`} type="text" placeholder="0.0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 px-2">
                            <input id={`slab_payin_tp_${idx}`} type="text" placeholder="0.0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none" />
                          </td>
                          <td className="py-2 pl-2">
                            <input id={`slab_payin_net_${idx}`} type="text" placeholder="0.0" className="w-full h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-200 focus:outline-none" />
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
              <button type="button" className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded">
                Cancel
              </button>
              <button id="submit_crm_form" type="submit" className="px-5 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded shadow cursor-pointer">
                Submit
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

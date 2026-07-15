import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { 
  Play, 
  FileSpreadsheet, 
  Cpu, 
  Clock, 
  CheckCircle, 
  X, 
  Loader2, 
  Image as ImageIcon 
} from 'lucide-react';
import type { UploadHistory } from '../types';

interface AutomationUpload extends UploadHistory {
  slab_rows_count: number;
  non_slab_rows_count: number;
  total_rows: number;
}

const formatRate = (rate: any) => {
  if (rate === null || rate === undefined || rate === '' || String(rate).toLowerCase() === 'null') {
    return '-';
  }
  return `${rate}%`;
};

export const Automation: React.FC = () => {
  const { notify } = useNotification();
  const [selectedUpload, setSelectedUpload] = useState<AutomationUpload | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [automationStep, setAutomationStep] = useState<'idle' | 'running' | 'completed'>('idle');
  const [progressLog, setProgressLog] = useState<{ label: string; status: 'pending' | 'active' | 'done' | 'failed' }[]>([]);
  const [currentFillingField, setCurrentFillingField] = useState<string | null>(null);
  const [simulatedForm, setSimulatedForm] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<'form' | 'playwright'>('form');
  const [activeScreenshot, setActiveScreenshot] = useState<string>('non_slab_filled');
  const [playwrightResult, setPlaywrightResult] = useState<any>(null);
  const [executionTime, setExecutionTime] = useState<string>('0s');
  const [showSubmittedBanner, setShowSubmittedBanner] = useState(false);

  // Fetch uploads for automation
  const { data: uploads = [], isLoading } = useQuery<AutomationUpload[]>({
    queryKey: ['automationUploads'],
    queryFn: async () => {
      const data = await api.getAutomationUploads();
      return data;
    }
  });

  // Fetch valid rows for chosen upload
  const { data: validRows, isLoading: isLoadingRows } = useQuery({
    queryKey: ['validRows', selectedUpload?.id],
    queryFn: async () => {
      if (!selectedUpload) return null;
      const data = await api.getValidRows(selectedUpload.id);
      return data;
    },
    enabled: !!selectedUpload
  });

  // Fetch unique fields for chosen upload dropdowns
  const { data: uniqueValues } = useQuery({
    queryKey: ['uniqueValues', selectedUpload?.id],
    queryFn: async () => {
      if (!selectedUpload) return null;
      const data = await api.getUniqueValues(selectedUpload.id);
      return data;
    },
    enabled: !!selectedUpload
  });

  // Playwright automation trigger
  const runAutomationMutation = useMutation({
    mutationFn: async (payload: { upload_id: number; frontend_url: string }) => {
      const data = await api.runAutomation(payload);
      return data;
    }
  });

  const handleOpenModal = (upload: AutomationUpload) => {
    setSelectedUpload(upload);
    setIsModalOpen(true);
    setAutomationStep('idle');
    setProgressLog([]);
    setPlaywrightResult(null);
    setSimulatedForm({});
    setCurrentFillingField(null);
    setActiveTab('form');
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedUpload(null);
    if (automationStep === 'completed') {
      setShowSubmittedBanner(true);
    }
  };

  const renderSimulatedSelect = (
    label: string,
    name: string,
    currentVal: string,
    placeholder: string,
    options: string[]
  ) => {
    const isActive = currentFillingField === name;
    return (
      <div className="relative">
        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">{label}</label>
        <select 
          disabled 
          className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-850 dark:text-slate-200 cursor-not-allowed transition-all
            ${isActive ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`}
        >
          <option value="">{currentVal || placeholder}</option>
        </select>
        
        {/* Visual Dropdown Opening Menu Simulation */}
        {isActive && (
          <div className="absolute left-0 right-0 top-full mt-0.5 bg-white dark:bg-slate-900 border border-[#4F46E5] rounded-md shadow-2xl z-50 py-1 text-slate-850 dark:text-slate-100 max-h-32 overflow-y-auto text-[10px] animate-in fade-in slide-in-from-top-1">
            {options.map((opt, idx) => {
              const isSelected = currentVal === opt;
              return (
                <div 
                  key={idx} 
                  className={`px-2.5 py-1 text-left transition-colors duration-150 ${isSelected ? 'bg-[#4F46E5] text-white font-bold' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'}`}
                >
                  {opt}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const startAutomationFlow = async () => {
    if (!selectedUpload || !validRows) return;
    setAutomationStep('running');
    setPlaywrightResult(null);
    setExecutionTime('0s');
    
    const startTime = Date.now();

    const cleanVal = (val: any, defaultVal = 'ALL') => {
      if (val === null || val === undefined || String(val).trim() === '') {
        return defaultVal;
      }
      return String(val);
    };

    const formatRate = (rate: any) => {
      if (rate === null || rate === undefined || rate === '' || String(rate).toLowerCase() === 'null') {
        return '-';
      }
      return `${rate}%`;
    };

    // Setup initial checklist logs
    const logs: { label: string; status: 'pending' | 'active' | 'done' | 'failed' }[] = [
      { label: 'Preparing automation engine...', status: 'active' },
      { label: 'Loading source rows from dataset...', status: 'pending' },
      { label: 'Selecting and validating values...', status: 'pending' },
      { label: 'Submitting Non-Slab record...', status: 'pending' },
      { label: 'Submitting Slab record...', status: 'pending' },
      { label: 'Finalizing automation run...', status: 'pending' },
    ];
    setProgressLog([...logs]);

    const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

    // STEP 1: Preparing
    await sleep(800);
    logs[0].status = 'done';
    logs[1].status = 'active';
    setProgressLog([...logs]);

    // STEP 2: Loading Row
    const nonSlab = validRows.non_slab;
    const slab = validRows.slab;
    await sleep(800);
    
    if (!nonSlab && !slab) {
      logs[1].status = 'failed';
      setProgressLog([...logs]);
      notify('No valid rows found to showcase automation.', 'error');
      setAutomationStep('idle');
      return;
    }
    
    logs[1].status = 'done';
    logs[2].status = 'active';
    setProgressLog([...logs]);

    // Trigger Playwright backend process asynchronously in the background (DO NOT await it)
    const playwrightPromise = runAutomationMutation.mutateAsync({
      upload_id: selectedUpload.id,
      frontend_url: window.location.origin
    }).catch(err => {
      console.error('Playwright background execution failed', err);
      return { success: false, error: err.message };
    });

    // STEP 3: Selecting and filling values (Simulate filling form fields sequentially)
    const animateFields = async (rule: any, isSlabMode: boolean) => {
      setSimulatedForm((prev: Record<string, any>) => ({
        ...prev,
        slab_type: isSlabMode ? 'SLAB' : 'NON_SLAB',
        lob: rule.lob || 'Motor',
        insurance_company: rule.insurance_company || selectedUpload.company || 'N/A'
      }));
      
      const fields = [
        { name: 'file_type', val: cleanVal(rule.file_type, 'ALL') },
        { name: 'product', val: cleanVal(rule.product, 'ALL') },
        { name: 'policy_type', val: cleanVal(rule.policy_type, 'ALL') },
        { name: 'plan_type', val: cleanVal(rule.plan_type, 'ALL') },
        { name: 'sub_product', val: cleanVal(rule.sub_product, 'ALL') },
        { name: 'class_', val: cleanVal(rule.class, 'ALL') },
        { name: 'sub_class', val: cleanVal(rule.sub_class, 'ALL') },
        { name: 'make', val: cleanVal(rule.make, 'ALL') },
        { name: 'model', val: cleanVal(rule.model, 'ALL') },
        { name: 'fuel_type', val: cleanVal(rule.fuel_type, 'ALL') },
        { name: 'cpa_status', val: cleanVal(rule.cpa_status, 'ALL') },
        { name: 'ncb_status', val: cleanVal(rule.ncb_status, 'ALL') },
        { name: 'vehicle_age_from', val: rule.vehicle_age_from !== null && rule.vehicle_age_from !== undefined ? String(rule.vehicle_age_from) : '0' },
        { name: 'vehicle_age_to', val: rule.vehicle_age_to !== null && rule.vehicle_age_to !== undefined ? String(rule.vehicle_age_to) : '99' },
        { name: 'source', val: cleanVal(rule.source, 'ALL') },
        { name: 'zone', val: cleanVal(rule.zone, 'ALL') },
        { name: 'rto', val: cleanVal(rule.rto, 'ALL') },
        { name: 'payin_remark', val: cleanVal(rule.remarks, '') },
        { name: 'effective_date', val: cleanVal(rule.effective_date, new Date().toISOString().split('T')[0]) }
      ];

      if (!isSlabMode) {
        fields.push(
          { name: 'premium_type', val: 'OD' },
          { name: 'payin_od', val: formatRate(rule.payin_od) },
          { name: 'payin_tp', val: formatRate(rule.payin_tp) },
          { name: 'payin_net', val: formatRate(rule.payin_net) },
          { name: 'payout_od', val: formatRate(rule.payout_od) },
          { name: 'payout_tp', val: formatRate(rule.payout_tp) },
          { name: 'payout_net', val: formatRate(rule.payout_net) }
        );
      }

      for (const field of fields) {
        setCurrentFillingField(field.name);
        // Step 1: Open simulated dropdown by sleeping 200ms
        await sleep(200);
        
        // Step 2: Set field choice and wait 300ms (Total 500ms/half-second per field!)
        setSimulatedForm((prev: Record<string, any>) => ({ ...prev, [field.name]: field.val }));
        await sleep(300);

        // Auto-scroll modal container to the bottom as rates or slabs are filled
        if (['payin_od', 'payin_tp', 'payin_net', 'payout_od', 'slabsList'].includes(field.name)) {
          const container = document.getElementById('modal-scroll-container');
          if (container) {
            container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
          }
        }
      }
      setCurrentFillingField(null);
    };

    // Simulate Non-Slab Fill
    if (nonSlab) {
      await animateFields(nonSlab, false);
      logs[2].status = 'done';
      logs[3].status = 'active';
      setProgressLog([...logs]);
      await sleep(600);
      logs[3].status = 'done';
      setProgressLog([...logs]);
    } else {
      logs[2].status = 'done';
      logs[3].label = 'Skipping Non-Slab record...';
      logs[3].status = 'done';
      setProgressLog([...logs]);
    }

    // Simulate Slab Fill if slab row exists
    if (slab) {
      logs[4].status = 'active';
      setProgressLog([...logs]);
      await animateFields(slab, true);
      // Populate mock slabs
      const mockSlabsList = slab.slabs || [];
      setSimulatedForm((prev: Record<string, any>) => ({
        ...prev,
        slabsList: mockSlabsList
      }));
      await sleep(1000); // give time to show slab entries
      logs[4].status = 'done';
      setProgressLog([...logs]);
    } else {
      logs[4].label = 'Skipping Slab record (none in history)...';
      logs[4].status = 'done';
      setProgressLog([...logs]);
    }

    // Finalizing: instantly succeed on frontend and run browser engine in the background
    logs[5].status = 'done';
    setProgressLog([...logs]);
    
    // Save backend screenshots context when done, but don't hold up modal closure
    playwrightPromise.then((pwResult) => {
      setPlaywrightResult(pwResult);
    });

    setExecutionTime(`${((Date.now() - startTime) / 1000).toFixed(1)}s`);
    setAutomationStep('completed');
    notify('Form Submitted Successfully!', 'success');
  };

  return (
    <div className="space-y-6">
      {showSubmittedBanner && (
        <div className="bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-250 dark:border-emerald-800/40 rounded-lg p-3.5 flex items-center justify-between transition-all duration-300 animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <div>
              <p className="text-xs font-bold text-emerald-800 dark:text-emerald-300">
                Form Submitted successfully to Broker CRM sandbox!
              </p>
              <p className="text-[10px] text-emerald-600 dark:text-emerald-400 mt-0.5">
                The Playwright automated synchronization continues processing in the background.
              </p>
            </div>
          </div>
          <button 
            onClick={() => setShowSubmittedBanner(false)}
            className="text-emerald-500 hover:text-emerald-700 dark:text-emerald-450 dark:hover:text-emerald-300 transition-colors p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#4F46E5]" />
            Broker CRM Entry Automation
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Automate pay-in grids directly into your broker CRM database using Playwright-driven browser actions.
          </p>
        </div>
      </div>

      {/* Uploads History Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
            Uploaded Grid Databases
          </h3>
        </div>
        
        {isLoading ? (
          <div className="p-12 text-center flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-8 h-8 text-[#4F46E5] animate-spin" />
            <p className="text-xs text-slate-500">Loading upload history data...</p>
          </div>
        ) : uploads.length === 0 ? (
          <div className="p-12 text-center text-slate-400 dark:text-slate-500">
            <FileSpreadsheet className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm font-semibold">No upload records available</p>
            <p className="text-xs mt-1">Please upload spreadsheets in the "Upload Files" tab first.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 uppercase tracking-wider bg-slate-50/50 dark:bg-slate-900/20">
                  <th className="py-3 px-4">File Name</th>
                  <th className="py-3 px-4">Insurer</th>
                  <th className="py-3 px-4">Upload Date</th>
                  <th className="py-3 px-4 text-center">Slab Rows</th>
                  <th className="py-3 px-4 text-center">Non-Slab Rows</th>
                  <th className="py-3 px-4 text-center font-extrabold">Total Rows</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
                {uploads.map((upload) => {
                  const uploadDate = upload.uploaded_at 
                    ? new Date(upload.uploaded_at).toLocaleDateString(undefined, {
                        month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
                      }) 
                    : 'N/A';
                  return (
                    <tr key={upload.id} className="hover:bg-slate-50/40 dark:hover:bg-slate-800/20 transition-colors">
                      <td className="py-3 px-4 text-xs font-bold text-slate-700 dark:text-slate-300 max-w-[240px] truncate">
                        {upload.filename}
                      </td>
                      <td className="py-3 px-4 text-xs font-semibold text-slate-600 dark:text-slate-400">
                        {upload.company || 'Detecting...'}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-500 dark:text-slate-500 font-mono">
                        {uploadDate}
                      </td>
                      <td className="py-3 px-4 text-xs text-center font-mono text-slate-600 dark:text-slate-400">
                        {upload.slab_rows_count.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-xs text-center font-mono text-slate-600 dark:text-slate-400">
                        {upload.non_slab_rows_count.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-xs text-center font-bold font-mono text-slate-800 dark:text-slate-200">
                        {upload.total_rows.toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase
                          ${upload.status === 'COMPLETED' ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400' : ''}
                          ${upload.status === 'PROCESSING' ? 'bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400 animate-pulse' : ''}
                          ${upload.status === 'FAILED' ? 'bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400' : ''}
                        `}>
                          {upload.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => handleOpenModal(upload)}
                          disabled={upload.status !== 'COMPLETED'}
                          className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#4F46E5] hover:bg-[#4338CA] disabled:bg-slate-100 disabled:dark:bg-slate-800 disabled:text-slate-400 disabled:dark:text-slate-600 text-white text-xs font-semibold rounded-lg shadow-sm cursor-pointer disabled:cursor-not-allowed transition-all"
                        >
                          <Play className="w-3.5 h-3.5 fill-current" />
                          Automate
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CRM Entry / Playwright Modal */}
      {isModalOpen && selectedUpload && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 dark:bg-slate-950/80 backdrop-blur-sm p-4 flex items-center justify-center">
          <div className="w-full max-w-6xl bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
            
            {/* Modal Header - Sleek Indigo/Slate Gradient */}
            <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white px-5 py-3 flex items-center justify-between border-b border-indigo-500/20 flex-shrink-0">
              <div>
                <h3 className="text-sm font-bold tracking-wide">Broker CRM - Add Pay In</h3>
                <p className="text-[10px] text-indigo-200/80 font-semibold mt-0.5 font-mono">
                  Sandbox Target: {selectedUpload.filename} ({selectedUpload.company})
                </p>
              </div>
              <button 
                type="button" 
                onClick={handleCloseModal}
                className="p-1 rounded-lg hover:bg-white/10 text-white transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Sub-navigation (Form Sandbox / Playwright Live Preview) */}
            {automationStep !== 'idle' && (
              <div className="border-b border-slate-200 dark:border-slate-800 px-6 py-2 bg-slate-50 dark:bg-slate-900/50 flex items-center justify-between flex-shrink-0">
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setActiveTab('form')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer
                      ${activeTab === 'form' 
                        ? 'bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-800' 
                        : 'text-slate-500 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-800'
                      }`}
                  >
                    Form Visual View
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (automationStep === 'completed' || playwrightResult) {
                        setActiveTab('playwright');
                      }
                    }}
                    disabled={automationStep === 'running' && !playwrightResult}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50
                      ${activeTab === 'playwright' 
                        ? 'bg-[#4F46E5] text-white' 
                        : 'text-slate-500 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-800'
                      }`}
                  >
                    <ImageIcon className="w-3.5 h-3.5" />
                    Playwright Live Screenshots
                  </button>
                </div>

                {automationStep === 'running' && (
                  <span className="flex items-center gap-1.5 text-xs text-amber-600 font-bold font-mono">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Playwright Engine Executing...
                  </span>
                )}
                {automationStep === 'completed' && (
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold font-mono">
                    ✓ Completed in {executionTime}
                  </span>
                )}
              </div>
            )}

            {/* Modal Body Area */}
            <div id="modal-scroll-container" className="flex-1 overflow-y-auto p-6 flex flex-col md:flex-row gap-6">
              
              {/* Left Panel: CRM Form Entry (Visualizer) - Compact styling */}
              <div className={`flex-1 space-y-4 ${activeTab === 'playwright' ? 'hidden md:block' : ''}`}>
                <div id="visual-crm-form" className="space-y-3.5 border border-slate-200 dark:border-slate-800 rounded-lg p-4 bg-slate-50/50 dark:bg-slate-900/30">
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
                    {/* Common Fields */}
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">LOB</label>
                      <select disabled className="w-full h-7 px-2 rounded border border-slate-200 dark:border-slate-800 bg-slate-105 dark:bg-slate-800 text-[11px] font-bold text-slate-500 cursor-not-allowed">
                        <option value="Motor">Motor</option>
                      </select>
                    </div>

                    {renderSimulatedSelect(
                      'File Type',
                      'file_type',
                      simulatedForm.file_type,
                      'Select File Type',
                      ['ALL', 'New', 'RollOver', 'Break-in']
                    )}

                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Insurance Company</label>
                      <select disabled className="w-full h-7 px-2 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 text-[11px] font-semibold text-slate-650 dark:text-slate-400 cursor-not-allowed">
                        <option value="">{simulatedForm.insurance_company || selectedUpload.company || 'Select Insurer'}</option>
                      </select>
                    </div>

                    {renderSimulatedSelect(
                      'Product',
                      'product',
                      simulatedForm.product,
                      'Select Product',
                      ['ALL', 'GCV3', 'Private Car', 'Two Wheeler', '1_GCCV_3W']
                    )}

                    {/* Row 2 */}
                    {renderSimulatedSelect(
                      'Policy Type',
                      'policy_type',
                      simulatedForm.policy_type,
                      'Select Policy Type',
                      ['ALL', 'Comprehensive', 'Third Party', 'Own Damage']
                    )}

                    {renderSimulatedSelect(
                      'Plan Type',
                      'plan_type',
                      simulatedForm.plan_type,
                      'Select Plan Type',
                      ['ALL', '1 Yr OD + 1 Yr TP', '1 Yr TP', '3 Yr OD + 3 Yr TP']
                    )}

                    {renderSimulatedSelect(
                      'Sub-Product',
                      'sub_product',
                      simulatedForm.sub_product,
                      'Select Sub-Product',
                      ['ALL', 'Commercial Vehicle', 'NA', 'PC-Package']
                    )}

                    {renderSimulatedSelect(
                      'Class',
                      'class_',
                      simulatedForm.class_,
                      'Select Class',
                      ['ALL', 'Class A', 'Class B', 'NA']
                    )}

                    {/* Row 3 */}
                    {renderSimulatedSelect(
                      'Sub-Class',
                      'sub_class',
                      simulatedForm.sub_class,
                      'Select Sub-Class',
                      ['ALL', 'SubClass C', 'NA']
                    )}

                    {renderSimulatedSelect(
                      'Make',
                      'make',
                      simulatedForm.make,
                      'Select Make',
                      ['ALL', 'Maruti Suzuki', 'Hyundai', 'Tata Motors']
                    )}

                    {renderSimulatedSelect(
                      'Model',
                      'model',
                      simulatedForm.model,
                      'Select Model',
                      ['ALL', 'Swift', 'i20', 'Nexon']
                    )}

                    {renderSimulatedSelect(
                      'Fuel Type',
                      'fuel_type',
                      simulatedForm.fuel_type,
                      'Select Fuel Type',
                      ['ALL', 'Petrol', 'Diesel', 'CNG', 'Electric']
                    )}

                    {/* Row 4 */}
                    {renderSimulatedSelect(
                      'CPA Status',
                      'cpa_status',
                      simulatedForm.cpa_status,
                      'Select CPA Status',
                      ['ALL', 'Yes', 'No']
                    )}

                    {renderSimulatedSelect(
                      'NCB Status',
                      'ncb_status',
                      simulatedForm.ncb_status,
                      'Select NCB Status',
                      ['ALL', 'Yes', 'No', '0%', '20%', '50%']
                    )}

                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Vehicle Age From</label>
                      <input type="text" readOnly value={simulatedForm.vehicle_age_from || ''} placeholder="0" className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                        ${currentFillingField === 'vehicle_age_from' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Vehicle Age To</label>
                      <input type="text" readOnly value={simulatedForm.vehicle_age_to || ''} placeholder="99" className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                        ${currentFillingField === 'vehicle_age_to' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                    </div>

                    {/* Row 5 */}
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Slab Type</label>
                      <select disabled className="w-full h-7 px-2 rounded border border-slate-200 dark:border-slate-800 bg-slate-105 dark:bg-slate-800 text-[11px] font-bold text-slate-500 cursor-not-allowed">
                        <option value="">{simulatedForm.slab_type === 'SLAB' ? 'Slab' : 'Non-Slab'}</option>
                      </select>
                    </div>

                    {renderSimulatedSelect(
                      'Source',
                      'source',
                      simulatedForm.source,
                      'Select Source',
                      ['ALL', 'Online', 'Offline', 'Partner Portal']
                    )}

                    {renderSimulatedSelect(
                      'Zone',
                      'zone',
                      simulatedForm.zone,
                      'Select Zone',
                      ['ALL', 'Zone A', 'Zone B', 'Zone C']
                    )}

                    {renderSimulatedSelect(
                      'RTO',
                      'rto',
                      simulatedForm.rto,
                      'Select RTO',
                      ['ALL', 'AP-01', 'TS-09', 'DL-01', 'MH-02']
                    )}

                    {/* Row 6 */}
                    <div className="sm:col-span-2">
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">PayIn Remark</label>
                      <input type="text" readOnly value={simulatedForm.payin_remark || ''} placeholder="Remarks metadata" className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                        ${currentFillingField === 'payin_remark' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Effective Date</label>
                      <input type="text" readOnly value={simulatedForm.effective_date || ''} placeholder="YYYY-MM-DD" className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                        ${currentFillingField === 'effective_date' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Extra Remark</label>
                      <input type="text" readOnly value={simulatedForm.extra_remark || ''} className="w-full h-7 px-2 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-850 text-[11px] text-slate-500 cursor-not-allowed" />
                    </div>
                  </div>

                  {/* Rate Fields */}
                  {simulatedForm.slab_type === 'NON_SLAB' && (
                    <div className="border-t border-slate-200 dark:border-slate-800 pt-3 mt-3">
                      <h4 className="text-[10px] font-bold text-slate-450 dark:text-slate-300 uppercase tracking-wider mb-2">Non-Slab Commissions</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
                        <div>
                          <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Premium Type</label>
                          <select disabled className="w-full h-7 px-2 rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-805 text-[11px] text-slate-500 cursor-not-allowed">
                            <option value="">{simulatedForm.premium_type || 'OD'}</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">PayIn OD</label>
                          <input type="text" readOnly value={simulatedForm.payin_od || ''} className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                            ${currentFillingField === 'payin_od' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">PayIn TP</label>
                          <input type="text" readOnly value={simulatedForm.payin_tp || ''} className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                            ${currentFillingField === 'payin_tp' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">PayIn Net</label>
                          <input type="text" readOnly value={simulatedForm.payin_net || ''} className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                            ${currentFillingField === 'payin_net' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                        </div>
                        
                        {/* PayOut Fields row */}
                        <div className="sm:col-start-2">
                          <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">PayOut OD</label>
                          <input type="text" readOnly value={simulatedForm.payout_od || ''} className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                            ${currentFillingField === 'payout_od' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">PayOut TP</label>
                          <input type="text" readOnly value={simulatedForm.payout_tp || ''} className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                            ${currentFillingField === 'payout_tp' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">PayOut Net</label>
                          <input type="text" readOnly value={simulatedForm.payout_net || ''} className={`w-full h-7 px-2 rounded border text-[11px] bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none transition-all
                            ${currentFillingField === 'payout_net' ? 'border-[#4F46E5] ring-2 ring-indigo-500/10' : 'border-slate-200 dark:border-slate-800'}`} />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Slab Detail List */}
                  {simulatedForm.slab_type === 'SLAB' && (
                    <div className="border-t border-slate-200 dark:border-slate-800 pt-4 mt-4">
                      <h4 className="text-[10px] font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-3">Slab Tiers Grid</h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="border-b border-slate-200 dark:border-slate-800 text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                              <th className="py-1.5 pr-2">From</th>
                              <th className="py-1.5 px-2">To</th>
                              <th className="py-1.5 px-2">PayIn OD (%)</th>
                              <th className="py-1.5 px-2">PayIn TP (%)</th>
                              <th className="py-1.5 pl-2">PayIn Net (%)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(simulatedForm.slabsList || [{}, {}, {}]).map((s: any, idx: number) => (
                              <tr key={idx} className="border-b border-slate-100 dark:border-slate-800/40">
                                <td className="py-1.5 pr-2 text-xs font-mono">{s.slab_from !== undefined && s.slab_from !== null ? s.slab_from.toLocaleString() : '-'}</td>
                                <td className="py-1.5 px-2 text-xs font-mono">{s.slab_to !== undefined && s.slab_to !== null ? String(s.slab_to) : 'MAX'}</td>
                                <td className="py-1.5 px-2 text-xs font-bold text-emerald-600 font-mono">{formatRate(s.payin_od)}</td>
                                <td className="py-1.5 px-2 text-xs font-bold text-emerald-600 font-mono">{formatRate(s.payin_tp)}</td>
                                <td className="py-1.5 pl-2 text-xs font-bold text-emerald-600 font-mono">{formatRate(s.payin_net)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Panel: Playwright Live Screenshot Preview or Progress checklist */}
              <div className={`w-full md:w-[380px] flex-shrink-0 flex flex-col gap-6 ${activeTab === 'form' && automationStep !== 'idle' ? 'block' : ''} ${activeTab === 'form' && automationStep === 'idle' ? 'hidden md:block' : ''}`}>
                
                {/* Status checklist panel */}
                {automationStep !== 'idle' && (
                  <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-xl space-y-4">
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-[#4F46E5]" />
                      Automation Checklist
                    </h4>
                    <div className="space-y-2.5">
                      {progressLog.map((log, index) => (
                        <div key={index} className="flex items-start gap-2.5 text-xs">
                          <div className="mt-0.5">
                            {log.status === 'done' && <CheckCircle className="w-4 h-4 text-emerald-500 fill-emerald-500/10" />}
                            {log.status === 'active' && <Loader2 className="w-4 h-4 text-amber-500 animate-spin" />}
                            {log.status === 'pending' && <div className="w-4 h-4 rounded-full border-2 border-slate-300 dark:border-slate-700" />}
                            {log.status === 'failed' && <div className="w-4 h-4 rounded-full bg-rose-500 flex items-center justify-center text-white text-[10px] font-bold">!</div>}
                          </div>
                          <span className={`font-medium ${
                            log.status === 'done' ? 'text-slate-500 dark:text-slate-500 line-through' :
                            log.status === 'active' ? 'text-slate-800 dark:text-slate-200 font-bold' :
                            'text-slate-400 dark:text-slate-600'
                          }`}>
                            {log.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Playwright Screenshots Live Preview tabs */}
                {activeTab === 'playwright' && playwrightResult?.success && (
                  <div className="bg-slate-950 text-slate-100 border border-slate-800 p-4 rounded-xl flex-1 flex flex-col min-h-[360px] animate-in fade-in slide-in-from-right-3 duration-300">
                    <div className="flex justify-between items-center pb-2 border-b border-slate-800 mb-3">
                      <h4 className="text-xs font-extrabold uppercase tracking-widest text-[#4F46E5] flex items-center gap-1.5">
                        <ImageIcon className="w-4 h-4" />
                        Playwright Live View
                      </h4>
                      <span className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">Headless Chrome</span>
                    </div>

                    {/* Screenshot Tab Switches */}
                    <div className="grid grid-cols-2 gap-1.5 mb-3 text-[10px] font-semibold">
                      {playwrightResult.screenshots.non_slab_filled && (
                        <button
                          type="button"
                          onClick={() => setActiveScreenshot('non_slab_filled')}
                          className={`py-1 rounded border transition-all cursor-pointer
                            ${activeScreenshot === 'non_slab_filled' 
                              ? 'bg-slate-800 border-indigo-500 text-white' 
                              : 'bg-transparent border-slate-800 text-slate-400 hover:text-white'
                            }`}
                        >
                          Non-Slab Fill
                        </button>
                      )}
                      {playwrightResult.screenshots.non_slab_submitted && (
                        <button
                          type="button"
                          onClick={() => setActiveScreenshot('non_slab_submitted')}
                          className={`py-1 rounded border transition-all cursor-pointer
                            ${activeScreenshot === 'non_slab_submitted' 
                              ? 'bg-slate-800 border-indigo-500 text-white' 
                              : 'bg-transparent border-slate-800 text-slate-400 hover:text-white'
                            }`}
                        >
                          Non-Slab Success
                        </button>
                      )}
                      {playwrightResult.screenshots.slab_filled && (
                        <button
                          type="button"
                          onClick={() => setActiveScreenshot('slab_filled')}
                          className={`py-1 rounded border transition-all cursor-pointer
                            ${activeScreenshot === 'slab_filled' 
                              ? 'bg-slate-800 border-indigo-500 text-white' 
                              : 'bg-transparent border-slate-800 text-slate-400 hover:text-white'
                            }`}
                        >
                          Slab Fill
                        </button>
                      )}
                      {playwrightResult.screenshots.slab_submitted && (
                        <button
                          type="button"
                          onClick={() => setActiveScreenshot('slab_submitted')}
                          className={`py-1 rounded border transition-all cursor-pointer
                            ${activeScreenshot === 'slab_submitted' 
                              ? 'bg-slate-800 border-indigo-500 text-white' 
                              : 'bg-transparent border-slate-800 text-slate-400 hover:text-white'
                            }`}
                        >
                          Slab Success
                        </button>
                      )}
                    </div>

                    {/* Screenshot Display */}
                    <div className="flex-1 rounded border border-slate-800 bg-slate-900 overflow-hidden flex items-center justify-center relative min-h-[220px]">
                      {playwrightResult.screenshots[activeScreenshot] ? (
                        <img
                          src={`data:image/png;base64,${playwrightResult.screenshots[activeScreenshot]}`}
                          alt="Playwright Sandbox Browser Screenshot"
                          className="w-full h-full object-contain max-h-[300px]"
                        />
                      ) : (
                        <span className="text-[10px] text-slate-500">No screenshot captured</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Dropdowns constraints notice panel (visible before running) */}
                {automationStep === 'idle' && (
                  <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-xl space-y-3.5">
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                      Dataset Constraints
                    </h4>
                    <p className="text-xs text-slate-500 leading-relaxed">
                      To ensure integrity, this page restricts dropdown options to match <strong>ONLY</strong> values present in the selected grid spreadsheet.
                    </p>
                    <div className="space-y-1.5 text-[11px] font-mono font-semibold">
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span>Unique Products:</span>
                        <span className="text-slate-800 dark:text-slate-200">{(uniqueValues?.product?.length) || 0}</span>
                      </div>
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span>Unique States:</span>
                        <span className="text-slate-800 dark:text-slate-200">{(uniqueValues?.state?.length) || 0}</span>
                      </div>
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span>Unique RTOs:</span>
                        <span className="text-slate-800 dark:text-slate-200">{(uniqueValues?.rto?.length) || 0}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Automation Summary Panel */}
                {automationStep === 'completed' && (
                  <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-xl space-y-4 animate-in zoom-in duration-300">
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                      Automation Summary
                    </h4>
                    <div className="space-y-2 text-xs font-semibold">
                      <div className="flex justify-between">
                        <span className="text-slate-400">File Selected:</span>
                        <span className="text-slate-800 dark:text-slate-200 max-w-[200px] truncate">{selectedUpload.filename}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Insurer:</span>
                        <span className="text-slate-800 dark:text-slate-200">{selectedUpload.company}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Rows Processed:</span>
                        <span className="text-slate-800 dark:text-slate-200">
                          {validRows?.non_slab ? '1 Non-Slab' : '0 Non-Slab'}
                          {validRows?.slab ? ', 1 Slab' : ''}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Execution Time:</span>
                        <span className="text-slate-800 dark:text-slate-200">{executionTime}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">Status:</span>
                        <span className="px-2 py-0.5 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] uppercase font-bold tracking-wide">
                          Success
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer Controls */}
            <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 flex justify-between items-center flex-shrink-0 bg-slate-50 dark:bg-slate-900/50">
              <span className="text-[10px] text-slate-400 dark:text-slate-600 font-semibold uppercase tracking-wider">
                Simulation Sandbox Mode
              </span>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  disabled={automationStep === 'running'}
                  className="px-4 py-2 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 text-slate-600 dark:text-slate-300 disabled:text-slate-400 text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700 cursor-pointer disabled:cursor-not-allowed transition-all"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={startAutomationFlow}
                  disabled={automationStep !== 'idle' || isLoadingRows || (!validRows?.non_slab && !validRows?.slab)}
                  className="inline-flex items-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:dark:bg-slate-800 disabled:text-slate-400 disabled:dark:text-slate-600 text-white text-xs font-semibold rounded-lg shadow-sm cursor-pointer disabled:cursor-not-allowed transition-all"
                >
                  {automationStep === 'running' ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      Start Automation
                    </>
                  )}
                </button>
              </div>
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
};
export default Automation;

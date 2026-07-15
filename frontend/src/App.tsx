import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './services/api';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Dashboard } from './pages/Dashboard';
import { CustomiseData } from './pages/CustomiseData';
import { DashboardHome } from './pages/DashboardHome';
import { Automation } from './pages/Automation';
import { MockCRM } from './pages/MockCRM';
import { useNotification } from './contexts/NotificationContext';

const getInitialTab = (): 'dashboard' | 'upload' | 'customise' | 'automation' => {
  const path = window.location.pathname.replace(/^\//, '');
  if (path === 'automation') return 'automation';
  if (path === 'dashboard') return 'dashboard';
  if (path === 'customise') return 'customise';
  return 'upload';
};

function App() {
  const queryClient = useQueryClient();
  const { notify } = useNotification();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'upload' | 'customise' | 'automation'>(getInitialTab);
  const [selectedUploadId, setSelectedUploadId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const [filters, setFilters] = useState<Record<string, string>>({
    search: '',
    lob: '',
    file_type: '',
    company: '',
    product: '',
    policy_type: '',
    plan_type: '',
    sub_product: '',
    class: '',
    sub_class: '',
    make: '',
    model: '',
    fuel_type: '',
    body_type: '',
    cpa_status: '',
    ncb_status: '',
    partner_type: '',
    state: '',
    zone: '',
    source: '',
    rto: '',
    effective_date: '',
    remarks: '',
    validation_status: '',
    // Defaults to 'NON_SLAB' (not '') so the very first query sent to the
    // backend actually matches the visually-active "Non-Slab" tab — an empty
    // string applies no commission_type filter at all, which silently
    // returned mixed SLAB/NON_SLAB rows under the "Non-Slab" tab until the
    // user explicitly clicked a tab once.
    commission_type: 'NON_SLAB',
    hasSlabs: '',
    vehicleAge: '',
  });

  // Fetch uploads history
  const { data: uploads = [], isLoading: isUploadsLoading } = useQuery({
    queryKey: ['uploads'],
    queryFn: api.getUploads,
    refetchInterval: (query) => {
      const data = query?.state?.data as any[] | undefined;
      const processingExists = data?.some(u => u.status === 'PROCESSING');
      return processingExists ? 4000 : false;
    },
  });

  // Auto-select the first upload once list loads
  useEffect(() => {
    if (uploads.length > 0 && selectedUploadId === null) {
      setSelectedUploadId(uploads[0].id);
    }
  }, [uploads, selectedUploadId]);

  // Fetch rules for the selected upload
  const { data: recordsData, isLoading: isRecordsLoading } = useQuery({
    queryKey: ['records', selectedUploadId, page, filters],
    queryFn: () => {
      if (selectedUploadId === null) return null;
      const cleanParams: Record<string, any> = {
        page,
        limit: 50,
      };
      Object.entries(filters).forEach(([key, val]) => {
        if (val) {
          // Map frontend filter name to backend API field names
          if (key === 'company') {
            cleanParams['company'] = val;
          } else if (key === 'status' || key === 'validation_status') {
            cleanParams['validation_status'] = val;
          } else if (key === 'hasSlabs') {
            cleanParams['has_slabs'] = val;
          } else if (key === 'vehicleAge') {
            cleanParams['vehicle_age'] = val;
          } else {
            cleanParams[key] = val;
          }
        }
      });
      return api.getExtractedRecords(selectedUploadId, cleanParams);
    },
    enabled: selectedUploadId !== null && activeTab === 'upload',
  });

  // Reset page on filter/upload change
  useEffect(() => { setPage(1); }, [filters, selectedUploadId]);

  // Track status transition for notifications and refetching
  const [prevStatuses, setPrevStatuses] = useState<Record<number, string>>({});

  useEffect(() => {
    if (uploads.length > 0) {
      uploads.forEach((u) => {
        const prevStatus = prevStatuses[u.id];
        if (prevStatus === 'PROCESSING' && u.status === 'COMPLETED') {
          if (u.id === selectedUploadId) {
            queryClient.invalidateQueries({ queryKey: ['records', u.id] });
            queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
          }
          notify(
            `Successfully processed "${u.filename}" — extracted ${u.total_records.toLocaleString()} commission rules.`,
            'success'
          );
        } else if (prevStatus === 'PROCESSING' && u.status === 'FAILED') {
          notify(`Failed to process "${u.filename}". Please check the file format.`, 'error');
        }
      });

      const nextStatuses: Record<number, string> = {};
      uploads.forEach((u) => {
        nextStatuses[u.id] = u.status;
      });
      if (JSON.stringify(nextStatuses) !== JSON.stringify(prevStatuses)) {
        setPrevStatuses(nextStatuses);
      }
    }
  }, [uploads, selectedUploadId, prevStatuses, queryClient, notify]);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: api.uploadFile,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['uploads'] });
      queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
      setSelectedUploadId(data.upload_id);
      setActiveTab('upload');
      setPage(1);
      notify(
        'File uploaded successfully. Detecting and extracting rules...',
        'info'
      );
    },
    onError: (err: any) => {
      notify(`Upload failed: ${err.response?.data?.detail || err.message}`, 'error');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: api.deleteUpload,
    onSuccess: (_data, deletedId) => {
      queryClient.setQueryData<any[]>(['uploads'], (old) => old?.filter(u => u.id !== deletedId) ?? []);
      if (selectedUploadId === deletedId) {
        const remaining = uploads.filter(u => u.id !== deletedId);
        setSelectedUploadId(remaining.length > 0 ? remaining[0].id : null);
      }
      queryClient.invalidateQueries({ queryKey: ['uploads'] });
      setPage(1);
      notify('Upload and all extracted rules deleted successfully.', 'success');
    },
    onError: (err: any) => {
      notify(`Deletion failed: ${err.message}`, 'error');
    },
  });

  // Rename mutation
  const renameMutation = useMutation({
    mutationFn: ({ id, filename }: { id: number; filename: string }) =>
      api.renameUpload(id, filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploads'] });
      notify('File renamed successfully.', 'success');
    },
    onError: (err: any) => {
      notify(`Rename failed: ${err.response?.data?.detail || err.message}`, 'error');
    },
  });

  const handleUploadFile = (file: File) => uploadMutation.mutate(file);
  const handleDeleteUpload = (id: number) => deleteMutation.mutate(id);
  const handleRenameUpload = (id: number, filename: string) => renameMutation.mutate({ id, filename });
  const handleSelectUpload = (id: number) => { setSelectedUploadId(id); setPage(1); };
  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['uploads'] });
    queryClient.invalidateQueries({ queryKey: ['filterOptions'] });
    if (selectedUploadId !== null) {
      queryClient.invalidateQueries({ queryKey: ['records', selectedUploadId] });
    }
    notify('Dashboard refreshed successfully.', 'success');
  };

  const handleTabChange = (tab: 'dashboard' | 'upload' | 'customise' | 'automation') => {
    setActiveTab(tab);
    window.history.pushState(null, '', '/' + (tab === 'upload' ? '' : tab));
  };

  useEffect(() => {
    const handlePopState = () => {
      setActiveTab(getInitialTab());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  if (window.location.pathname === '/mock-crm') {
    return <MockCRM />;
  }

  return (
    <>
      {/* DashboardLayout now only handles sidebar + top nav */}
      <DashboardLayout activeTab={activeTab} onTabChange={handleTabChange}>
        {activeTab === 'dashboard' ? (
          <DashboardHome />
        ) : activeTab === 'upload' ? (
          <Dashboard
            /* table data */
            records={recordsData?.records || []}
            totalRecords={recordsData?.metadata?.total || 0}
            currentPage={page}
            totalPages={recordsData?.metadata?.pages || 0}
            isLoading={isRecordsLoading}
            filename={recordsData?.metadata?.filename || ''}
            company={recordsData?.metadata?.company || ''}
            onPageChange={setPage}
            filters={filters}
            setFilters={setFilters}
            onRefresh={handleRefresh}
            /* upload history — now lives in Dashboard's HistoryDrawer */
            uploads={uploads}
            selectedUploadId={selectedUploadId}
            onSelectUpload={handleSelectUpload}
            onDeleteUpload={handleDeleteUpload}
            onRenameUpload={handleRenameUpload}
            isUploadsLoading={isUploadsLoading}
            onUploadFile={handleUploadFile}
            isUploading={uploadMutation.isPending}
          />
        ) : activeTab === 'automation' ? (
          <Automation />
        ) : (
          <CustomiseData />
        )}
      </DashboardLayout>
    </>
  );
}

export default App;

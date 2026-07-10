export interface UploadHistory {
  id: number;
  filename: string;
  company: string | null;
  uploaded_by: string | null;
  uploaded_at: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  total_records: number;
}

export interface SlabDetail {
  id: number;
  payin_type: string | null;
  premium_type: string | null;
  slab_from: number | null;
  slab_to: number | null;
  payin_od: number | null;
  payout_od: number | null;
  payin_tp: number | null;
  payout_tp: number | null;
  payin_net: number | null;
  payout_net: number | null;
}

export interface CommissionRule {
  id: number;
  upload_id: number;
  sheet_name: string;
  lob: string | null;
  file_type: string | null;
  insurance_company: string | null;
  product: string | null;
  product_label?: string | null;
  policy_type: string | null;
  plan_type: string | null;
  sub_product: string | null;
  class: string | null;
  sub_class: string | null;
  make: string | null;
  model: string | null;
  fuel_type: string | null;
  body_type: string | null;
  vehicle_age_from: number | null;
  vehicle_age_to: number | null;
  cpa_status: string | null;
  ncb_status: string | null;
  partner_type: string | null;
  state: string | null;
  state_label?: string | null;
  zone: string | null;
  source: string | null;
  rto: string | null;
  effective_date: string | null;
  remarks: string | null;
  validation_status: 'VALID' | 'WARNING';
  warnings: string[] | null;
  raw_json?: Record<string, unknown> | null;
  commission_type: 'SLAB' | 'NON_SLAB';
  commissionType?: 'SLAB' | 'NON_SLAB';
  slab_configuration: boolean;
  slabConfiguration?: boolean;
  payin_od: number | null;
  payout_od: number | null;
  payin_tp: number | null;
  payout_tp: number | null;
  payin_net: number | null;
  payout_net: number | null;
  payin_reward: number | null;
  payout_reward: number | null;
  payin_scheme: number | null;
  payout_scheme: number | null;
  slabs: SlabDetail[];
}

export interface PaginationMetadata {
  total: number;
  page: number;
  limit: number;
  pages: number;
  filename: string;
  company: string;
}

export interface ExtractedRecordsResponse {
  metadata: PaginationMetadata;
  records: CommissionRule[];
}

export interface MasterListItem {
  code: string;
  name: string;
}

/** Fields the backend PATCH /api/commission-rule/{id} endpoint accepts. */
export type EditableRuleField =
  | 'lob' | 'file_type' | 'insurance_company' | 'product' | 'policy_type' | 'plan_type'
  | 'sub_product' | 'class' | 'sub_class' | 'make' | 'model' | 'fuel_type'
  | 'body_type' | 'cpa_status' | 'ncb_status' | 'partner_type' | 'state'
  | 'zone' | 'source' | 'rto' | 'remarks' | 'vehicle_age_from' | 'vehicle_age_to'
  | 'effective_date' | 'commission_type'
  | 'payin_od' | 'payout_od' | 'payin_tp' | 'payout_tp' | 'payin_net' | 'payout_net'
  | 'payin_reward' | 'payout_reward' | 'payin_scheme' | 'payout_scheme';

/** Fields the backend PATCH /api/slab-detail/{id} endpoint accepts. */
export type EditableSlabField =
  | 'payin_type' | 'premium_type' | 'slab_from' | 'slab_to'
  | 'payin_od' | 'payout_od' | 'payin_tp' | 'payout_tp' | 'payin_net' | 'payout_net';

/**
 * Agency API client — Phase A5.
 *
 * Wrappers over /api/agency/* — the rebuilt agent dashboard
 * (suppliers + foreign buyers + portfolio) hangs off these.
 */

import { api } from "@/api/client";

export interface Supplier {
  id: string;
  agent_company_id: string;
  name: string;
  country: string | null;
  factory_address: string | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  notes: string | null;
  foreign_buyer_id: string | null;
  created_at: string;
  updated_at: string;
  active_lc_count: number;
  open_discrepancy_count: number;
}

export interface SupplierInput {
  name: string;
  country?: string | null;
  factory_address?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  notes?: string | null;
  foreign_buyer_id?: string | null;
}

export interface ForeignBuyer {
  id: string;
  agent_company_id: string;
  name: string;
  country: string | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ForeignBuyerInput {
  name: string;
  country?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  notes?: string | null;
}

export interface PortfolioActivity {
  validation_session_id: string;
  supplier_id: string | null;
  supplier_name: string | null;
  lifecycle_state: string | null;
  status: string;
  created_at: string;
}

export interface Portfolio {
  supplier_count: number;
  foreign_buyer_count: number;
  active_lc_count: number;
  open_discrepancy_count: number;
  completed_this_month: number;
  recent_activity: PortfolioActivity[];
}

// ---- Suppliers ----------------------------------------------------------

export async function listSuppliers(): Promise<Supplier[]> {
  const { data } = await api.get<Supplier[]>("/api/agency/suppliers");
  return data ?? [];
}

export async function createSupplier(input: SupplierInput): Promise<Supplier> {
  const { data } = await api.post<Supplier>("/api/agency/suppliers", input);
  return data;
}

export async function getSupplier(id: string): Promise<Supplier> {
  const { data } = await api.get<Supplier>(`/api/agency/suppliers/${id}`);
  return data;
}

export async function updateSupplier(
  id: string,
  patch: Partial<SupplierInput>,
): Promise<Supplier> {
  const { data } = await api.patch<Supplier>(`/api/agency/suppliers/${id}`, patch);
  return data;
}

export async function deleteSupplier(id: string): Promise<void> {
  await api.delete(`/api/agency/suppliers/${id}`);
}

// ---- Foreign Buyers -----------------------------------------------------

export async function listBuyers(): Promise<ForeignBuyer[]> {
  const { data } = await api.get<ForeignBuyer[]>("/api/agency/buyers");
  return data ?? [];
}

export async function createBuyer(input: ForeignBuyerInput): Promise<ForeignBuyer> {
  const { data } = await api.post<ForeignBuyer>("/api/agency/buyers", input);
  return data;
}

export async function getBuyer(id: string): Promise<ForeignBuyer> {
  const { data } = await api.get<ForeignBuyer>(`/api/agency/buyers/${id}`);
  return data;
}

export async function updateBuyer(
  id: string,
  patch: Partial<ForeignBuyerInput>,
): Promise<ForeignBuyer> {
  const { data } = await api.patch<ForeignBuyer>(`/api/agency/buyers/${id}`, patch);
  return data;
}

export async function deleteBuyer(id: string): Promise<void> {
  await api.delete(`/api/agency/buyers/${id}`);
}

// ---- Portfolio ----------------------------------------------------------

export async function getPortfolio(): Promise<Portfolio> {
  const { data } = await api.get<Portfolio>("/api/agency/portfolio");
  return data;
}

// ---- Re-papering coordination (Phase A7) -------------------------------

export interface AgencyRepaperingRequest {
  id: string;
  discrepancy_id: string;
  discrepancy_description: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  recipient_email: string;
  recipient_display_name: string | null;
  state: string;
  message: string | null;
  created_at: string;
  opened_at: string | null;
  submitted_at: string | null;
  resolved_at: string | null;
  cancelled_at: string | null;
  replacement_session_id: string | null;
  requester_user_id: string | null;
  access_token: string | null;
}

export async function listAgencyRepaperRequests(opts?: {
  onlyOpen?: boolean;
}): Promise<AgencyRepaperingRequest[]> {
  const params = new URLSearchParams();
  if (opts?.onlyOpen) params.set("only_open", "true");
  const query = params.toString();
  const path = query
    ? `/api/agency/repaper-requests?${query}`
    : "/api/agency/repaper-requests";
  const { data } = await api.get<AgencyRepaperingRequest[]>(path);
  return data ?? [];
}

export async function resendAgencyRepaperEmail(
  requestId: string,
): Promise<{ sent: boolean; recipient: string }> {
  const { data } = await api.post<{ sent: boolean; recipient: string }>(
    `/api/agency/repaper-requests/${requestId}/resend-email`,
  );
  return data;
}

export async function cancelAgencyRepaperRequest(
  requestId: string,
): Promise<void> {
  // Reuses the existing requester-cancel endpoint from Phase A2.
  await api.post(`/api/repaper/${requestId}/cancel`);
}

// ---- Reports (Phase A7 slice 3) ----------------------------------------

export interface SupplierReportRecentSession {
  validation_session_id: string;
  lifecycle_state: string | null;
  status: string;
  findings_count: number;
  created_at: string;
}

export interface SupplierReportData {
  supplier_id: string;
  supplier_name: string;
  country: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  foreign_buyer_id: string | null;
  foreign_buyer_name: string | null;
  total_sessions: number;
  active_sessions: number;
  completed_this_month: number;
  total_discrepancies: number;
  open_discrepancies: number;
  repaper_requests: number;
  repaper_open: number;
  discrepancy_rate: number;
  recent_sessions: SupplierReportRecentSession[];
  generated_at: string;
}

export interface BuyerReportSupplier {
  supplier_id: string;
  supplier_name: string;
  country: string | null;
  total_sessions: number;
  active_sessions: number;
  open_discrepancies: number;
}

export interface BuyerReportData {
  buyer_id: string;
  buyer_name: string;
  country: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  supplier_count: number;
  total_sessions: number;
  active_sessions: number;
  open_discrepancies: number;
  suppliers: BuyerReportSupplier[];
  generated_at: string;
}

export async function getSupplierReport(
  supplierId: string,
): Promise<SupplierReportData> {
  const { data } = await api.get<SupplierReportData>(
    `/api/agency/reports/supplier/${supplierId}`,
  );
  return data;
}

export async function getBuyerReport(
  buyerId: string,
): Promise<BuyerReportData> {
  const { data } = await api.get<BuyerReportData>(
    `/api/agency/reports/buyer/${buyerId}`,
  );
  return data;
}

export function supplierReportPdfUrl(supplierId: string): string {
  // Bare API URL — let the user open it in a new tab; axios bearer-auth +
  // CSRF cookies ride on cross-origin requests automatically.
  const base = (api.defaults.baseURL ?? "").replace(/\/$/, "");
  return `${base}/api/agency/reports/supplier/${supplierId}.pdf`;
}

export function buyerReportPdfUrl(buyerId: string): string {
  const base = (api.defaults.baseURL ?? "").replace(/\/$/, "");
  return `${base}/api/agency/reports/buyer/${buyerId}.pdf`;
}

/**
 * Trigger a PDF download with the existing axios auth/CSRF stack.
 * Browser <a href> won't carry the bearer header so we fetch + create
 * a Blob URL on the fly.
 */
export async function downloadSupplierReportPdf(
  supplierId: string,
  filename = "supplier-report.pdf",
): Promise<void> {
  const { data } = await api.get<Blob>(
    `/api/agency/reports/supplier/${supplierId}.pdf`,
    { responseType: "blob" },
  );
  triggerBlobDownload(data, filename);
}

export async function downloadBuyerReportPdf(
  buyerId: string,
  filename = "buyer-report.pdf",
): Promise<void> {
  const { data } = await api.get<Blob>(
    `/api/agency/reports/buyer/${buyerId}.pdf`,
    { responseType: "blob" },
  );
  triggerBlobDownload(data, filename);
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Defer revoke so the browser actually finishes the download
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

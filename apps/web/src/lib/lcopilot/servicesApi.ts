/**
 * Services API client — Phases A8 + A9.
 *
 * CRUD for clients + time entries, the portfolio snapshot, and the
 * invoice generator (preview + PDF).
 */

import { api } from "@/api/client";

export interface ServicesClient {
  id: string;
  services_company_id: string;
  name: string;
  country: string | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  notes: string | null;
  billing_rate: number | string | null;
  retainer_active: boolean;
  retainer_hours_per_month: number | string | null;
  created_at: string;
  updated_at: string;
  active_lc_count: number;
  open_discrepancy_count: number;
  hours_this_month: number | string;
  billable_hours_unbilled: number | string;
}

export interface ServicesClientInput {
  name: string;
  country?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  notes?: string | null;
  billing_rate?: number | null;
  retainer_active?: boolean;
  retainer_hours_per_month?: number | null;
}

export interface TimeEntry {
  id: string;
  services_company_id: string;
  services_client_id: string;
  validation_session_id: string | null;
  user_id: string | null;
  hours: number | string;
  description: string | null;
  billable: boolean;
  billed: boolean;
  performed_on: string | null;
  created_at: string;
  updated_at: string;
}

export interface TimeEntryInput {
  services_client_id: string;
  validation_session_id?: string | null;
  hours: number;
  description?: string | null;
  billable?: boolean;
  performed_on?: string | null;
}

export interface ServicesPortfolio {
  client_count: number;
  active_lc_count: number;
  open_discrepancy_count: number;
  completed_this_month: number;
  hours_this_month: number | string;
  billable_hours_unbilled: number | string;
  recent_activity: Array<{
    validation_session_id: string;
    services_client_id: string | null;
    client_name: string | null;
    lifecycle_state: string | null;
    status: string;
    created_at: string;
  }>;
}

export interface InvoicePreview {
  client_id: string;
  client_name: string;
  period_start: string;
  period_end: string;
  lines: Array<{
    time_entry_id: string;
    description: string | null;
    hours: number | string;
    rate: number | string;
    line_total: number | string;
    performed_on: string | null;
  }>;
  lcs: Array<{
    validation_session_id: string;
    lifecycle_state: string | null;
    status: string;
    created_at: string;
  }>;
  total_hours: number | string;
  total_amount: number | string;
  rate: number | string;
  generated_at: string;
}

export interface InvoiceGenerateInput {
  client_id: string;
  period_start: string;
  period_end: string;
  rate_override?: number | null;
  mark_billed?: boolean;
}

// ---- Clients ------------------------------------------------------------

export async function listServicesClients(): Promise<ServicesClient[]> {
  const { data } = await api.get<ServicesClient[]>("/api/services/clients");
  return data ?? [];
}

export async function createServicesClient(
  input: ServicesClientInput,
): Promise<ServicesClient> {
  const { data } = await api.post<ServicesClient>("/api/services/clients", input);
  return data;
}

export async function getServicesClient(id: string): Promise<ServicesClient> {
  const { data } = await api.get<ServicesClient>(`/api/services/clients/${id}`);
  return data;
}

export async function updateServicesClient(
  id: string,
  patch: Partial<ServicesClientInput>,
): Promise<ServicesClient> {
  const { data } = await api.patch<ServicesClient>(
    `/api/services/clients/${id}`,
    patch,
  );
  return data;
}

export async function deleteServicesClient(id: string): Promise<void> {
  await api.delete(`/api/services/clients/${id}`);
}

// ---- Time entries -------------------------------------------------------

export async function listTimeEntries(opts?: {
  clientId?: string;
  onlyUnbilled?: boolean;
  limit?: number;
}): Promise<TimeEntry[]> {
  const params = new URLSearchParams();
  if (opts?.clientId) params.set("client_id", opts.clientId);
  if (opts?.onlyUnbilled) params.set("only_unbilled", "true");
  if (opts?.limit) params.set("limit", String(opts.limit));
  const query = params.toString();
  const path = query ? `/api/services/time?${query}` : "/api/services/time";
  const { data } = await api.get<TimeEntry[]>(path);
  return data ?? [];
}

export async function createTimeEntry(input: TimeEntryInput): Promise<TimeEntry> {
  const { data } = await api.post<TimeEntry>("/api/services/time", input);
  return data;
}

export async function updateTimeEntry(
  id: string,
  patch: Partial<TimeEntryInput> & { billed?: boolean },
): Promise<TimeEntry> {
  const { data } = await api.patch<TimeEntry>(`/api/services/time/${id}`, patch);
  return data;
}

export async function deleteTimeEntry(id: string): Promise<void> {
  await api.delete(`/api/services/time/${id}`);
}

// ---- Portfolio ----------------------------------------------------------

export async function getServicesPortfolio(): Promise<ServicesPortfolio> {
  const { data } = await api.get<ServicesPortfolio>("/api/services/portfolio");
  return data;
}

// ---- Invoices -----------------------------------------------------------

export async function generateInvoicePreview(
  body: InvoiceGenerateInput,
): Promise<InvoicePreview> {
  const { data } = await api.post<InvoicePreview>(
    "/api/services/invoices/generate",
    body,
  );
  return data;
}

export async function downloadInvoicePdf(
  body: InvoiceGenerateInput,
  filename = "invoice.pdf",
): Promise<void> {
  const { data } = await api.post<Blob>(
    "/api/services/invoices/generate.pdf",
    body,
    { responseType: "blob" },
  );
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

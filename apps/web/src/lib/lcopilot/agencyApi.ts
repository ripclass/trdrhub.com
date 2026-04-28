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

/**
 * Company Profile API service
 */
import { api } from "@/api/client";

export interface CompanyAddress {
  id: string;
  company_id: string;
  label: string;
  address_type: "business" | "shipping" | "billing" | "warehouse" | "custom";
  street_address: string;
  city: string;
  state_province?: string;
  postal_code?: string;
  country: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  is_default_shipping: boolean;
  is_default_billing: boolean;
  is_active: boolean;
  metadata_?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CompanyComplianceInfo {
  id: string;
  company_id: string;
  tax_id?: string;
  vat_number?: string;
  registration_number?: string;
  regulator_id?: string;
  compliance_status: "pending" | "verified" | "expired" | "rejected";
  verified_at?: string;
  verified_by?: string;
  expiry_date?: string;
  compliance_documents?: Array<Record<string, any>>;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface DefaultConsigneeShipper {
  id: string;
  company_id: string;
  type_: "consignee" | "shipper";
  company_name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  address_id?: string;
  street_address?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  bank_name?: string;
  bank_account?: string;
  swift_code?: string;
  is_active: boolean;
  metadata_?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CompanyAddressCreate {
  company_id: string;
  label: string;
  address_type: "business" | "shipping" | "billing" | "warehouse" | "custom";
  street_address: string;
  city: string;
  state_province?: string;
  postal_code?: string;
  country: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  is_default_shipping?: boolean;
  is_default_billing?: boolean;
  metadata_?: Record<string, any>;
}

export interface CompanyComplianceInfoCreate {
  company_id: string;
  tax_id?: string;
  vat_number?: string;
  registration_number?: string;
  regulator_id?: string;
  compliance_status?: "pending" | "verified" | "expired" | "rejected";
  expiry_date?: string;
  compliance_documents?: Array<Record<string, any>>;
  notes?: string;
}

export interface DefaultConsigneeShipperCreate {
  company_id: string;
  type_: "consignee" | "shipper";
  company_name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  address_id?: string;
  street_address?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  bank_name?: string;
  bank_account?: string;
  swift_code?: string;
  metadata_?: Record<string, any>;
}

class CompanyProfileService {
  private baseUrl = "/api/company-profile";

  // Address endpoints
  async listAddresses(params?: {
    address_type?: string;
    active_only?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<{ total: number; page: number; page_size: number; items: CompanyAddress[] }> {
    const response = await api.get(`${this.baseUrl}/addresses`, { params });
    return response.data;
  }

  async getAddress(addressId: string): Promise<CompanyAddress> {
    const response = await api.get(`${this.baseUrl}/addresses/${addressId}`);
    return response.data;
  }

  async createAddress(data: CompanyAddressCreate): Promise<CompanyAddress> {
    const response = await api.post(`${this.baseUrl}/addresses`, data);
    return response.data;
  }

  async updateAddress(addressId: string, data: Partial<CompanyAddressCreate>): Promise<CompanyAddress> {
    const response = await api.patch(`${this.baseUrl}/addresses/${addressId}`, data);
    return response.data;
  }

  async deleteAddress(addressId: string): Promise<void> {
    await api.delete(`${this.baseUrl}/addresses/${addressId}`);
  }

  // Compliance endpoints
  async getComplianceInfo(): Promise<CompanyComplianceInfo> {
    const response = await api.get(`${this.baseUrl}/compliance`);
    return response.data;
  }

  async upsertComplianceInfo(data: CompanyComplianceInfoCreate): Promise<CompanyComplianceInfo> {
    const response = await api.post(`${this.baseUrl}/compliance`, data);
    return response.data;
  }

  async updateComplianceInfo(data: Partial<CompanyComplianceInfoCreate>): Promise<CompanyComplianceInfo> {
    const response = await api.patch(`${this.baseUrl}/compliance`, data);
    return response.data;
  }

  // Consignee/Shipper endpoints
  async listConsigneeShipper(params?: {
    type?: string;
    active_only?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<{ total: number; page: number; page_size: number; items: DefaultConsigneeShipper[] }> {
    const response = await api.get(`${this.baseUrl}/consignee-shipper`, { params });
    return response.data;
  }

  async getConsigneeShipper(id: string): Promise<DefaultConsigneeShipper> {
    const response = await api.get(`${this.baseUrl}/consignee-shipper/${id}`);
    return response.data;
  }

  async createConsigneeShipper(data: DefaultConsigneeShipperCreate): Promise<DefaultConsigneeShipper> {
    const response = await api.post(`${this.baseUrl}/consignee-shipper`, data);
    return response.data;
  }

  async updateConsigneeShipper(id: string, data: Partial<DefaultConsigneeShipperCreate>): Promise<DefaultConsigneeShipper> {
    const response = await api.patch(`${this.baseUrl}/consignee-shipper/${id}`, data);
    return response.data;
  }

  async deleteConsigneeShipper(id: string): Promise<void> {
    await api.delete(`${this.baseUrl}/consignee-shipper/${id}`);
  }
}

export const companyProfileService = new CompanyProfileService();


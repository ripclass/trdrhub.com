/**
 * TypeScript types for billing system
 */

export enum PlanType {
  FREE = 'FREE',
  STARTER = 'STARTER',
  PROFESSIONAL = 'PROFESSIONAL',
  ENTERPRISE = 'ENTERPRISE'
}

export enum InvoiceStatus {
  PENDING = 'PENDING',
  PAID = 'PAID',
  OVERDUE = 'OVERDUE',
  CANCELLED = 'CANCELLED',
  FAILED = 'FAILED'
}

export enum SettlementStatus {
  PENDING = 'PENDING',
  PROCESSED = 'PROCESSED',
  RECONCILED = 'RECONCILED',
  DISPUTED = 'DISPUTED'
}

export enum PaymentProvider {
  SSLCOMMERZ = 'sslcommerz',
  STRIPE = 'stripe'
}

export enum Currency {
  BDT = 'BDT',
  USD = 'USD'
}

export interface CompanyBillingInfo {
  id: string;
  name: string;
  plan: PlanType;
  quota_limit: number | null;
  quota_used: number;
  quota_remaining: number | null;
  billing_email: string | null;
  payment_customer_id: string | null;
}

export interface UsageStats {
  company_id: string;
  current_month: number;
  current_week: number;
  today: number;
  total_usage: number;
  total_cost: number;
  quota_limit: number | null;
  quota_used: number;
  quota_remaining: number | null;
}

export interface UsageRecord {
  id: string;
  company_id: string;
  user_id: string | null;
  session_id: string | null;
  action: string;
  cost: number;
  created_at: string;
  updated_at: string | null;
  metadata: Record<string, any> | null;
}

export interface UsageRecordList {
  records: UsageRecord[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
}

export interface Invoice {
  id: string;
  company_id: string;
  invoice_number: string;
  amount: number;
  currency: Currency;
  status: InvoiceStatus;
  issued_date: string;
  due_date: string;
  paid_date: string | null;
  payment_intent_id: string | null;
  payment_method: string | null;
  description: string | null;
  line_items: InvoiceLineItem[];
  created_at: string;
  updated_at: string | null;
}

export interface InvoiceList {
  invoices: Invoice[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface PaymentIntent {
  id: string;
  amount: number;
  currency: Currency;
  status: string;
  client_secret: string | null;
  checkout_url: string | null;
  payment_method_types: string[];
  created_at: string;
  expires_at: string | null;
}

export interface PricingInfo {
  per_check: number;
  import_draft: number;
  import_bundle: number;
  currency: Currency;
}

export interface QuotaCheckResult {
  allowed: boolean;
  remaining: number | null;
  limit: number | null;
  message: string | null;
}

// Plan definitions
export interface PlanFeatures {
  name: string;
  quota: number | null;
  price: number;
  currency: Currency;
  features: string[];
  popular?: boolean;
}

export const PLAN_DEFINITIONS: Record<PlanType, PlanFeatures> = {
  [PlanType.FREE]: {
    name: 'Free',
    quota: 5,
    price: 0,
    currency: Currency.BDT,
    features: ['5 LC validations per month', 'Basic validation features', 'Email support']
  },
  [PlanType.STARTER]: {
    name: 'Starter',
    quota: 100,
    price: 15000,
    currency: Currency.BDT,
    features: ['100 LC validations per month', 'Standard features', 'Priority email support', 'Usage analytics'],
    popular: true
  },
  [PlanType.PROFESSIONAL]: {
    name: 'Professional',
    quota: 500,
    price: 45000,
    currency: Currency.BDT,
    features: ['500 LC validations per month', 'Advanced features', 'Phone support', 'Custom integrations', 'Advanced analytics']
  },
  [PlanType.ENTERPRISE]: {
    name: 'Enterprise',
    quota: null, // unlimited
    price: 0, // custom pricing
    currency: Currency.BDT,
    features: ['Unlimited validations', 'All features included', 'Dedicated support', 'Custom workflows', 'SLA guarantees']
  }
};

// Admin types
export interface AdminCompanyStats {
  company_id: string;
  company_name: string;
  plan: PlanType;
  total_usage: number;
  total_cost: number;
  quota_limit: number | null;
  quota_used: number;
  last_activity: string | null;
  status: string;
}

export interface AdminUsageReport {
  period_start: string;
  period_end: string;
  total_companies: number;
  total_usage: number;
  total_revenue: number;
  companies: AdminCompanyStats[];
}

export interface SystemBillingKPIs {
  total_revenue_monthly: number;
  active_companies: number;
  delinquent_accounts: number;
  invoices_this_cycle: number;
  average_revenue_per_company: number;
  quota_utilization_average: number;
}

// API request types
export interface UsageRecordsFilters {
  page?: number;
  per_page?: number;
  start_date?: string;
  end_date?: string;
  action?: string;
  // Bank-specific filters
  client_id?: string;
  branch_id?: string;
  product?: string;
}

export interface InvoicesFilters {
  page?: number;
  per_page?: number;
  status?: InvoiceStatus;
  // Bank-specific filters
  client_id?: string;
  branch_id?: string;
  product?: string;
  settlement_status?: SettlementStatus;
}

export interface CheckoutRequest {
  plan: PlanType;
  provider: PaymentProvider;
  return_url?: string;
  cancel_url?: string;
  amount?: number;
  currency?: string;
  priceId?: string;
  quantity?: number;
  mode?: 'payment' | 'subscription';
  metadata?: Record<string, any>;
  paymentMethodTypes?: string[];
}

export interface CompanyBillingUpdate {
  plan?: PlanType;
  quota_limit?: number;
  billing_email?: string;
}

// Bank compliance types
export interface BankComplianceReport {
  period_start: string;
  period_end: string;
  total_companies: number;
  active_companies: number;
  total_usage: number;
  total_revenue: number;
  compliance_score: number;
  usage_trends: BankUsageTrend[];
  plan_distribution: PlanDistribution[];
  compliance_metrics: ComplianceMetric[];
}

export interface BankUsageTrend {
  month: string;
  total_usage: number;
  total_revenue: number;
  active_companies: number;
  compliance_score: number;
  avg_cost_per_company: number;
}

export interface PlanDistribution {
  plan: PlanType;
  companies: number;
  revenue: number;
  percentage: number;
}

export interface ComplianceMetric {
  metric: string;
  score: number;
  status: 'excellent' | 'good' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
  description?: string;
}

export interface SMEMetrics {
  total_companies: number;
  active_companies: number;
  total_usage: number;
  total_revenue: number;
  compliance_score: number;
  avg_monthly_usage: number;
  top_plan: PlanType;
  usage_growth: number;
  revenue_growth: number;
  period: string;
}

export interface ComplianceFilters {
  period: '1m' | '3m' | '6m' | '12m';
  start_date?: string;
  end_date?: string;
  include_inactive?: boolean;
  plan_filter?: PlanType;
}

// Chart data types for analytics
export interface UsageTrendData {
  date: string;
  usage: number;
  cost: number;
}

export interface RevenueTrendData {
  date: string;
  revenue: number;
  plan_breakdown: Record<PlanType, number>;
}

export interface QuotaThresholds {
  warning: number; // percentage (e.g., 80)
  critical: number; // percentage (e.g., 95)
  exceeded: number; // percentage (100)
}

export const DEFAULT_QUOTA_THRESHOLDS: QuotaThresholds = {
  warning: 80,
  critical: 95,
  exceeded: 100
};

// Utility functions
export function formatCurrency(amount: number, currency: Currency = Currency.BDT): string {
  const symbols = {
    [Currency.BDT]: '৳',
    [Currency.USD]: '$'
  };

  return `${symbols[currency]}${amount.toLocaleString()}`;
}

export function getQuotaThreshold(used: number, limit: number | null): 'normal' | 'warning' | 'critical' | 'exceeded' {
  if (!limit) return 'normal';

  const percentage = (used / limit) * 100;

  if (percentage >= DEFAULT_QUOTA_THRESHOLDS.exceeded) return 'exceeded';
  if (percentage >= DEFAULT_QUOTA_THRESHOLDS.critical) return 'critical';
  if (percentage >= DEFAULT_QUOTA_THRESHOLDS.warning) return 'warning';
  return 'normal';
}

export function getPlanDisplayName(plan: PlanType): string {
  return PLAN_DEFINITIONS[plan].name;
}

export function isUnlimitedPlan(plan: PlanType): boolean {
  return PLAN_DEFINITIONS[plan].quota === null;
}

export function getInvoiceStatusColor(status: InvoiceStatus): string {
  switch (status) {
    case InvoiceStatus.PAID:
      return 'text-green-600 bg-green-100';
    case InvoiceStatus.PENDING:
      return 'text-yellow-600 bg-yellow-100';
    case InvoiceStatus.OVERDUE:
    case InvoiceStatus.FAILED:
      return 'text-red-600 bg-red-100';
    case InvoiceStatus.CANCELLED:
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

// Bank-specific types
export interface BankContract {
  id: string;
  bank_id: string;
  contract_number: string;
  plan: PlanType;
  contract_term_months: number;
  start_date: string;
  end_date: string;
  quota_limit: number | null;
  overage_rate: number; // per validation
  billing_contact_name: string;
  billing_contact_email: string;
  billing_contact_phone: string | null;
  po_reference: string | null;
  next_settlement_date: string;
  payment_terms: string; // e.g., "Net-30", "Net-45"
  currency: Currency;
  status: 'active' | 'expired' | 'terminated';
  created_at: string;
  updated_at: string | null;
}

export interface Allocation {
  id: string;
  bank_id: string;
  client_id: string | null; // null for bank-wide allocation
  client_name: string | null;
  branch_id: string | null;
  branch_name: string | null;
  product: string | null; // e.g., "LC_VALIDATION", "RE_CHECK"
  budget_limit: number | null; // null for unlimited
  quota_limit: number | null;
  usage_current_period: number;
  usage_cost_current_period: number;
  remaining_budget: number | null;
  alerts_enabled: boolean;
  alert_threshold_percent: number; // e.g., 80 for 80% warning
  period_start: string;
  period_end: string;
  created_at: string;
  updated_at: string | null;
}

export interface AllocationList {
  allocations: Allocation[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AllocationUpdate {
  budget_limit?: number | null;
  quota_limit?: number | null;
  alerts_enabled?: boolean;
  alert_threshold_percent?: number;
}
/**
 * Billing Invoices Page - invoice management and history
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  FileText,
  Download,
  CreditCard,
  Plus,
  AlertCircle,
  CheckCircle,
  Clock,
  Calendar
} from 'lucide-react';
import { format } from 'date-fns';

// Billing components
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { InvoicesTable } from '@/components/billing/InvoicesTable';

// Hooks
import {
  useInvoices,
  useInvoice,
  useGenerateInvoice,
  useDownloadInvoice,
  useRetryPayment
} from '@/hooks/useBilling';
import { useAuth } from '@/hooks/use-auth';

// Types
import { formatCurrency, getInvoiceStatusColor } from '@/types/billing';
import type { Invoice, InvoiceStatus, InvoicesFilters } from '@/types/billing';
import { RoleType } from '@/types/auth';

export function BillingInvoicesPage() {
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [filters, setFilters] = useState<InvoicesFilters>({
    page: 1,
    per_page: 20
  });

  const { user } = useAuth();

  // Queries
  const { data: invoicesData, isLoading: invoicesLoading } = useInvoices(filters);
  const { data: invoiceDetails, isLoading: invoiceDetailsLoading } = useInvoice(
    selectedInvoice?.id || '',
    { enabled: !!selectedInvoice?.id }
  );

  // Mutations
  const generateInvoice = useGenerateInvoice();
  const downloadInvoice = useDownloadInvoice();
  const retryPayment = useRetryPayment();

  const canGenerateInvoices = user?.role === RoleType.ADMIN || user?.role === RoleType.COMPANY_ADMIN;

  const handleInvoiceClick = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setShowInvoiceModal(true);
  };

  const handleDownloadInvoice = (invoiceId: string) => {
    downloadInvoice.mutate(invoiceId);
  };

  const handleRetryPayment = (invoiceId: string) => {
    retryPayment.mutate({ invoiceId });
  };

  const handleGenerateInvoice = () => {
    const startOfMonth = new Date();
    startOfMonth.setDate(1);
    startOfMonth.setHours(0, 0, 0, 0);

    const endOfMonth = new Date();
    endOfMonth.setMonth(endOfMonth.getMonth() + 1);
    endOfMonth.setDate(0);
    endOfMonth.setHours(23, 59, 59, 999);

    generateInvoice.mutate({
      startDate: startOfMonth.toISOString().split('T')[0],
      endDate: endOfMonth.toISOString().split('T')[0]
    });
  };

  const getStatusSummary = () => {
    if (!invoicesData?.invoices) return null;

    const summary = invoicesData.invoices.reduce((acc, invoice) => {
      acc[invoice.status] = (acc[invoice.status] || 0) + 1;
      return acc;
    }, {} as Record<InvoiceStatus, number>);

    return summary;
  };

  const statusSummary = getStatusSummary();

  if (invoicesLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <BillingBreadcrumb />
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-12 w-full" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Invoices</h1>
          <p className="text-muted-foreground">
            View and manage your billing invoices
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {canGenerateInvoices && (
            <Button
              onClick={handleGenerateInvoice}
              disabled={generateInvoice.isPending}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              {generateInvoice.isPending ? 'Generating...' : 'Generate Invoice'}
            </Button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <BillingNav />

      {/* Status Summary */}
      {statusSummary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{invoicesData?.total || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Paid</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {statusSummary.PAID || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending</CardTitle>
              <Clock className="h-4 w-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">
                {statusSummary.PENDING || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Overdue</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {(statusSummary.OVERDUE || 0) + (statusSummary.FAILED || 0)}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Invoices Table */}
      <InvoicesTable
        initialFilters={filters}
        onInvoiceClick={handleInvoiceClick}
      />

      {/* Invoice Details Modal */}
      <Dialog open={showInvoiceModal} onOpenChange={setShowInvoiceModal}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>Invoice Details</span>
              {selectedInvoice && (
                <Badge
                  variant={selectedInvoice.status === 'PAID' ? 'default' :
                          selectedInvoice.status === 'PENDING' ? 'secondary' : 'destructive'}
                  className={getInvoiceStatusColor(selectedInvoice.status)}
                >
                  {selectedInvoice.status}
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              {selectedInvoice?.invoice_number} • {selectedInvoice && format(new Date(selectedInvoice.issued_date), 'MMMM dd, yyyy')}
            </DialogDescription>
          </DialogHeader>

          {invoiceDetailsLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : selectedInvoice ? (
            <div className="space-y-6">
              {/* Invoice Header */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Amount</h3>
                  <p className="text-2xl font-bold">
                    {formatCurrency(selectedInvoice.amount, selectedInvoice.currency)}
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Due Date</h3>
                  <p className="text-lg">
                    {format(new Date(selectedInvoice.due_date), 'MMMM dd, yyyy')}
                  </p>
                </div>
              </div>

              {/* Payment Information */}
              {selectedInvoice.paid_date && (
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Payment Date</h3>
                  <p className="text-sm">
                    {format(new Date(selectedInvoice.paid_date), 'MMMM dd, yyyy')}
                  </p>
                </div>
              )}

              {/* Line Items */}
              {selectedInvoice.line_items && selectedInvoice.line_items.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    Invoice Items
                  </h3>
                  <div className="space-y-2">
                    {selectedInvoice.line_items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between py-2 border-b last:border-b-0"
                      >
                        <div className="flex-1">
                          <div className="font-medium">{item.description}</div>
                          {item.quantity > 1 && (
                            <div className="text-sm text-muted-foreground">
                              {item.quantity} × {formatCurrency(item.unit_price)}
                            </div>
                          )}
                        </div>
                        <div className="font-medium">
                          {formatCurrency(item.amount)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-between pt-4 border-t">
                <div className="space-x-2">
                  <Button
                    variant="outline"
                    onClick={() => handleDownloadInvoice(selectedInvoice.id)}
                    disabled={downloadInvoice.isPending}
                    className="gap-2"
                  >
                    <Download className="h-4 w-4" />
                    {downloadInvoice.isPending ? 'Downloading...' : 'Download PDF'}
                  </Button>
                </div>

                {(selectedInvoice.status === 'FAILED' || selectedInvoice.status === 'OVERDUE') && (
                  <Button
                    onClick={() => handleRetryPayment(selectedInvoice.id)}
                    disabled={retryPayment.isPending}
                    className="gap-2"
                  >
                    <CreditCard className="h-4 w-4" />
                    {retryPayment.isPending ? 'Processing...' : 'Retry Payment'}
                  </Button>
                )}
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default BillingInvoicesPage;
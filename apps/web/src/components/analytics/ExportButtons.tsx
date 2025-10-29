import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Download,
  FileText,
  FileSpreadsheet,
  ChevronDown,
  Loader2
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { analyticsApi } from "@/api/analytics";
import type { AnalyticsFilters } from "@/types/analytics";

interface ExportButtonsProps {
  filters: AnalyticsFilters;
  className?: string;
  variant?: "default" | "outline" | "ghost";
}

export function ExportButtons({
  filters,
  className,
  variant = "outline"
}: ExportButtonsProps) {
  const [isExporting, setIsExporting] = React.useState(false);
  const { toast } = useToast();

  const getExportParams = () => {
    const params: any = {
      time_range: filters.timeRange,
    };

    if (filters.timeRange === "custom" && filters.startDate && filters.endDate) {
      params.start_date = filters.startDate.toISOString();
      params.end_date = filters.endDate.toISOString();
    }

    return params;
  };

  const handleCsvExport = async () => {
    try {
      setIsExporting(true);

      const params = getExportParams();
      const blob = await analyticsApi.exportCsv(params);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `lcopilot-analytics-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: "Export successful",
        description: "Analytics data has been exported to CSV",
      });
    } catch (error) {
      console.error('Export failed:', error);
      toast({
        title: "Export failed",
        description: "Unable to export analytics data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handlePdfExport = async () => {
    // Stub implementation - could integrate with backend PDF generation
    toast({
      title: "PDF Export",
      description: "PDF export will be available in a future update",
    });
  };

  const handlePrint = () => {
    window.print();
  };

  if (isExporting) {
    return (
      <Button variant={variant} disabled className={className}>
        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        Exporting...
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant={variant} className={className}>
          <Download className="h-4 w-4 mr-2" />
          Export
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={handleCsvExport}>
          <FileSpreadsheet className="h-4 w-4 mr-2" />
          Export as CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handlePdfExport}>
          <FileText className="h-4 w-4 mr-2" />
          Export as PDF
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handlePrint}>
          <FileText className="h-4 w-4 mr-2" />
          Print Report
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Simple CSV export button for tables
interface CsvExportButtonProps {
  data: any[];
  filename?: string;
  className?: string;
}

export function CsvExportButton({
  data,
  filename = "export.csv",
  className
}: CsvExportButtonProps) {
  const { toast } = useToast();

  const handleExport = () => {
    try {
      if (!data || data.length === 0) {
        toast({
          title: "No data",
          description: "There's no data to export",
          variant: "destructive",
        });
        return;
      }

      // Convert data to CSV
      const headers = Object.keys(data[0]);
      const csvContent = [
        headers.join(','),
        ...data.map(row =>
          headers.map(header => {
            const value = row[header];
            // Escape commas and quotes
            return typeof value === 'string' && (value.includes(',') || value.includes('"'))
              ? `"${value.replace(/"/g, '""')}"`
              : value;
          }).join(',')
        )
      ].join('\n');

      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();

      toast({
        title: "Export successful",
        description: `${data.length} records exported to CSV`,
      });
    } catch (error) {
      console.error('CSV export failed:', error);
      toast({
        title: "Export failed",
        description: "Unable to export data to CSV",
        variant: "destructive",
      });
    }
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleExport}
      className={className}
    >
      <FileSpreadsheet className="h-4 w-4 mr-2" />
      Export CSV
    </Button>
  );
}
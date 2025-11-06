import * as React from "react";

import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

export interface DataTableColumn<T> {
  /** Unique key for the column */
  key: string;
  /** Header label */
  header: React.ReactNode;
  /** Optional text alignment */
  align?: "left" | "center" | "right";
  /** Optional width */
  width?: string | number;
  /** Optional custom cell renderer */
  render?: (item: T, index: number) => React.ReactNode;
  /** Optional accessor when `render` not provided */
  accessor?: (item: T) => React.ReactNode;
  /** Optional className for cells */
  className?: string;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  loading?: boolean;
  emptyState?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

const LoadingRow: React.FC<{ columns: number }> = ({ columns }) => (
  <TableRow>
    <TableCell colSpan={columns}>
      <div className="flex flex-col gap-2">
        {Array.from({ length: 3 }).map((_, index) => (
          <Skeleton key={index} className="h-6 w-full" />
        ))}
      </div>
    </TableCell>
  </TableRow>
);

export function DataTable<T>({
  columns,
  data,
  loading,
  emptyState,
  footer,
  className,
}: DataTableProps<T>) {
  const hasData = data.length > 0;

  return (
    <div className={cn("overflow-hidden rounded-lg border border-border/50 bg-card", className)}>
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/40">
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={cn(
                  column.className,
                  column.align === "center" && "text-center",
                  column.align === "right" && "text-right",
                )}
                style={column.width ? { width: column.width } : undefined}
              >
                {column.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <LoadingRow columns={columns.length} />
          ) : hasData ? (
            data.map((item, rowIndex) => (
              <TableRow key={(item as unknown as { id?: string }).id ?? rowIndex}>
                {columns.map((column, colIndex) => {
                  const content = column.render
                    ? column.render(item, rowIndex)
                    : column.accessor
                      ? column.accessor(item)
                      :
                        // @ts-expect-error allow indexed access when no accessor provided
                        (item[column.key as keyof T] as React.ReactNode);
                  return (
                    <TableCell
                      key={`${column.key}-${colIndex}`}
                      className={cn(
                        column.className,
                        column.align === "center" && "text-center",
                        column.align === "right" && "text-right",
                      )}
                    >
                      {content}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length}>
                {emptyState ?? (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    No records found.
                  </div>
                )}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      {footer && <div className="border-t border-border/50 bg-muted/10 p-4">{footer}</div>}
    </div>
  );
}


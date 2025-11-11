/**
 * Duplicate Badge Component
 * Shows duplicate indicator badge with click handler
 */
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Copy } from "lucide-react";

interface DuplicateBadgeProps {
  count: number;
  onClick?: () => void;
  className?: string;
}

export function DuplicateBadge({ count, onClick, className }: DuplicateBadgeProps) {
  if (count === 0) return null;

  return (
    <Badge
      variant="outline"
      className={`text-[10px] h-4 px-1 cursor-pointer hover:bg-muted ${className || ''}`}
      title={`This LC has been validated ${count} time(s) before`}
      onClick={onClick}
    >
      <Copy className="w-2.5 h-2.5 mr-0.5" />
      {count}x
    </Badge>
  );
}


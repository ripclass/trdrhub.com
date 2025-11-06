import * as React from "react";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterGroup {
  /** Label for the filter */
  label: string;
  /** Selected value */
  value: string | string[];
  /** Options for the filter */
  options: FilterOption[];
  /** Callback when selection changes */
  onChange: (value: string | string[]) => void;
  /** Whether multiple values can be selected */
  multi?: boolean;
  /** Optional clear button */
  allowClear?: boolean;
}

interface AdminFiltersProps {
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  filterGroups?: FilterGroup[];
  /** Render additional elements on the right (e.g., date range picker) */
  endAdornment?: React.ReactNode;
  children?: React.ReactNode;
}

export function AdminFilters({
  searchPlaceholder = "Search...",
  searchValue,
  onSearchChange,
  filterGroups,
  endAdornment,
  children,
}: AdminFiltersProps) {
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onSearchChange?.(event.target.value);
  };

  return (
    <div className="flex w-full flex-wrap items-center gap-3">
      {onSearchChange && (
        <div className="flex w-full min-w-[200px] max-w-sm flex-1">
          <Input
            value={searchValue ?? ""}
            onChange={handleSearchChange}
            placeholder={searchPlaceholder}
            className="w-full"
          />
        </div>
      )}

      {filterGroups?.map((group) => {
        if (group.multi) {
          const value = Array.isArray(group.value) ? group.value : [group.value].filter(Boolean);
          return (
            <div key={group.label} className="flex items-center gap-2">
              <Select
                onValueChange={(next) => {
                  if (!value.includes(next)) {
                    group.onChange([...value, next]);
                  }
                }}
              >
                <SelectTrigger className="min-w-[180px]">
                  <SelectValue placeholder={group.label} />
                </SelectTrigger>
                <SelectContent>
                  {group.options.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex flex-wrap items-center gap-1">
                {value.map((val) => {
                  const option = group.options.find((opt) => opt.value === val);
                  if (!option) return null;
                  return (
                    <Button
                      key={val}
                      variant="secondary"
                      size="sm"
                      type="button"
                      className="h-7 gap-1"
                      onClick={() => group.onChange(value.filter((item) => item !== val))}
                    >
                      <span>{option.label}</span>
                      <X className="h-3 w-3" />
                    </Button>
                  );
                })}
              </div>
            </div>
          );
        }

        const value = Array.isArray(group.value) ? group.value[0] ?? "" : group.value;
        return (
          <div key={group.label} className="flex items-center gap-2">
            <Select value={value} onValueChange={(next) => group.onChange(next)}>
              <SelectTrigger className="min-w-[180px]">
                <SelectValue placeholder={group.label} />
              </SelectTrigger>
              <SelectContent>
                {group.options.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {group.allowClear && value && (
              <Button variant="ghost" size="sm" onClick={() => group.onChange("")}>Clear</Button>
            )}
          </div>
        );
      })}

      {children}

      {endAdornment && <div className="ml-auto flex items-center gap-2">{endAdornment}</div>}
    </div>
  );
}


import * as React from "react";
import { CalendarIcon, ChevronDownIcon } from "lucide-react";
import { format, subDays, startOfYear } from "date-fns";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DateRange } from "react-day-picker";
import type { TimeRange, AnalyticsFilters } from "@/types/analytics";

interface DateRangePickerProps {
  value: AnalyticsFilters;
  onChange: (filters: AnalyticsFilters) => void;
  className?: string;
}

const timeRangeOptions: Array<{ value: TimeRange; label: string }> = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
  { value: "180d", label: "Last 6 months" },
  { value: "365d", label: "Last year" },
  { value: "custom", label: "Custom range" },
];

const getDateRangeFromTimeRange = (timeRange: TimeRange): [Date, Date] => {
  const now = new Date();
  const end = new Date(now);

  switch (timeRange) {
    case "7d":
      return [subDays(now, 7), end];
    case "30d":
      return [subDays(now, 30), end];
    case "90d":
      return [subDays(now, 90), end];
    case "180d":
      return [subDays(now, 180), end];
    case "365d":
      return [subDays(now, 365), end];
    default:
      return [subDays(now, 30), end];
  }
};

export function DateRangePicker({ value, onChange, className }: DateRangePickerProps) {
  const [isCalendarOpen, setIsCalendarOpen] = React.useState(false);

  const handleTimeRangeChange = (timeRange: TimeRange) => {
    if (timeRange === "custom") {
      // Keep existing dates for custom or set defaults
      const [defaultStart, defaultEnd] = getDateRangeFromTimeRange("30d");
      onChange({
        ...value,
        timeRange,
        startDate: value.startDate || defaultStart,
        endDate: value.endDate || defaultEnd,
      });
    } else {
      const [start, end] = getDateRangeFromTimeRange(timeRange);
      onChange({
        ...value,
        timeRange,
        startDate: start,
        endDate: end,
      });
    }
  };

  const handleDateRangeChange = (dateRange: DateRange | undefined) => {
    if (dateRange?.from && dateRange?.to) {
      onChange({
        ...value,
        timeRange: "custom",
        startDate: dateRange.from,
        endDate: dateRange.to,
      });
      setIsCalendarOpen(false);
    }
  };

  const formatDateRange = () => {
    if (value.timeRange === "custom" && value.startDate && value.endDate) {
      return `${format(value.startDate, "MMM d, y")} - ${format(value.endDate, "MMM d, y")}`;
    }

    const option = timeRangeOptions.find(opt => opt.value === value.timeRange);
    return option?.label || "Last 30 days";
  };

  const selectedDateRange: DateRange | undefined =
    value.startDate && value.endDate
      ? { from: value.startDate, to: value.endDate }
      : undefined;

  return (
    <div className={cn("flex flex-col sm:flex-row gap-2", className)}>
      {/* Time Range Selector */}
      <Select
        value={value.timeRange}
        onValueChange={handleTimeRangeChange}
      >
        <SelectTrigger className="w-full sm:w-[180px]">
          <SelectValue placeholder="Select range" />
        </SelectTrigger>
        <SelectContent>
          {timeRangeOptions.map(option => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Custom Date Range Picker */}
      {value.timeRange === "custom" && (
        <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                "w-full sm:w-[280px] justify-start text-left font-normal",
                !selectedDateRange && "text-muted-foreground"
              )}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {selectedDateRange ? (
                formatDateRange()
              ) : (
                <span>Pick a date range</span>
              )}
              <ChevronDownIcon className="ml-auto h-4 w-4 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              initialFocus
              mode="range"
              defaultMonth={selectedDateRange?.from}
              selected={selectedDateRange}
              onSelect={handleDateRangeChange}
              numberOfMonths={2}
              disabled={(date) =>
                date > new Date() || date < new Date("2020-01-01")
              }
            />
            <div className="p-3 border-t">
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const now = new Date();
                    handleDateRangeChange({
                      from: startOfYear(now),
                      to: now
                    });
                  }}
                >
                  Year to Date
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsCalendarOpen(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
}
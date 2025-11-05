import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}
;
import type { ChartProps } from '@/types/analytics';

interface ChartAreaProps extends ChartProps {
  areas?: Array<{
    dataKey: string;
    name: string;
    color: string;
    fillOpacity?: number;
  }>;
  xAxisKey?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  stacked?: boolean;
}

const defaultAreas = [
  { dataKey: 'value', name: 'Value', color: '#8884d8', fillOpacity: 0.3 }
];

export function ChartArea({
  data,
  areas = defaultAreas,
  xAxisKey = 'date',
  height = 300,
  showLegend = true,
  showGrid = true,
  stacked = false,
  className
}: ChartAreaProps) {
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background border border-border rounded-md shadow-md p-3">
          <p className="font-medium mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (!data || data.length === 0) {
    return (
      <div className={cn(
        "flex items-center justify-center border border-dashed rounded-md",
        className
      )} style={{ height }}>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">No data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" className="opacity-30" />}

          <XAxis
            dataKey={xAxisKey}
            tick={{ fontSize: 12 }}
            tickLine={{ strokeWidth: 1 }}
            axisLine={{ strokeWidth: 1 }}
          />

          <YAxis
            tick={{ fontSize: 12 }}
            tickLine={{ strokeWidth: 1 }}
            axisLine={{ strokeWidth: 1 }}
          />

          <Tooltip content={<CustomTooltip />} />

          {showLegend && <Legend />}

          {areas.map((area, index) => (
            <Area
              key={index}
              type="monotone"
              dataKey={area.dataKey}
              name={area.name}
              stackId={stacked ? "1" : undefined}
              stroke={area.color}
              fill={area.color}
              fillOpacity={area.fillOpacity || 0.3}
              strokeWidth={2}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
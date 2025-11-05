import {
  BarChart,
  Bar,
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

interface ChartBarProps extends ChartProps {
  bars?: Array<{
    dataKey: string;
    name: string;
    color: string;
  }>;
  xAxisKey?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  layout?: 'horizontal' | 'vertical';
}

const defaultBars = [
  { dataKey: 'value', name: 'Value', color: '#8884d8' }
];

export function ChartBar({
  data,
  bars = defaultBars,
  xAxisKey = 'name',
  height = 300,
  showLegend = false,
  showGrid = true,
  layout = 'vertical',
  className
}: ChartBarProps) {
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background border border-border rounded-md shadow-md p-3">
          <p className="font-medium mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
              {entry.payload.percentage && (
                <span className="text-muted-foreground ml-1">
                  ({entry.payload.percentage.toFixed(1)}%)
                </span>
              )}
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
        <BarChart
          data={data}
          layout={layout}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          {showGrid && <CartesianGrid strokeDasharray="3 3" className="opacity-30" />}

          {layout === 'vertical' ? (
            <>
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis
                dataKey={xAxisKey}
                type="category"
                width={120}
                tick={{ fontSize: 12 }}
                tickLine={{ strokeWidth: 1 }}
                axisLine={{ strokeWidth: 1 }}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey={xAxisKey}
                tick={{ fontSize: 12 }}
                tickLine={{ strokeWidth: 1 }}
                axisLine={{ strokeWidth: 1 }}
              />
              <YAxis tick={{ fontSize: 12 }} />
            </>
          )}

          <Tooltip content={<CustomTooltip />} />

          {showLegend && <Legend />}

          {bars.map((bar, index) => (
            <Bar
              key={index}
              dataKey={bar.dataKey}
              name={bar.name}
              fill={bar.color}
              radius={[2, 2, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
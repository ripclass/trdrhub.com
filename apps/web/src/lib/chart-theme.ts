/**
 * Centralized chart configuration for Recharts
 * Provides consistent theming across light and dark modes
 */

export interface ChartThemeConfig {
  // Grid and axes
  gridColor: string;
  axisColor: string;
  tickColor: string;
  
  // Chart colors (series)
  colors: string[];
  
  // Text
  textColor: string;
  mutedTextColor: string;
  
  // Tooltips
  tooltipBackground: string;
  tooltipBorder: string;
  tooltipText: string;
  
  // Background
  background: string;
}

/**
 * Get chart theme configuration based on current theme
 * Reads from CSS variables for automatic dark/light mode support
 */
export function getChartTheme(isDark?: boolean): ChartThemeConfig {
  // If isDark not provided, check document
  const resolvedIsDark = isDark ?? document.documentElement.classList.contains('dark');
  
  if (resolvedIsDark) {
    return {
      gridColor: 'hsl(220 13% 18%)',
      axisColor: 'hsl(220 13% 18%)',
      tickColor: 'hsl(220 9% 68%)',
      
      colors: [
        'hsl(190 100% 50%)',  // Cyan accent
        'hsl(142 76% 42%)',   // Success green
        'hsl(38 92% 55%)',    // Warning amber
        'hsl(210 100% 60%)',  // Info blue
        'hsl(0 72% 55%)',     // Destructive red
        'hsl(280 65% 60%)',   // Purple
        'hsl(160 60% 50%)',   // Teal
      ],
      
      textColor: 'hsl(220 5% 92%)',
      mutedTextColor: 'hsl(220 9% 68%)',
      
      tooltipBackground: 'hsl(220 13% 11%)',
      tooltipBorder: 'hsl(220 13% 18%)',
      tooltipText: 'hsl(220 5% 92%)',
      
      background: 'hsl(220 13% 6%)',
    };
  }
  
  // Light theme
  return {
    gridColor: 'hsl(220 13% 91%)',
    axisColor: 'hsl(220 13% 91%)',
    tickColor: 'hsl(220 8.9% 46.1%)',
    
    colors: [
      'hsl(158 64% 25%)',   // Primary
      'hsl(142 76% 36%)',   // Success
      'hsl(38 92% 50%)',    // Warning
      'hsl(221 83% 53%)',   // Info
      'hsl(0 72% 51%)',     // Destructive
      'hsl(280 65% 50%)',   // Purple
      'hsl(160 60% 45%)',   // Teal
    ],
    
    textColor: 'hsl(220 13% 18%)',
    mutedTextColor: 'hsl(220 8.9% 46.1%)',
    
    tooltipBackground: 'hsl(0 0% 100%)',
    tooltipBorder: 'hsl(220 13% 91%)',
    tooltipText: 'hsl(220 13% 18%)',
    
    background: 'hsl(0 0% 100%)',
  };
}

/**
 * Default chart margin for professional data-dense layout
 */
export const CHART_MARGIN = {
  top: 12,
  right: 12,
  bottom: 24,
  left: 12,
};

/**
 * Compact chart margin for very dense layouts
 */
export const CHART_MARGIN_COMPACT = {
  top: 8,
  right: 8,
  bottom: 20,
  left: 8,
};

/**
 * Default axis style for professional appearance
 */
export function getAxisStyle(theme: ChartThemeConfig) {
  return {
    tick: { fill: theme.tickColor, fontSize: 11 },
    axisLine: { stroke: theme.axisColor, strokeWidth: 1 },
    tickLine: { stroke: theme.axisColor },
  };
}

/**
 * Default grid style for subtle appearance
 */
export function getGridStyle(theme: ChartThemeConfig) {
  return {
    stroke: theme.gridColor,
    strokeWidth: 1,
    strokeDasharray: '3 3',
    opacity: 0.5,
  };
}

/**
 * Default tooltip style for professional appearance
 */
export function getTooltipStyle(theme: ChartThemeConfig) {
  return {
    contentStyle: {
      backgroundColor: theme.tooltipBackground,
      border: `1px solid ${theme.tooltipBorder}`,
      borderRadius: '6px',
      padding: '8px 12px',
      fontSize: '12px',
      color: theme.tooltipText,
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    },
    itemStyle: {
      color: theme.tooltipText,
      fontSize: '11px',
      padding: '2px 0',
    },
    labelStyle: {
      color: theme.mutedTextColor,
      fontSize: '11px',
      fontWeight: 600,
      marginBottom: '4px',
    },
  };
}


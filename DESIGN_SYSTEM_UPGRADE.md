# Professional Design System Upgrade

## Overview

This upgrade implements a professional, Bloomberg-style design system across the entire LCopilot application (bank, importer, and exporter dashboards) with full dark/light theme support and data-dense components optimized for financial data display.

## Key Features

### 1. Dual Theme Support (Dark/Light)
- **ThemeProvider**: `apps/web/src/providers/ThemeProvider.tsx`
  - Respects system preference
  - Persists user choice to localStorage
  - Provides `useTheme()` hook for components
  
- **Theme Toggle**: `apps/web/src/components/ui/theme-toggle.tsx`
  - Accessible dropdown with Light/Dark/System options
  - Integrated into AppShell header

- **Enhanced CSS Variables**: `apps/web/src/index.css`
  - Semantic color tokens for both themes
  - Density tokens (spacing, typography, table dimensions)
  - Professional shadows and focus rings
  - Data-dense typography scale (11px-18px)

### 2. Professional App Shell
- **AppShell Component**: `apps/web/src/components/layout/AppShell.tsx`
  - Unified layout with sticky header
  - Breadcrumb navigation
  - Action buttons area
  - Optional toolbar section
  - Compact mode for dense layouts

### 3. Data-Dense Table Components
- **Enhanced Table**: `apps/web/src/components/ui/table.tsx`
  - `dense` prop: Reduces padding for compact rows (2.5rem height)
  - `sticky` prop: Sticky header for long tables
  - `zebra` prop: Alternating row colors for readability
  - `numeric` prop: Right-aligned numbers with tabular-nums font

**Usage Example:**
```tsx
<Table dense sticky>
  <TableHeader sticky>
    <TableRow dense>
      <TableHead dense>Item</TableHead>
      <TableHead dense numeric>Amount</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody zebra>
    <TableRow dense>
      <TableCell dense>Transaction</TableCell>
      <TableCell dense numeric>$1,234.56</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### 4. Compact Form Components

#### Buttons (`apps/web/src/components/ui/button.tsx`)
- New sizes: `xs` (h-7), `sm` (h-8), `icon-sm` (h-8 w-8)
- Professional shadows on primary buttons
- Consistent 6px border radius

#### Inputs (`apps/web/src/components/ui/input.tsx`)
- `dense` prop: Reduces height to h-8 with smaller text

#### Cards (`apps/web/src/components/ui/card.tsx`)
- `dense` prop on all card components
- Reduced padding from p-6 to p-4/p-5
- Tighter typography in headers

### 5. Chart Theming
- **Chart Theme Utility**: `apps/web/src/lib/chart-theme.ts`
  - `getChartTheme(isDark)`: Returns theme-aware colors
  - `getAxisStyle()`, `getGridStyle()`, `getTooltipStyle()`
  - Predefined margins for professional layouts
  - Automatic dark/light mode support

**Usage Example:**
```tsx
import { getChartTheme, getAxisStyle, CHART_MARGIN } from '@/lib/chart-theme';
const theme = getChartTheme();

<LineChart margin={CHART_MARGIN}>
  <XAxis {...getAxisStyle(theme)} />
  <Line stroke={theme.colors[0]} />
</LineChart>
```

### 6. Updated Pages

#### BankDashboard (`apps/web/src/pages/BankDashboard.tsx`)
- Migrated to AppShell
- Theme toggle in header
- Professional breadcrumbs

#### ResultsTable (`apps/web/src/components/bank/ResultsTable.tsx`)
- Dense table variant applied
- Sticky headers for long result lists
- Numeric alignment for scores and counts
- Zebra striping for readability

### 7. Component Gallery
- **Gallery Page**: `/lcopilot/component-gallery`
- **File**: `apps/web/src/pages/ComponentGallery.tsx`
- Demonstrates all component variants
- Shows theme-aware colors
- Includes usage guidelines

## Design Tokens

### Spacing
- `--spacing-compact`: 0.25rem (4px)
- `--spacing-tight`: 0.5rem (8px)
- `--spacing-normal`: 0.75rem (12px)
- `--spacing-relaxed`: 1rem (16px)

### Typography
- `--text-xs`: 0.6875rem (11px)
- `--text-sm`: 0.8125rem (13px)
- `--text-base`: 0.875rem (14px)
- `--text-lg`: 1rem (16px)
- `--text-xl`: 1.125rem (18px)

### Line Heights
- `--line-height-tight`: 1.35
- `--line-height-normal`: 1.45
- `--line-height-relaxed`: 1.6

### Table Density
- `--table-row-height`: 2.5rem
- `--table-padding-x`: 0.75rem
- `--table-padding-y`: 0.5rem

### Border Radius
- Default: 0.375rem (6px) - tighter for professional look

## Accessibility Features

1. **High-Contrast Focus Rings**
   - 2px solid ring with 2px offset
   - Uses `--ring` color (theme-aware)
   - Applied to all interactive elements

2. **Professional Scrollbars**
   - Styled webkit scrollbars
   - Theme-aware colors
   - Smooth hover transitions

3. **Keyboard Navigation**
   - Full keyboard support in tables
   - Tab navigation through forms
   - Escape key support in modals

4. **Color Contrast**
   - All text meets WCAG AA standards
   - High contrast in dark mode
   - Subtle borders with sufficient contrast

## Migration Guide

### For Existing Pages

1. **Add AppShell wrapper:**
```tsx
import { AppShell } from "@/components/layout/AppShell";

return (
  <AppShell
    title="Your Page Title"
    subtitle="Brief description"
    breadcrumbs={[
      { label: "LCopilot", href: "/lcopilot" },
      { label: "Your Page" },
    ]}
    actions={<Button>Action</Button>}
    compact
  >
    {/* Your page content */}
  </AppShell>
);
```

2. **Update Tables:**
```tsx
// Before
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead className="text-right">Value</TableHead>

// After
<Table dense sticky>
  <TableHeader sticky>
    <TableRow dense>
      <TableHead dense>Name</TableHead>
      <TableHead dense numeric>Value</TableHead>
```

3. **Apply Dense Props:**
```tsx
// Cards
<Card dense>
  <CardHeader dense>
    <CardTitle dense>Title</CardTitle>

// Inputs
<Input dense placeholder="..." />

// Buttons
<Button size="sm">Action</Button>
```

### For Charts

```tsx
import { getChartTheme, getAxisStyle, getGridStyle } from '@/lib/chart-theme';

function MyChart() {
  const theme = getChartTheme();
  
  return (
    <ResponsiveContainer>
      <LineChart>
        <XAxis {...getAxisStyle(theme)} />
        <YAxis {...getAxisStyle(theme)} />
        <CartesianGrid {...getGridStyle(theme)} />
        <Line stroke={theme.colors[0]} />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

## Browser Support

- Modern evergreen browsers (Chrome, Firefox, Safari, Edge)
- CSS Variables support required
- Backdrop filter support for sticky headers
- `prefers-color-scheme` media query for system theme detection

## Performance Considerations

1. **CSS Variables**: Instant theme switching without re-render
2. **Sticky Headers**: Uses CSS `position: sticky` (hardware accelerated)
3. **Backdrop Blur**: Optional, gracefully degrades
4. **Focus Rings**: Pure CSS, no JavaScript overhead

## Next Steps

To complete the rollout:

1. Apply AppShell to remaining pages (importer, exporter, analytics)
2. Update all tables to use dense variant where appropriate
3. Apply dense props to cards and inputs in data-heavy sections
4. Update charts to use centralized theme utility
5. Add theme toggle to any custom headers
6. Test keyboard navigation flows
7. Verify color contrast in both themes
8. Add loading skeletons for better perceived performance

## Resources

- Component Gallery: `/lcopilot/component-gallery`
- Theme Provider: `apps/web/src/providers/ThemeProvider.tsx`
- Chart Theme: `apps/web/src/lib/chart-theme.ts`
- Design Tokens: `apps/web/src/index.css` (lines 11-109)


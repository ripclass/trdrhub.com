# DiscrepancyList Component

A polished React component for displaying detailed discrepancy information in the LCopilot validation results.

## Features

### 🎯 **Core Functionality**
- **Detailed Cards**: Each discrepancy displayed as a clean, informative card
- **Severity-Based Styling**: Color-coded by severity (Critical, Major, Minor)
- **Smart Icons**: Context-aware icons based on discrepancy type
- **Filtering**: Filter discrepancies by severity level
- **Mobile Responsive**: Optimized for all screen sizes

### 🎨 **Visual Design**
- **Color Coding**:
  - Critical: Red (#ef4444)
  - Major: Orange (#f59e0b)
  - Minor: Green (#10b981)
- **Interactive Elements**: Hover effects and smooth transitions
- **Typography**: Clean, readable text hierarchy
- **Badges**: Color-coded document type badges

### 📱 **Responsive Design**
- **Desktop**: Multi-column layout with side-by-side comparisons
- **Tablet**: Adapted layout with proper spacing
- **Mobile**: Stacked layout, touch-friendly interactions

## Usage

```tsx
import DiscrepancyList from '../components/DiscrepancyList'
import { DiscrepancyInfo } from '../api/sessions'

const discrepancies: DiscrepancyInfo[] = [
  {
    id: '1',
    discrepancy_type: 'amount_mismatch',
    severity: 'critical',
    rule_name: 'Amount Consistency Check',
    field_name: 'invoice_amount',
    expected_value: 'USD 25,000.00',
    actual_value: 'USD 35,000.00',
    description: 'Invoice amount exceeds the Letter of Credit limit.',
    source_document_types: ['letter_of_credit', 'commercial_invoice'],
    created_at: '2024-01-15T10:30:00Z'
  }
  // ... more discrepancies
]

function ValidationResults() {
  return (
    <div>
      <h2>Validation Results</h2>
      <DiscrepancyList discrepancies={discrepancies} />
    </div>
  )
}
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `discrepancies` | `DiscrepancyInfo[]` | Yes | - | Array of discrepancy objects |
| `className` | `string` | No | `''` | Additional CSS classes |

## DiscrepancyInfo Interface

```typescript
interface DiscrepancyInfo {
  id: string
  discrepancy_type: string              // Used for icon selection
  severity: 'critical' | 'major' | 'minor'
  rule_name: string                     // Main title
  field_name?: string                   // Optional field identifier
  expected_value?: string               // What was expected
  actual_value?: string                 // What was found
  description: string                   // Detailed explanation
  source_document_types?: string[]      // Which documents involved
  created_at: string                    // ISO timestamp
}
```

## Icon Mapping

The component automatically selects appropriate icons based on `discrepancy_type`:

- **Amount**: `DollarSign` - for amount_mismatch, invoice_amount, etc.
- **Date**: `Calendar` - for date_mismatch, expiry_date, etc.
- **Party**: `Users` - for party_mismatch, beneficiary, etc.
- **Port**: `MapPin` - for port_mismatch, loading_port, etc.
- **Default**: `AlertTriangle` - for other types

## Document Type Colors

Document badges are color-coded for easy identification:

- **Letter of Credit**: Blue (#3b82f6)
- **Commercial Invoice**: Purple (#8b5cf6)
- **Bill of Lading**: Cyan (#06b6d4)
- **Other**: Gray (#6b7280)

## State Handling

### Empty State
When no discrepancies are provided, shows a success message with checkmark icon.

### Filtering
- **All Severities**: Shows complete list with counts
- **By Severity**: Filters to show only selected severity
- **Empty Filter**: Shows "No X discrepancies found" message
- **Disabled Options**: Filter options with 0 count are disabled

## CSS Classes

The component uses these main CSS classes (defined in `index.css`):

```css
.discrepancy-list-container     /* Main container */
.discrepancy-summary           /* Header with counts and filters */
.discrepancy-list             /* List of discrepancy cards */
.discrepancy-card             /* Individual discrepancy card */
.severity-badge               /* Severity indicator badges */
.filter-controls              /* Filter dropdown container */
.value-comparison             /* Expected vs actual display */
.document-badges              /* Source document indicators */
```

## Styling Customization

To customize colors or styling, override these CSS custom properties:

```css
.discrepancy-card {
  --critical-color: #ef4444;
  --major-color: #f59e0b;
  --minor-color: #10b981;
}
```

## Accessibility

- **Keyboard Navigation**: Full keyboard support for filter dropdown
- **Screen Readers**: Proper ARIA labels and semantic HTML
- **Color Contrast**: WCAG AA compliant color combinations
- **Focus Indicators**: Clear focus states for interactive elements

## Performance

- **Efficient Filtering**: Uses native array methods for fast filtering
- **Memoization**: Consider wrapping in React.memo if parent re-renders frequently
- **Virtual Scrolling**: For 100+ items, consider adding virtualization

## Examples

### Basic Usage
```tsx
<DiscrepancyList discrepancies={session.discrepancies} />
```

### With Custom Styling
```tsx
<DiscrepancyList
  discrepancies={discrepancies}
  className="my-custom-discrepancy-list"
/>
```

### Empty State
```tsx
<DiscrepancyList discrepancies={[]} />
```

## Testing

See `test-discrepancy-component.md` for comprehensive testing instructions and scenarios.

## Dependencies

- **React**: 18.2.0+
- **Lucide React**: 0.286.0+ (for icons)
- **TypeScript**: 5.0.2+ (for type safety)
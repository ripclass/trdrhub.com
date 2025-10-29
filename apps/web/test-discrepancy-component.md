# DiscrepancyList Component Testing Guide

## Overview
This guide shows how to test the new DiscrepancyList component with different scenarios.

## Testing Steps

### 1. Start the Development Server
```bash
cd apps/web
npm run dev
```

### 2. Test the Demo Component
Visit: `http://localhost:5173/demo`

This demo page shows:
- **Full Scenario**: All types of discrepancies (critical, major, minor)
- **No Discrepancies**: How the component handles empty state
- **Critical Only**: Testing severity filtering

### 3. Test with Stub Scenarios
With the API server running in stub mode, you can test real scenarios:

1. **Start the API server in stub mode**:
   ```bash
   cd apps/api
   python3 main.py
   ```

2. **Upload documents and test different stub scenarios**:
   - Visit `http://localhost:5173/upload`
   - Upload any 3 PDF files
   - The backend will simulate different discrepancy scenarios

### 4. Verify Component Features

#### ✅ Visual Elements
- **Severity indicators**: Critical (red), Major (orange), Minor (green)
- **Icons**: Different icons for amount, date, party, and port discrepancies
- **Document badges**: Color-coded by document type

#### ✅ Functionality
- **Filtering**: Dropdown to filter by severity level
- **Summary header**: Shows total count and breakdown by severity
- **Responsive design**: Works on mobile devices
- **Expected vs Actual values**: Clear comparison display

#### ✅ Data Handling
- **Empty state**: Shows "No Discrepancies Found" message
- **Multiple documents**: Handles source document arrays
- **Missing fields**: Gracefully handles optional fields

## Component Features Tested

### 1. Severity-Based Styling
- ❤️ **Critical**: Red background (#fecaca), red border, red icon
- 🧡 **Major**: Yellow background (#fef3c7), orange border, orange icon
- 💚 **Minor**: Green background (#d1fae5), green border, green icon

### 2. Icon Mapping
- 📅 **Date discrepancies**: Calendar icon
- 💰 **Amount discrepancies**: Dollar sign icon
- 👥 **Party discrepancies**: Users icon
- 🚢 **Port discrepancies**: Map pin icon
- ⚠️ **Other**: Alert triangle icon

### 3. Document Type Badges
- 🔵 **Letter of Credit**: Blue badge
- 🟣 **Commercial Invoice**: Purple badge
- 🟢 **Bill of Lading**: Cyan badge

### 4. Filtering Options
- **All Severities**: Shows complete list
- **Critical Only**: Shows only critical issues
- **Major Only**: Shows only major issues
- **Minor Only**: Shows only minor issues
- **Disabled states**: Options with 0 count are disabled

### 5. Mobile Responsiveness
- **Stacked layout**: On mobile, elements stack vertically
- **Touch-friendly**: Filter dropdown works well on touch devices
- **Readable text**: Proper font sizes for small screens

## Expected Test Results

### Demo Page (/demo)
1. **Sample Discrepancies Section**:
   - Shows 5 discrepancies (2 critical, 2 major, 1 minor)
   - Filter dropdown functional
   - All visual elements properly styled

2. **No Discrepancies Section**:
   - Shows green checkmark and success message
   - Clean, centered layout

3. **Critical Only Section**:
   - Shows 2 critical discrepancies
   - Proper red styling applied

### Integration with ReviewPage
1. **With discrepancies**: Component replaces old inline display
2. **Without discrepancies**: Shows success state
3. **Filtering**: Users can filter by severity
4. **Mobile view**: Responsive layout maintained

## Browser Testing
Test in multiple browsers:
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers

## Performance Checks
- ✅ Fast rendering with 10+ discrepancies
- ✅ Smooth filter transitions
- ✅ No layout shifts during filtering
- ✅ Accessible keyboard navigation

## Cleanup
After testing, remove the demo route from App.tsx if not needed in production.
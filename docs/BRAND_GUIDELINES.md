# TRDR Hub Brand & Style Guidelines

> **Version:** 1.0 (Feb 2026)
> **Theme:** "System Critical" / Bloomberg-style Professional

## 1. Core Brand Identity

Our design language communicates precision, speed, and reliability. We use a high-contrast "System Critical" aesthetic for our dark mode to evoke the feeling of professional trading terminals and mission-critical infrastructure.

### 1.1 Color Palette (Strict)

#### Primary Brand Colors
| Token | Color | Hex | Usage |
|-------|-------|-----|-------|
| `--brand-green` | Deep Jungle | `#00261C` | Primary Background, Dark Mode Base |
| `--brand-lime` | Neon Lime | `#B2F273` | Primary Accent, Success, Highlights |
| `--brand-mint` | Ice Mint | `#EDF5F2` | Text, Light Mode Backgrounds |

#### Secondary / Muted Colors
| Token | Color | Hex | Usage |
|-------|-------|-----|-------|
| `--brand-green-muted` | Darker Jungle | `#001F17` | Card Backgrounds, Sidebar |
| `--brand-lime-muted` | Muted Lime | `#364D23` | Borders, Subtle Highlights |

### 1.2 Typography

**Headings:** `Space Grotesk`
- Used for all H1-H6 elements.
- Features: Technical, geometric, modern.
- Usage: `font-display` class.

**Body:** `Inter`
- Used for all body text, UI elements, and data.
- Features: Highly legible, neutral, professional.
- Usage: Default font.

**Monospace:** `JetBrains Mono` (or system mono)
- Used for code, data values, and technical labels.
- Usage: `font-mono` class.

---

## 2. Design System Tokens

### 2.1 Spacing (Density)
We prioritize data density without sacrificing readability.

| Token | Value | Pixel | Usage |
|-------|-------|-------|-------|
| `--spacing-compact` | `0.25rem` | 4px | Tight grouping |
| `--spacing-tight` | `0.5rem` | 8px | Component internal padding |
| `--spacing-normal` | `0.75rem` | 12px | Standard padding |
| `--spacing-relaxed` | `1rem` | 16px | Section spacing |

### 2.2 Border Radius
Consistent `6px` (`0.375rem` or `0.5rem`) radius for a professional, software-like feel. Avoid fully rounded corners for main containers.

### 2.3 Typography Scale
Data-dense scale for financial interfaces.

| Token | Size | Usage |
|-------|------|-------|
| `--text-xs` | 11px | Labels, Metadata |
| `--text-sm` | 13px | Body, Table Data |
| `--text-base` | 14px | Primary Body |
| `--text-lg` | 16px | Subheadings |
| `--text-xl` | 18px | Page Titles |

---

## 3. Theme Guidelines

### 3.1 Dark Mode ("System Critical")
This is our signature look for the landing page and pro-tools.

- **Background:** `#00261C` (Deep Jungle)
- **Text:** `#EDF5F2` (Ice Mint) - 60-80% opacity for body.
- **Accents:** `#B2F273` (Neon Lime) - Used sparingly for CTAs and critical data.
- **Borders:** `#EDF5F2` at 10% opacity.
- **Effects:**
  - **Grid Overlay:** Radial fade grid pattern.
  - **Glows:** Subtle lime glows behind key elements.
  - **Glassmorphism:** `bg-[#00261C]/80 backdrop-blur-md`.

### 3.2 Light Mode (Documentation / Standard)
Used for documentation and standard dashboard views.

- **Background:** `#FFFFFF` or `#EDF5F2`
- **Text:** `#00261C`
- **Accents:** `#00261C` (Primary), `#B2F273` (Highlights)

---

## 4. UI Component Styles

### 4.1 Cards (System Critical Style)
Cards in the dark theme should feel like heads-up display modules.

```css
.card-system-critical {
  @apply bg-[#00382E]/50;
  @apply border border-[#EDF5F2]/10;
  @apply rounded-2xl;
  @apply backdrop-blur-sm;
}

.card-system-critical:hover {
  @apply border-[#B2F273]/50;
  @apply shadow-[0_10px_40px_-10px_rgba(178,242,115,0.1)];
}
```

### 4.2 Buttons

**Primary CTA:**
- Background: `#B2F273`
- Text: `#00261C`
- Hover: `#a3e662`
- Shadow: `shadow-[0_0_20px_rgba(178,242,115,0.3)]`

**Secondary / Outline:**
- Border: `#EDF5F2` (20% opacity)
- Text: `#EDF5F2`
- Hover: `bg-[#EDF5F2]/5`

### 4.3 Background Effects

**Grid Pattern:**
```tsx
<div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
```

**Ambient Blobs:**
```tsx
<div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
```

**Top Gradient Line:**
```tsx
<div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
```

---

## 5. Implementation Checklist

When creating new pages or components:

1.  [ ] **Theme Check:** Does it support the `--brand-green` dark theme?
2.  [ ] **Typography:** Are headings `Space Grotesk` and body `Inter`?
3.  [ ] **Contrast:** Is text legible against the dark background (use opacity 60-80% for secondary text)?
4.  [ ] **Interaction:** Do interactive elements have hover states (glows, border color changes)?
5.  [ ] **Density:** Is the spacing appropriate for the content type (compact for data, relaxed for marketing)?
6.  [ ] **Background:** Does the section include the standard grid/blob/line background layers?

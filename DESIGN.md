# Design System — Logistics Presale AI System

## 1. Visual Theme & Atmosphere

A professional enterprise SaaS dashboard for logistics presale consultants. The design language communicates **precision, trust, and data confidence** — qualities essential when generating multi-million-yuan warehouse proposals for Fortune 500 clients like Porsche, Bosch, and BMW.

The interface uses a cool-neutral foundation with an indigo accent system that signals intelligence without coldness. Surfaces are clean white cards on a subtle warm-gray canvas (`#f8fafc`), creating depth through gentle elevation rather than heavy borders. The overall density is **medium-high** — this is a working tool, not a marketing site. Information density matters, but breathing room prevents cognitive overload.

**Key Characteristics:**
- Enterprise dashboard aesthetic with card-based information architecture
- Indigo (`#4f46e5`) as the primary brand accent — conveys trust, technology, intelligence
- Warm-gray canvas (`#f8fafc`) with pure white (`#ffffff`) card surfaces
- Pipeline visualization as the central UX metaphor (12-stage horizontal progress)
- Status-driven color system: green=completed, blue=running, red=failed, gray=pending
- Data tables and KPI cards as primary information containers
- Chinese-first UI with English technical terms preserved (e.g., "Pipeline", "Stage", "QA")
- Minimal use of icons — emoji serve as lightweight, universally-readable stage indicators
- Shadow-border hybrid: cards use `border: 1px solid #e2e8f0` with subtle shadow for lift

## 2. Color Palette & Roles

### Primary Brand
- **Indigo 600** (`#4f46e5`): Primary CTA buttons, active tab indicators, selected states, brand accent
- **Indigo 700** (`#4338ca`): Button hover, active link text
- **Indigo 50** (`#eef2ff`): Active sidebar item background, selected state tint, badge background

### Text Hierarchy
- **Slate 900** (`#0f172a`): `--text-primary`. Page titles, card headings, primary data values
- **Slate 700** (`#334155`): Section headings, secondary emphasis
- **Slate 600** (`#475569`): Body text, descriptions, table cell content
- **Slate 500** (`#64748b`): `--text-secondary`. Metadata, timestamps, helper text
- **Slate 400** (`#94a3b8`): Placeholder text, disabled labels, muted icons

### Surfaces
- **White** (`#ffffff`): `--bg-primary`. Card surfaces, modal backgrounds, sidebar
- **Slate 50** (`#f8fafc`): `--bg-secondary`. Page canvas, main content area background
- **Slate 100** (`#f1f5f9`): Hover state for list items, table row zebra stripe
- **Gray 50** (`#f9fafb`): Code block backgrounds, collapsed detail surfaces

### Pipeline Status Colors
- **Green 100/700** (`#dcfce7` / `#15803d`): Stage completed — `.stage-completed`
- **Blue 100/700** (`#dbeafe` / `#1d4ed8`): Stage running (with `animate-pulse`) — `.stage-running`
- **Red 100/700** (`#fee2e2` / `#b91c1c`): Stage failed — `.stage-failed`
- **Gray 100/600** (`#f3f4f6` / `#4b5563`): Stage pending — `.stage-pending`

### Severity / Priority
- **Red 100/800** (`#fee2e2` / `#991b1b`): P0 critical — `.severity-p0`
- **Orange 100/800** (`#ffedd5` / `#9a3412`): P1 major — `.severity-p1`
- **Yellow 100/800** (`#fef9c3` / `#854d0e`): P2 minor — `.severity-p2`

### Financial KPI
- **Green 600** (`#16a34a`): Positive metrics (ROI, NPV, savings)
- **Purple 600** (`#9333ea`): Neutral highlight metrics (NPV values)
- **Blue 600** (`#2563eb`): Secondary metrics (IRR)

### Borders & Dividers
- **Slate 200** (`#e2e8f0`): `--border`. Card borders, section dividers, input borders
- **Slate 100** (`#f1f5f9`): Subtle dividers within cards, zebra stripe borders
- **Indigo 300** (`#a5b4fc`): Accent borders on feature navigation buttons

## 3. Typography Rules

### Font Family
- **Primary**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- System font stack for maximum readability across platforms, zero FOUT

### Hierarchy

| Role | Size | Weight | Line Height | Color | Usage |
|------|------|--------|-------------|-------|-------|
| Page Title | 18px (1.125rem) | 600 | 1.5 | Slate 900 | `<h1>` in page headers |
| Section Heading | 16px (1rem) / 14px | 600 | 1.5 | Slate 900 | Card titles, section labels |
| Body | 14px (0.875rem) | 400 | 1.5 | Slate 600 | Standard text, descriptions |
| Body Medium | 14px | 500 | 1.5 | Slate 700 | Navigation items, emphasized text |
| Small / Caption | 12px (0.75rem) | 400-500 | 1.33 | Slate 500 | Metadata, timestamps, badge text |
| Tiny / Micro | 10px (0.625rem) | 400 | 1.2 | Slate 400 | Version labels, tracking text |
| KPI Value | 24px-36px | 700 | 1.2 | varies | Large numbers on KPI cards |
| Mono | `ui-monospace, monospace` | 400 | 1.5 | Slate 700 | JSON output, code blocks |

### Principles
- **Compact but readable**: 14px base, not 16px — enterprise dashboards need density
- **Weight as hierarchy**: 400 (read), 500 (interact), 600 (section), 700 (KPI values only)
- **No decorative fonts**: System stack only. Speed and consistency over personality
- **Chinese optimization**: `-webkit-font-smoothing: antialiased` for CJK rendering

## 4. Component Stylings

### Buttons

**Primary (Indigo filled)**
- Background: `#4f46e5`
- Text: `#ffffff`, 14px, weight 500
- Padding: 8px 16px
- Radius: 8px (`rounded-lg`)
- Hover: `#4338ca`
- Disabled: `opacity: 0.5`
- Use: "启动 AI 分析", "从 Pipeline 生成报价"

**Secondary (Outlined)**
- Background: `transparent`
- Border: `1px solid` + accent color (indigo/green/orange/purple)
- Text: accent color, 14px, weight 500
- Padding: 8px 16px
- Radius: 8px
- Hover: accent-50 tint background
- Use: "方案对比", "方案详情", "QA 审核", "标书编辑"

**Danger**
- Background: `#ef4444` (Red 500)
- Text: white
- Use: "从断点恢复" (orange variant: `#f97316`)

**Ghost**
- Background: transparent
- Border: `1px solid #d1d5db`
- Text: Slate 700
- Use: "上传招标文件", secondary actions

### Cards

**Standard Card**
- Background: `#ffffff`
- Border: `1px solid #e2e8f0`
- Radius: 12px (`rounded-xl`)
- Padding: 24px (`p-6`)
- Shadow: none (border provides depth)
- Use: Stage output panels, KPI groups, form sections

**KPI Card**
- Same as standard card
- Inner: centered text, KPI value in 24-36px bold, label in 12px Slate 500
- Background variant: `#f9fafb` for nested KPI grouping

**Stage List Item**
- Background: white, hover `#f9fafb`
- Left: emoji icon + stage name (14px, Slate 900)
- Right: status badge (colored pill)
- Border-bottom: `1px solid #f1f5f9`
- Active/selected: left border `3px solid #4f46e5`, background `#eef2ff`

### Status Badges
- Radius: 4px (`rounded`)
- Padding: 2px 8px
- Font: 12px, weight 500
- Variants: `stage-completed` (green), `stage-running` (blue, pulse), `stage-failed` (red), `stage-pending` (gray)

### Inputs & Selects
- Border: `1px solid #d1d5db`
- Radius: 8px
- Padding: 8px 12px
- Font: 14px
- Focus: `outline: none`, `border-color: #4f46e5`, `ring: 2px solid #a5b4fc`

### Navigation (Sidebar)
- Width: 224px (`w-56`)
- Background: white
- Items: 14px, weight 400, Slate 600
- Active: `bg-indigo-50 text-indigo-700 font-medium`
- Icon: emoji, 16px, margin-right 10px
- Footer: version label, 10px, Slate 400

### Tabs
- Horizontal tab bar
- Active: `bg-indigo-600 text-white` pill (radius 8px)
- Inactive: `text-slate-600 hover:bg-gray-50`
- Padding: 8px 16px

### Modals
- Overlay: `bg-black/40`
- Container: white, radius 12px, max-width 500px
- Padding: 24px
- Close: top-right button

### Toast Notifications
- Position: fixed top-right
- Background: `#111827` (Gray 900)
- Text: white, 14px
- Radius: 8px
- Shadow: `0 4px 6px -1px rgba(0,0,0,0.1)`
- Auto-dismiss: 3 seconds

## 5. Layout Principles

### Spacing System
- Base: 4px
- Scale: 4, 8, 12, 16, 20, 24, 32, 48, 64px
- Primary gaps: 12px (tight), 16px (standard), 24px (section)

### Grid & Container
- Max content width: `max-w-7xl` (1280px)
- Sidebar: fixed 224px left
- Main content: flex-1 with horizontal padding 24px
- Cards: single column or 2-5 column grids depending on content type

### Page Structure
```
┌──────────────────────────────────────────────────┐
│ Sidebar (224px) │ Header (white, border-bottom)  │
│                 │──────────────────────────────── │
│ 📊 项目总览     │ Main Content (bg-gray-50)       │
│ 📈 数据看板     │                                  │
│ 📚 知识库       │ ┌─────────────────────────────┐ │
│ ⚙️ 系统设置     │ │ Content Cards               │ │
│                 │ │                             │ │
│                 │ └─────────────────────────────┘ │
│ v0.4.0          │                                  │
└──────────────────────────────────────────────────┘
```

### Project Detail Layout
```
┌─────────────────────────────────────────────────┐
│ Header: Project Name + Action Buttons + Language │
│─────────────────────────────────────────────────│
│ Progress Bar (12 stages, horizontal icons)       │
│─────────────────────────────────────────────────│
│ Tabs: [流水线] [报价] [文档生成] [QA]             │
│─────────────────────────────────────────────────│
│ ┌──────────┐  ┌────────────────────────────┐    │
│ │Stage List │  │ Stage Detail Output         │    │
│ │(40%)     │  │ (60%)                       │    │
│ │          │  │ Specialized Renderer         │    │
│ └──────────┘  └────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Whitespace Philosophy
- **Functional density**: Information-rich without feeling cramped
- **Card spacing**: 16-24px gaps between cards (`gap-4` to `gap-6`)
- **Section separation**: 24px vertical padding between major sections
- **Inner card padding**: 16-24px (`p-4` to `p-6`)

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (L0) | No shadow, no border | Page canvas, text blocks |
| Surface (L1) | `border: 1px solid #e2e8f0` | Standard cards, sidebar |
| Lifted (L2) | `border + box-shadow: 0 1px 2px rgba(0,0,0,0.05)` | Hovered cards, dropdowns |
| Floating (L3) | `box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1)` | Modals, toast notifications |
| Overlay (L4) | `bg-black/40` backdrop + L3 shadow | Modal overlays |

**Shadow Philosophy**: Minimal shadows. Borders do the heavy lifting for surface definition. Shadows appear only on interactive hover states and floating elements (modals, toasts). This keeps the interface feeling grounded and professional — warehouses are grounded, so the UI should be too.

## 7. Do's and Don'ts

### Do
- Use emoji as stage indicators — they're universally readable and add warmth to a dense UI
- Keep KPI values large (24px+) and in semantic colors (green=good, red=bad)
- Show calculation logic transparently (e.g., "人力 = 490托 ÷ 18托/人 = 27人")
- Use `whitespace-pre-wrap` for LLM-generated content to preserve formatting
- Use collapsible `<details>` for long stage outputs — respect the user's attention
- Display Chinese as the primary language with English technical terms preserved
- Show confidence percentages on stage outputs
- Use the 12-stage progress bar as the primary navigation metaphor

### Don't
- Don't use decorative gradients or background images — this is a working tool
- Don't use animation except for the running-stage pulse and toast entrance
- Don't use more than 3 columns for KPI cards on any screen size
- Don't hide the pipeline progress — it should always be visible in the project view
- Don't use serif fonts — the entire system is sans-serif
- Don't use pure black (`#000000`) for text — use Slate 900 (`#0f172a`) for softness
- Don't use colored backgrounds on cards — all cards are white on gray canvas
- Don't make buttons wider than their content (except full-width mobile CTAs)

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | <640px (`sm:`) | Sidebar hidden, hamburger menu, single column |
| Tablet | 640-1024px | Sidebar visible, 2-column grids |
| Desktop | >1024px | Full layout, 3-5 column KPI grids |

### Touch Targets
- All buttons: min-height 44px, min-width 44px on touch devices
- Sidebar links: 40px row height with 10px padding

### Collapsing Strategy
- Sidebar: hidden on mobile, slide-out overlay with backdrop
- KPI grids: 5-col → 2-col on mobile
- Stage list + detail: stacked vertically on mobile (list above, detail below)
- Header action buttons: horizontal scroll on mobile
- Tab bar: remains horizontal, scrollable

## 9. Agent Prompt Guide

### Quick Color Reference
- Primary CTA: Indigo 600 (`#4f46e5`)
- Background: Slate 50 (`#f8fafc`)
- Card surface: White (`#ffffff`)
- Heading text: Slate 900 (`#0f172a`)
- Body text: Slate 600 (`#475569`)
- Border: Slate 200 (`#e2e8f0`)
- Success: Green 700 (`#15803d`)
- Error: Red 700 (`#b91c1c`)
- Running: Blue 700 (`#1d4ed8`)

### Example Component Prompts
- "Create a KPI card: white bg, border 1px solid #e2e8f0, rounded-xl, p-5. Large value at 24px font-bold in green-600 (#16a34a). Label below at 12px slate-500. Centered layout."
- "Build a stage list item: white bg, hover bg-gray-50, border-bottom 1px solid #f1f5f9. Left side: emoji + stage name 14px slate-900. Right side: status badge (green pill for completed, blue pulse for running)."
- "Design the pipeline progress bar: horizontal row of 12 emoji circles. Completed=green-100 border, Running=blue-100 with pulse animation, Failed=red-100, Pending=gray-100. Progress percentage label right-aligned."
- "Create an action button row: outlined buttons with colored borders (indigo for analysis, green for pricing, orange for QA). 14px font-medium, 8px 16px padding, rounded-lg. Hover adds tinted background."

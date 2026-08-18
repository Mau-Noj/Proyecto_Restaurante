---
name: Bistro OS Modern Professional
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45474c'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#75777d'
  outline-variant: '#c5c6cd'
  surface-tint: '#545f74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#111c2e'
  on-primary-container: '#7a849b'
  inverse-primary: '#bcc7df'
  secondary: '#ac3400'
  on-secondary: '#ffffff'
  secondary-container: '#ff6f3c'
  on-secondary-container: '#611a00'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#002116'
  on-tertiary-container: '#539d80'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2fc'
  primary-fixed-dim: '#bcc7df'
  on-primary-fixed: '#111c2e'
  on-primary-fixed-variant: '#3d475b'
  secondary-fixed: '#ffdbd0'
  secondary-fixed-dim: '#ffb59d'
  on-secondary-fixed: '#390b00'
  on-secondary-fixed-variant: '#842600'
  tertiary-fixed: '#bfedd7'
  tertiary-fixed-dim: '#8bd6b6'
  on-tertiary-fixed: '#002116'
  on-tertiary-fixed-variant: '#254e3f'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  stats-xl:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '800'
    lineHeight: 48px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  baseline: 4px
  section-gap: 2rem
  gutter: 1.5rem
  card-padding: 2rem
  margin-mobile: 1rem
  margin-desktop: 2.5rem
---

## Brand & Style

Bistro OS embodies a **Corporate/Modern** aesthetic tailored specifically for high-end hospitality management. The brand personality is professional, secure, and hyper-efficient, evoking the precision of a Michelin-star kitchen. 

The visual style utilizes a "Clean Enterprise" approach:
- **Precision and Order:** Heavy reliance on structured grids and clear information hierarchy.
- **Subtle Sophistication:** Use of muted background textures (stainless steel/kitchen motifs) at very low opacity (3%) to provide depth without distracting from functional tasks.
- **Trust-Oriented:** A palette of deep navys and technical teals reinforces a sense of stability and data security, while energetic orange accents highlight primary actions.

## Colors

The color system is designed for high legibility in professional environments:
- **Primary (#091426):** A deep, near-black navy used for branding, headers, and critical text. It provides the "anchor" for the UI.
- **Secondary (#ac3400):** A burnt orange used exclusively for primary action buttons and brand iconography. It provides high contrast against the cool-toned background.
- **Tertiary (#002f21):** A deep forest green utilized for "Secure State" indicators and success-related messaging.
- **Neutral Palette:** Built on a "Cool Grey" scale. `background` is a crisp `#f7f9fb`, while containers use a pure white `#ffffff` to pop against the subtle surface tints.
- **Functional Accents:** `outline-variant` is used for input borders to maintain a soft but visible structure.

## Typography

The system uses a dual-font approach to balance readability with a technical edge:
- **Primary Sans (Inter):** Used for all headings and body copy. It is selected for its neutral, highly legible character at small sizes.
- **Technical Mono (JetBrains Mono):** Reserved for labels, metadata, and security status indicators. This adds a "system-level" feel to the admin portal.
- **Hierarchy:** Strong contrast is achieved through aggressive weight stepping (from 400 for body to 800 for stats). Large headings use negative letter-spacing to maintain a tight, modern appearance.
- **Utility Styles:** Small labels often use uppercase with wide tracking for an "administrative" or "restricted" feel.

## Layout & Spacing

The system follows a **Fixed Grid** philosophy for centralized tools like login portals, transitioning to a **Fluid Grid** for dashboard views.

- **Grid System:** A 12-column grid with 24px (1.5rem) gutters is standard for desktop layouts. 
- **Rhythm:** An 8px base unit (referenced as 2x baseline) governs all internal component spacing.
- **Login/Admin Focus:** Centered containers are capped at 448px (max-w-md) to maintain focus and minimize eye travel during high-frequency data entry.
- **Responsive Behavior:** Side margins shrink to 16px on mobile devices, with primary action buttons spanning the full width of their containers.

## Elevation & Depth

Hierarchy is established through a combination of **Tonal Layering** and **Ambient Shadows**:

- **Surface Tiers:** Backgrounds use a slightly dimmed surface (`#f7f9fb`), while primary interactive cards use the "Lowest" surface (`#ffffff`) to create a clear visual lift.
- **Shadow Profile:** The system uses a highly diffused, low-opacity shadow for main containers: `0 16px 32px -12px rgba(9, 20, 38, 0.1)`. This shadow is tinted with the Primary Navy color rather than pure black, ensuring a softer, more integrated appearance.
- **Interaction Depth:** Buttons utilize a subtle `shadow-sm` on rest, and a slight scale-down (98%) on active states to provide tactile feedback without traditional skeuomorphism.

## Shapes

The shape language is **Soft and Precise**:
- **Core Radius:** Standard components (inputs, buttons) use a 0.5rem (8px) radius.
- **Container Radius:** Primary cards and modals use an 0.75rem (12px) radius to distinguish structural elements from interactive ones.
- **Pill Shapes:** Status badges and secondary indicator chips use a `full` (9999px) radius to separate them from the rectangular grid of the form fields.

## Components

### Buttons
- **Primary:** Burnt orange background, white text, 8px radius. Features an icon (e.g., `arrow_forward`) for directional flow.
- **MFA/Utility:** 48x48px square buttons with 8px radius, featuring centered icons. High-contrast border (`outline-variant`) that shifts to `primary` on hover.

### Input Fields
- **Floating Label Design:** Uses a stacked layout where the label sits inside the input. On focus, the label scales down (90%) and shifts upwards.
- **Visual State:** Background uses `surface-container` to differentiate from the card surface. Borders are 1px solid `outline-variant`, becoming `primary` on focus.

### Chips & Badges
- **Security Badge:** Pill-shaped, using 30% opacity of the tertiary-fixed color. Combines a 16px icon with `label-md` JetBrains Mono text.

### Cards
- **Primary Card:** White background, 12px radius, deep tinted shadow. Includes a 1px border of `surface-container-highest` for crisp definition on high-DPI displays.
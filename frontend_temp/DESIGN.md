---
name: Lumina Dining
colors:
  surface: '#121414'
  surface-dim: '#121414'
  surface-bright: '#37393a'
  surface-container-lowest: '#0c0f0f'
  surface-container-low: '#1a1c1c'
  surface-container: '#1e2020'
  surface-container-high: '#282a2b'
  surface-container-highest: '#333535'
  on-surface: '#e2e2e2'
  on-surface-variant: '#cbc3d7'
  inverse-surface: '#e2e2e2'
  inverse-on-surface: '#2f3131'
  outline: '#958ea0'
  outline-variant: '#494454'
  surface-tint: '#d0bcff'
  primary: '#d0bcff'
  on-primary: '#3c0091'
  primary-container: '#a078ff'
  on-primary-container: '#340080'
  inverse-primary: '#6d3bd7'
  secondary: '#dabcea'
  on-secondary: '#3d274c'
  secondary-container: '#553d64'
  on-secondary-container: '#c8abd8'
  tertiary: '#c8c5ce'
  on-tertiary: '#303037'
  tertiary-container: '#928f98'
  on-tertiary-container: '#292930'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e9ddff'
  primary-fixed-dim: '#d0bcff'
  on-primary-fixed: '#23005c'
  on-primary-fixed-variant: '#5516be'
  secondary-fixed: '#f3daff'
  secondary-fixed-dim: '#dabcea'
  on-secondary-fixed: '#271236'
  on-secondary-fixed-variant: '#553d64'
  tertiary-fixed: '#e4e1ea'
  tertiary-fixed-dim: '#c8c5ce'
  on-tertiary-fixed: '#1b1b22'
  on-tertiary-fixed-variant: '#47464d'
  background: '#121414'
  on-background: '#e2e2e2'
  surface-variant: '#333535'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 64px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 40px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-sm:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 48px
  xl: 80px
  container-max: 1440px
  gutter: 24px
  margin-desktop: 64px
  margin-mobile: 20px
---

## Brand & Style

This design system targets an affluent, tech-savvy demographic seeking exclusive culinary experiences curated by artificial intelligence. The brand personality is **sophisticated, forward-thinking, and cinematic**. 

The aesthetic is rooted in **Glassmorphism**, utilizing deep atmospheric layering to create a sense of infinite depth. By leveraging translucent surfaces and vibrant background blurs, the UI feels lightweight and premium, mimicking high-end hardware interfaces. The emotional response should be one of discovery and prestige—shifting the app from a mere utility to a luxury concierge service.

## Colors

The palette is anchored in a **Deep Navy (#05050A)** base to provide a "true black" canvas that allows vibrant elements to pop. **Deep Purple (#1A0529)** is used for radial background gradients to provide organic depth and prevent a flat appearance.

**Vibrant Violet (#8B5CF6)** serves as the primary action color, used sparingly for call-to-actions, selection states, and AI-driven insights to signify intelligence and energy. **Glassy White (#FFFFFF1A)** is the functional foundation for all containers, creating the signature frosted-glass effect when paired with a `backdrop-filter: blur(20px)`.

## Typography

The typography system pairs the geometric precision of **Outfit** for headings with the systematic clarity of **Inter** for functional text. 

Headlines utilize tighter letter-spacing and bold weights to command attention against the dark backgrounds. Display sizes should often incorporate a subtle text-shadow or be placed atop high-contrast imagery to maintain legibility. Body text is prioritized for readability with generous line heights, while labels use uppercase styling to differentiate metadata from primary content.

## Layout & Spacing

This design system follows a **Fixed Grid** philosophy for desktop to maintain a cinematic, magazine-like composition. 

- **Desktop (1440px+):** A 12-column grid with 24px gutters and 64px side margins. Content is often centered with wide whitespace to evoke luxury.
- **Tablet (768px - 1439px):** An 8-column grid with 24px gutters and 40px margins.
- **Mobile (Up to 767px):** A 4-column fluid grid with 16px gutters and 20px margins.

Spacing follows an 8px base unit. Component internal padding should be generous (typically 24px or 32px) to support the "breathable" high-end feel.

## Elevation & Depth

Depth is not communicated through traditional drop shadows, but through **Backdrop Blurs** and **Inner Glows**.

1.  **Level 0 (Base):** Deep Navy background with subtle Deep Purple radial gradients.
2.  **Level 1 (Cards/Panels):** Glassy White (10% opacity) with a 20px backdrop blur. A 1px solid border (15% white) defines the edge.
3.  **Level 2 (Modals/Popovers):** Higher opacity glass (15%) with a more intense blur (40px) and a subtle 1px white top-stroke to simulate light hitting the edge.
4.  **Accent Depth:** Interactive elements like the primary button use a soft "bloom" effect—a primary-colored outer glow (drop shadow with 20px+ blur) rather than a dark shadow.

## Shapes

The design system uses **Rounded (0.5rem base)** geometry to balance modern precision with an approachable, organic feel. 

- **Cards & Containers:** Use `rounded-xl` (1.5rem) to create a soft, protective feel for restaurant imagery.
- **Buttons & Inputs:** Use `rounded-lg` (1rem) to maintain a distinct, tactile shape.
- **Interactive Chips:** Use full pill-shaped rounding for category tags and filters.
- **Visual Flourish:** Use "Squircle" masks for AI profile avatars and featured restaurant icons to further differentiate from standard UI libraries.

## Components

### Buttons
- **Primary:** Gradient fill (Primary to a slightly lighter violet), white text, `rounded-lg`. On hover, increase the outer bloom (shadow).
- **Secondary (Glass):** Glassy White background, 1px border, white text. Backdrop blur is essential.

### Cards
Restaurant cards are the centerpiece. They feature full-bleed imagery with a glass-morphic overlay at the bottom for the restaurant name and rating. The entire card should have a 1px "inner glow" border.

### Inputs
- **Search:** Large, glass-morphic fields with "Outfit" placeholder text. Icons should be thin-stroke (1.5px) to maintain the sleek aesthetic.
- **Focus State:** Instead of a heavy border, the backdrop-blur intensity should increase, and the border-color should transition to the Primary Violet.

### AI Recommendations (Special Component)
AI-generated content should be framed with a subtle, shimmering gradient border that cycles through the Violet and Purple palette, distinguishing machine-intelligence suggestions from standard search results.

### Lists & Navigation
Vertical navigation lists use a high-contrast active state: a vertical violet bar on the left and a subtle violet tint on the glass background of the selected item.
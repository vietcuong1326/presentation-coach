---
name: frontend-app-builder
description: Frontend UI/UX implementation and redesign guide for AI Presentation Coach (React + TypeScript + Vite + Tailwind CSS + Lucide). Enforces feedback-first hierarchy, clean component architecture, complete UI states, and browser verification within MVP scope.
---

# Frontend App Builder — AI Presentation Coach

Use this skill when building, refining, or redesigning frontend screens and components in `frontend/src/`. Act first as a product designer aligned with [UI_UX.md](./UI_UX.md) and [SRS_MVP.md](./SRS_MVP.md), then as a senior React + TypeScript engineer.

## 1. Product & Visual Standards (Non-Negotiable)

1. **Feedback-First, Score-Second**:
   - Never display a numeric score badge as the primary hero/focal element.
   - Prioritize qualitative coaching: overall summary, priority actions, strengths, areas for improvement (observation, evidence/timestamp/slide, impact, recommendation), and rubric details at the bottom.
   - Clearly surface `NOT_EVALUATED` criteria and limitations; never display missing evidence as `0`.
2. **Calm, High-Readability Aesthetic**:
   - Follow the established palette (`bg-slate-50` canvas, `bg-white` surfaces, `text-slate-900`/`slate-600` ink, `blue-600` primary accent, semantic `emerald`/`amber`/`rose` statuses).
   - Use gradients sparingly (e.g., primary CTA banners or drawer headers); prioritize generous whitespace and long-form reading comfort.
   - Avoid visual filler: no decorative fake metrics, unrequested hero eyebrows/kicker pills, or cluttered card grids where a clean list/band works better.
3. **Typography & Icon Consistency**:
   - Define deliberate typography on every control (buttons, tabs, inputs, badges, status pills, table/list rows) — never rely on unstyled browser defaults.
   - Use `lucide-react` consistently across all views, matching stroke weight, optical size (`w-3.5 h-3.5` in compact controls, `w-4 h-4` / `w-5 h-5` in headers/cards), and baseline alignment.
4. **Scope & Security Boundaries**:
   - Stay strictly within MVP scope defined in [AGENTS.md](./AGENTS.md) and [TASKS.md](./TASKS.md) (do not add eye-contact/posture UI, speaker-identity recognition, revision tracker, PDF export, or admin portal).
   - Never reference `SUPABASE_SERVICE_ROLE_KEY` or secret credentials in `frontend/src/`.

## 2. Tech Stack & Architecture Rules

- **Framework**: React 18, TypeScript, Vite, React Router v6, Tailwind CSS, `lucide-react`, Supabase JS client (`@supabase/supabase-js`).
- **Thin Routing Shell**: Keep [App.tsx](./frontend/src/App.tsx) focused on route definitions and auth guards (`ProtectedRoute`).
- **API & Auth Layer**: Put all backend requests and TypeScript payload interfaces in [client.ts](./frontend/src/api/client.ts); obtain access tokens from [AuthContext.tsx](./frontend/src/context/AuthContext.tsx). Never ship hardcoded mock data in production screens.
- **Component Hygiene**:
  - Extract repeated UI patterns (status badges, feedback cards, confirmation modals/actions, empty/error banners) into focused components under `frontend/src/components/` rather than duplicating JSX across pages.
  - Keep page components cleanly structured by section and state.
- **Optional Visual Concepting**: For major new screens or full-page redesigns where layout exploration is helpful, you may use the `image-generator` subagent to draft a visual reference or custom empty-state illustration first, then translate it into Tailwind/Lucide tokens. Do not block small UI tasks or bug fixes on image generation.

## 3. Required UI States & Core Surfaces

Every data-driven screen (`Dashboard`, `NewProject`, `ProjectDetail`, `EvaluationReport`, `ChatCoach`) must explicitly handle all 5 states:

1. **Loading**: Clear spinner/skeleton with descriptive status text.
2. **Empty**: Helpful message and primary CTA (e.g., create first project, start evaluation, starter chat prompts).
3. **Error**: Actionable error banner with retry or safe back-navigation (no swallowed errors).
4. **Partial**: Distinct `PARTIAL` evaluation state, `NOT_EVALUATED` rubric badges, and visible timeline/overlap warnings.
5. **Success**: Clean interactive controls with immediate state updates (e.g., optimistic or synced chat messages, project/evaluation deletion, tab/scope filtering).

### Surface-Specific Guidelines

- **Dashboard**: Recent Projects & Evaluation History tabs, clear status pills (`PENDING`, `PROCESSING`, `COMPLETED`, `PARTIAL`, `FAILED`), direct actions to **Reopen Report**, **Chat**, or **Delete** (with confirmation), plus primary CTA **New Evaluation**.
- **Project Workspace**: Clear format and configured size limits (`.pdf`/`.pptx` max 20MB; `.mp3`/`.wav`/`.m4a`/`.mp4` max 50MB), slide text preview, group member time-range warnings, and previous evaluations list.
- **Evaluation Report**: Recommended section order from [UI_UX.md](./UI_UX.md) (Overall feedback -> Priority actions -> Strengths -> Improvements with `ALL`/`GROUP`/`INDIVIDUAL` scope filter -> 20-criteria rubric accordion at bottom).
- **AI Coach Chat**: Scoped to the current Evaluation, session switcher to reopen prior sessions or start a new chat, suggested coaching prompts, and clear distinction between grounded report feedback and general guidance.

## 4. Implementation Checklist

Before editing:
- Read the target page/component and [client.ts](./frontend/src/api/client.ts) to match existing types and patterns.
- Check responsive behavior (`sm:`, `md:`, `lg:` breakpoints) so desktop-first layouts collapse cleanly on mobile without horizontal overflow.
- Respect `prefers-reduced-motion` when adding transitions or animations.

## 5. Verification

After editing frontend code:

1. **Type Check & Production Build**:
   - Run `npm run build` (`tsc && vite build`) in `frontend/` and verify zero TypeScript or bundler errors.
2. **Browser Verification (when UI layout or interaction changes)**:
   - Use the `browser` subagent (with the app running outside the sandbox if local) to inspect desktop and mobile viewports, verify no clipped/overlapping text, and click through the affected flow (`Login -> Dashboard -> Project -> Evaluation Report -> Chat Coach`).
3. **Cleanup**:
   - Remove any temporary screenshots or scratch files from the workspace before handoff.

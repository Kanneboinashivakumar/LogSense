# LogSense — Build Prompts (Copy-Paste Ready)

Four phases. Each phase = one prompt block you hand to Fable/Antigravity. Don't start a phase until the previous one's test checklist passes. Every prompt below already bakes in: self-tests, mobile+desktop responsiveness, production-grade code quality, and clean SaaS-level UI — you don't need to remind it each time.

---

## PHASE 1 — Deterministic Core Engine (backend logic + self-tests, no UI yet)

```
Build the core Python analysis engine for LogSense, a log incident detection tool.

CONTEXT:
Input is raw log text, one entry per line, format: "YYYY-MM-DD HH:MM:SS LEVEL MESSAGE"
e.g. "2026-08-16 15:02:11 ERROR Database connection timeout"
Levels are INFO, WARNING, or ERROR.

BUILD THESE FUNCTIONS, in this file structure:
- parser.py       -> parse_logs(raw_text) -> list[dict] with keys timestamp, level, message.
                      Skip malformed lines without crashing; collect skipped-line warnings separately.
- bucketing.py     -> bucket_by_hour(entries) -> dict keyed by "YYYY-MM-DD HH:00" with total_count,
                      error_count, warning_count per hour.
- analysis.py      -> find_peak_hour(buckets)
                    -> calculate_baseline_deviation(buckets)  [local baseline = avg of surrounding hours]
                    -> detect_spikes(buckets) implementing CONFIDENCE-TIERED logic:
                         - >=3 comparable neighbor hours available: compute mean + std dev of neighbors,
                           z-score, flag spike if z-score > 2. confidence = "HIGH"
                         - 1-2 neighbors available: fall back to plain % deviation from available baseline
                           (do not compute z-score with insufficient samples). confidence = "MEDIUM"
                         - baseline == 0: any nonzero error count is a spike by definition. confidence = "MEDIUM"
                         - no usable neighbors at all (edge of dataset): still report raw count,
                           confidence = "LOW", never fabricate a baseline.
                    -> classify_severity(deviation_pct) -> "Normal" | "Warning" | "Critical"
                         thresholds: <50% Normal, 50-150% Warning, >150% Critical
- patterns.py      -> classify_pattern(messages: list[str]) -> str
                      keyword-match against categories: Database (db, connection, timeout, sql, postgres, mysql),
                      Auth (auth, token, login, unauthorized, jwt), API (api, request, endpoint, 4xx, 5xx),
                      Network (network, dns, socket, connection refused), Other (fallback).
                      Return majority category for a given hour's error messages.
- incident.py      -> build_incident_card(hour, buckets, spikes, severities, patterns) -> dict with
                      category, severity, deviation_pct, window, error_count, baseline, confidence.
                    -> build_evidence_panel(incident_card, z_score) -> dict with error_count, local_baseline,
                      deviation_pct, z_score (nullable), confidence, dominant_pattern, severity, and a
                      one-sentence plain-English "reason" string. The reason wording must differ when
                      confidence is MEDIUM/LOW (mention "limited surrounding data") vs HIGH.
- report.py        -> generate_report(buckets, peak_hour, spikes) -> formatted string: hour-wise error
                      breakdown, peak error hour, spike alerts. This must stand alone as a correct answer
                      to the literal problem statement even with no UI at all.

CODE QUALITY REQUIREMENTS:
- Type hints on every function signature.
- Docstrings explaining what each function does and why (especially the confidence-tiering logic).
- No bare except clauses — catch specific exceptions.
- Pure functions where possible (no hidden global state).

WRITE TESTS (pytest, in a tests/ folder):
- Test parser against valid lines, malformed lines, and empty input.
- Test bucketing against a hand-verifiable small dataset (assert exact counts).
- Test peak hour detection against a dataset with a known, obvious peak.
- Test detect_spikes against THREE scenarios in separate test functions:
  1. Dataset with >=3 neighbors around the spike hour -> assert confidence == "HIGH" and z-score used.
  2. Tiny dataset with only 1-2 total neighbor hours -> assert confidence == "MEDIUM", no crash.
  3. All-zero baseline with one nonzero hour -> assert that hour is flagged, confidence == "MEDIUM".
  4. Edge-of-dataset hour with no usable neighbor on one side -> assert confidence == "LOW".
- Test classify_pattern returns correct majority category on a mixed-message input.
- Test generate_report output contains all three required elements: hourly breakdown, peak hour, spike alert.

Run all tests and show me the output. Do not proceed to any UI work in this phase — backend logic only.
```

**Checkpoint before moving on:** All pytest tests pass. `generate_report()` output alone would satisfy someone grading strictly against the problem statement PDF, with zero UI involved.

---

## PHASE 2 — API Layer + Responsive Foundation (backend wired to a working, plain frontend)

```
Wire the Phase 1 engine into a FastAPI backend and build the minimum responsive frontend shell.

BACKEND:
- Single FastAPI app, one POST endpoint /analyze that accepts raw log text (from file upload OR
  pasted text in a JSON body) and returns a JSON response containing: hourly buckets, peak hour,
  all spike/incident cards, all evidence panels, and the plain-text report string from Phase 1.
- Add basic input validation: reject empty input with a clear error message, handle very large
  files without hanging (stream or cap reasonably with a friendly message if exceeded).
- Add a pytest test that hits /analyze with the same synthetic dataset from Phase 1 and asserts
  the JSON response contains the expected incident and confidence values end-to-end.

FRONTEND (single HTML/CSS/JS file, no build tooling, no React):
- A responsive layout using CSS Grid/Flexbox with mobile-first breakpoints (test at 375px, 768px,
  1440px widths). On mobile: single-column stacked layout. On desktop: the dashboard panels can
  sit side by side where it makes sense.
- Two input methods: drag-and-drop file upload zone, and a textarea for pasting logs directly.
  Both trigger the same /analyze call.
- Render the RAW JSON response as a simple readable list for now (hourly counts, peak hour,
  spike list) — no styling polish yet, that's Phase 3. The goal here is just: input works,
  API call works, real data renders, on both mobile and desktop viewport sizes.

Show me the working end-to-end flow: paste sample logs -> click analyze -> real backend-computed
data appears on screen, correctly, at both a mobile and a desktop viewport width.
```

**Checkpoint before moving on:** Full request/response loop works on a live server. Resizing the browser to phone width doesn't break the layout or cut off content.

---

## PHASE 3 — Production SaaS UI (the wow-factor visual pass)

```
Now take the working Phase 2 dashboard and turn it into a polished, production-grade SaaS UI.
This is a visual/UX pass only — do not change any backend logic or API contract.

VISUAL DIRECTION:
- Dark "terminal/void" aesthetic: near-black background (#0a0a0a range), monospace font for
  data/numbers (e.g. JetBrains Mono or similar from a CDN), a single accent color used
  consistently (pick one — e.g. terminal violet or amber — not multiple competing accents).
- This should look like a real monitoring product (think Datadog/Grafana incident view),
  not a college project table. Clear visual hierarchy: status banner at the top is the
  first thing anyone sees.

COMPONENTS TO BUILD:
1. Status banner: full-width, color-coded by highest current severity
   (green/normal, amber/warning, red/critical), large and unmissable.
2. Error trend chart: bar chart of hourly error counts, spike hour(s) visually distinct
   (color + subtle pulse animation), rendered with lightweight inline SVG or Chart.js (CDN).
3. Incident card(s): category, severity, deviation %, time window, error count — one card
   per detected incident, clearly separated if there are multiple.
4. "Why was this flagged?" — collapsed by default, smooth expand/collapse animation
   (CSS transition, not a hard show/hide snap), showing the evidence panel data from
   Phase 1 plus the reason sentence.
5. Recommended actions checklist, mapped by category (Database/Auth/API/Network — write a
   short static list of 3-4 sensible checks per category).
6. Input area (upload/paste) restyled to match the aesthetic, with a clear loading state
   while /analyze is in flight (skeleton loader or subtle spinner, not a frozen screen).

ANIMATION RULES (important — restraint, not decoration):
- Use animation ONLY for: state transitions (idle -> loading -> result), the expand/collapse
  of the evidence panel, the status banner color change, and a subtle pulse on the spike bar.
- No animation on static content, no bouncing/spinning logos, no unnecessary motion.
  Every animation must communicate a state change, not just look cool.
- Respect prefers-reduced-motion media query — disable non-essential animations for users
  who have that OS setting on.

RESPONSIVENESS:
- Re-verify at 375px, 768px, 1440px after this visual pass — confirm nothing overlaps,
  text doesn't overflow containers, and the chart is legible (not squished) on mobile.
- Touch targets (upload zone, expand/collapse toggle, buttons) must be comfortably tappable
  on mobile — no tiny click targets.

CODE QUALITY:
- Keep CSS organized with custom properties (CSS variables) for the color palette and spacing
  scale, not magic numbers scattered everywhere.
- Comment the animation timing choices briefly.

Show me the final result at all three viewport widths, and confirm the loading/expand
animations feel smooth, not janky.
```

**Checkpoint before moving on:** Dashboard looks and feels like a real product at every viewport size. No animation exists that doesn't communicate a state change.

---

## PHASE 4 — Full Integration Testing + Edge Case Hardening

```
Do a full pass of integration testing and edge-case hardening on the complete LogSense app
(Phases 1-3 combined). This is a quality/robustness phase — no new features.

TEST THESE SCENARIOS END TO END (through the actual UI, not just backend unit tests):
1. A clean dataset with one obvious, unambiguous spike — confirm correct incident card,
   correct severity, correct "why flagged" evidence, correct recommended actions category.
2. A dataset with NO spikes at all (normal, stable traffic) — confirm the UI shows a
   green/normal status, not a broken or empty state.
3. A dataset with MULTIPLE separate spikes in different hours — confirm multiple incident
   cards render correctly and don't overlap or clobber each other.
4. A tiny dataset (under 5 total log lines) — confirm graceful LOW/MEDIUM confidence handling,
   no crash, no misleading "HIGH confidence" claim on insufficient data.
5. Malformed/garbage input mixed with valid lines — confirm valid lines still get analyzed
   and the user gets a clear, non-technical warning about skipped lines (not a raw stack trace).
6. Empty input submitted — confirm a clear, friendly error message, not a silent failure
   or ugly server error.
7. A very large log file (a few thousand lines) — confirm it completes in a reasonable time
   and the UI shows a loading state throughout rather than appearing frozen.

For each scenario, report: what you tested, what happened, and confirm it matches the
expected behavior above. Fix anything that doesn't. Re-run the full pytest suite from
Phase 1 one final time and confirm everything is still green after all the UI changes.

Finally, do a final responsive check: full walkthrough of the app at mobile width (375px)
from empty state through to a rendered incident, confirming every step is usable on a
touch screen with no horizontal scrolling anywhere.
```

**Checkpoint:** This is your demo-ready state. Everything in the problem statement is satisfied, the wow-factor features work, it's tested against edge cases, and it works cleanly on both phone and laptop.

---

## After Phase 4

Only now consider Tier 3 stretch features (Ask Your Logs, export report, timeline strip) from the main spec — as separate, isolated prompts, each with its own test checkpoint, each with a working fallback if it fails. Never let a Tier 3 feature touch or destabilize anything from Phases 1–4.

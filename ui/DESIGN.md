# Design picks

We merge the best parts of several reference designs instead of copying one. Each reference gets a verdict:
**take** (use as is), **adapt** (use with changes, noted), **skip** (does not fit, with the reason).
The look is then built once, on shadcn/ui, from the merged list.

## Rules that every pick has to respect

1. **Real data only.** The portal gives us assignments, deadlines, submissions, marks, attendance, exams and lectures.
   It does not give teachers, lesson durations, avatars or learning progress. Nothing is invented to fill a layout.
2. **Deadlines stay above the fold.** Students open this to see what is due and to upload. Up next and the deadline list
   come before anything decorative.
3. **Colour never carries status.** Course colours identify courses. Status (overdue, due soon, submitted) is shown by
   label and icon in the shared status colours, so a red course card cannot read as "overdue".
4. **Contrast.** Text is at least 4.5:1 (large text 3:1) on every surface in both themes. A bright accent is used for
   fills with dark text, not as text on white.
5. **One main action per screen** (Upload), reachable by keyboard.
6. **Components, not custom drawing:** shadcn/ui parts, customised through theme tokens.

## References

### 1. Ronas IT, "Online Course Student Dashboard" ([Dribbble](https://dribbble.com/shots/26411864-Online-Course-Student-Dashboard))
A "My courses" screen: bold flat-colour course cards with a progress bar, a lime promo tile, a lessons list, outlined
filter pills, large radii on a light grey shell.

- **Take:** large radii (16 to 24 px); a lime action accent with dark text; outlined pill filters.
- **Adapt:** course cards become a compact row (or horizontal scroll) of colour-coded tiles showing submitted/total and
  the next deadline, below Up next, not above it. The lime promo tile becomes Up next.
- **Skip:** teacher names, lesson durations, avatar stacks and "continue" (no such data); full-size cards that push the
  deadline list below the fold; colour as status.

### 2. Denys Solonenko, "Campus | Student Dashboard for University LMS" ([Dribbble](https://dribbble.com/shots/27789570-Campus-Student-Dashboard-for-University-LMS))
A calm student home: a slate-blue greeting banner with a semester ring and four figures, a live "This week" timetable,
a right column of Deadlines (with days-left chips), Course progress bars and Latest grades.

- **Take:** the structure (it answers "what is due next" first); the greeting banner with a ring and a few key figures;
  the Deadlines list with days-left chips; per-course progress bars; the quiet palette and white panels.
- **Adapt:** banner figures from real data only (submitted/total, due today, overdue, attendance %); the week view uses
  the CMS timetable we already read, with deadlines placed on their days; "Latest grades" = our Results data.
- **Skip:** the AI study plan (invented content, no data behind it); "weighted average" (we show CGPA instead).

### 3. Denys Solonenko, "Helio | Solar Plant Monitoring Dashboard" ([Dribbble](https://dribbble.com/shots/27792265-Helio-Solar-Plant-Monitoring-Dashboard))
A dark monitoring console: KPI strip, one large chart, a "Needs attention" alert panel, dense mono numerals.

- **Take:** the dark theme treatment (charcoal surfaces, one warm accent, mono numbers); the KPI strip; the
  **Needs attention** panel.
- **Adapt:** Needs attention = overdue work, due today, attendance under the minimum, an exam inside 7 days. The large
  chart becomes deadline load per day for the next 14 days (derived from real deadlines).
- **Skip:** the very small dense type (too tiring for a student checking in a hurry); solar-specific content.

### 4. Ronas IT, "Student Website - Campus Life Portal" ([Dribbble](https://dribbble.com/shots/27813824-Student-Website-Campus-Life-Portal))
A lifestyle portal: photo hero ("Make Today Count"), Focus Time, Study Rhythm, Focus Map, a dark day-schedule tile.

- **Take:** the dark day-schedule tile idea for today's classes.
- **Skip:** photo hero (spends the top of the screen on decoration); Focus Time, Study Rhythm and Focus Map (we cannot
  measure study time, so it would be invented). Weakest fit of the set.

### 5. Harsh Pal, "Designo - Streamlined LMS Dashboards" ([Figma Community](https://www.figma.com/community/file/1395793003651190548/designo-streamlined-lms-dashboards))
A generic LMS kit (CC BY 4.0). Its Assignments page is a plain table: title, course, due date, status chip, Submit link.

- **Take:** it confirms the table we already have (status chip plus one action per row).
- **Skip:** pagination (we have dozens of rows, not thousands); small low-contrast text; an orange accent that reads as
  status. Ideas only, no assets copied.

## Merged direction (prototype built: Home page, 2026-11-18)
Campus gives the **home layout and the calm light theme**; Helio gives the **dark theme and "Needs attention"**; Ronas gives the
**lime action colour and big radii** (used for buttons and the Up next tile only). Course colour appears as a small dot or progress bar,
never as a full card and never as status.

## Colour (decided 2026-11-18)
Why the first pass felt flat: grey neutrals with no hue, a dull steel banner next to a lone acid-lime, and random course colours.
Fix, applied to three switchable palettes (user menu, bottom of the sidebar; default Royal):
- every neutral carries the palette hue (a tint, not a grey);
- the banner is a rich colour with a second stop for depth, and lime is the only primary action colour;
- course colours are OKLCH at near-equal lightness and chroma, so no course shouts;
- contrast checked numerically: body, muted text and lime-button text are all at least 5.7:1 in all six themes.
**Royal** (royal blue + lilac-tinted neutrals), **Ink** (warm paper + near-black banner), **Forest** (cream and sage + deep green),
**Ember** (from the website: warm near-black and the #fd693d orange; orange is the primary action here, and its warning colour is
shifted to yellow so it never reads as the action colour). Shared polish: palette-tinted shadows, a primary-coloured marker on the
active sidebar item, a soft highlight in the banner and on the Up next tile, chart bars tied to the banner colour.

## Update 2026-11-18 (second pass)
- Each palette now has its own action colour, so no two look alike: **Royal** aqua, **Ink** monochrome (black in light, cream in dark),
  **Forest** lime, **Ember** orange (the website's). Banner ring, glow and the Up next tile button follow the palette (`--glow`, `--tile-btn`).
- Course colours are an analogous family around the palette hue (`--course-h`); they identify courses only.
- Progress bars use one calm colour (the banner tone) and turn green when a course is fully submitted.
- Home carries complete information: banner figures with context (lowest attendance, last GPA), a per-course panel (submitted, percent,
  next due or "n overdue, not submitted", attendance), deadlines with date and time, an Exams panel, a Results trend. The banner is a
  greeting row plus a KPI row, so it holds at any width (a one-row layout broke at about 1180 px).
- Contrast: lowest measured pair across all eight themes is 5.9:1.

## Whole app (2026-11-18, third pass)
Pages, all on real data from the engine, in the same style: Home, Assignments (search, sort, grouped sections, file downloads, marks,
extension notes, the upload/replace/delete sheet), Attendance (ring per course, minimum marker, advice, class by class), Exams (by type,
date/time/room/seat, survey and fee flags), Lectures (select and download, New badges, open folder), Announcements, Results (semester
tabs, trend, what-if per course, same-grade scenarios), Settings (theme, palettes, folders, about). Routing is the URL hash, so back and
forward work. The Settings page does not yet manage sign-in, alerts, automatic checks or cloud checks: those stay in the desktop app.

## Account settings (2026-11-18, fourth pass)
The Settings page now manages what the desktop app's does: portal account (saved and verified through a sign-in), appearance, notifications
(with voice, volume and test alert), campus tracking, automatic checks, start with Windows, tray and updates, email, phone pairing (QR),
calendar, cloud checks (GitHub device sign-in with the same consent text) and clearing saved data. Rules kept in the engine
(settings_api.py): a secret is never returned (only "set"), an empty secret field means "keep", updates are validated against an allow-list
(types, bounds, single-line), and a source run never turns the installed app's background tasks on or off.

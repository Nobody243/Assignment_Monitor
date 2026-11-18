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

## Merged direction (proposal, not built)
Campus gives the **home layout and the calm light theme**; Helio gives the **dark theme and "Needs attention"**; Ronas gives the
**lime action colour and big radii** (used for buttons and the Up next tile only). Course colour appears as a small dot or progress bar,
never as a full card and never as status.

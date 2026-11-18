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

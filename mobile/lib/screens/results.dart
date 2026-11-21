import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../data.dart';
import '../logic.dart';
import '../theme.dart';
import 'widgets.dart';

enum _View { transcript, calculator }

String _fmt(double? v) => v == null ? '–' : v.toStringAsFixed(2);

/// Results: the transcript read from the portal (CGPA, a trend, every semester and its courses) and a calculator for
/// "what if" grades and "what do I need" targets. Nothing typed into the calculator is saved or sent.
class ResultsPage extends StatefulWidget {
  const ResultsPage({super.key, required this.summary});
  final Summary summary;
  @override
  State<ResultsPage> createState() => _ResultsState();
}

class _ResultsState extends State<ResultsPage> {
  _View view = _View.transcript;
  final rows = [for (var i = 0; i < 4; i++) GradedCourse()];
  final prevCgpa = TextEditingController(), prevCredits = TextEditingController(), target = TextEditingController();

  @override
  void initState() {
    super.initState();
    for (final c in [prevCgpa, prevCredits, target]) { c.addListener(() => setState(() {})); }
  }

  @override
  void dispose() { prevCgpa.dispose(); prevCredits.dispose(); target.dispose(); super.dispose(); }

  /// Credit hours the transcript already counts: every course with a grade.
  double get _graded {
    var n = 0.0;
    for (final s in widget.summary.terms) { for (final c in s.courses) { if (c.grade != null && gradePoints.containsKey(c.grade)) n += c.credits; } }
    return n;
  }

  void _useTranscript() {
    final c = widget.summary.cgpa;
    if (c == null) return;
    prevCgpa.text = c.toStringAsFixed(2);
    prevCredits.text = _graded.round().toString();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.summary;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
        child: SizedBox(width: double.infinity, child: SegmentedButton<_View>(
          showSelectedIcon: false,
          segments: const [
            ButtonSegment(value: _View.transcript, label: Text('Transcript'), icon: Icon(LucideIcons.award, size: 18)),
            ButtonSegment(value: _View.calculator, label: Text('Calculator'), icon: Icon(LucideIcons.calculator, size: 18)),
          ],
          selected: {view},
          onSelectionChanged: (v) => setState(() => view = v.first),
        )),
      ),
      Expanded(child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 240),
        child: KeyedSubtree(key: ValueKey(view), child: view == _View.transcript ? _Transcript(summary: s, graded: _graded) : _calculator(context)),
      )),
    ]);
  }

  // ------------------------------------------------------------------------------------------------ calculator
  Widget _calculator(BuildContext context) {
    final t = Theme.of(context);
    final pg = double.tryParse(prevCgpa.text), pc = double.tryParse(prevCredits.text) ?? 0, tg = double.tryParse(target.text);
    final gpa = gpaOf(rows), cgpa = cgpaAfter(rows, pg, pc);
    final all = rows.fold<double>(0, (n, r) => n + (r.credits > 0 ? r.credits : 0));
    final goal = tg == null ? null : neededGpa(tg, pg, pc, all);
    String lowest(double need) {
      String? found;
      for (final g in gradePoints.entries) { if (g.value + 1e-9 >= need) found = g.key; }
      return found ?? '';
    }
    return ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
      // the answer first, so it stays in view while the grades below change it
      Container(
        padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 8),
        decoration: BoxDecoration(color: t.colorScheme.primaryContainer, borderRadius: BorderRadius.circular(28)),
        child: Row(children: [
          Expanded(child: _Figure('Semester GPA', _fmt(gpa), big: true)),
          Container(width: 1, height: 44, color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.2)),
          Expanded(child: _Figure(pg != null && pc > 0 ? 'New CGPA' : 'CGPA', _fmt(cgpa), big: true)),
          Container(width: 1, height: 44, color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.2)),
          Expanded(child: _Figure('Credit hours', all.round().toString())),
        ]),
      ),
      const SizedBox(height: 20),
      SectionTitle('This semester', trailing: 'Credit hours and grade'),
      for (final (i, r) in rows.indexed) Padding(padding: const EdgeInsets.only(bottom: 10), child: _GradeRow(
        index: i, course: r,
        onChanged: () => setState(() {}),
        onRemove: rows.length > 1 ? () => setState(() => rows.removeAt(i)) : null,
      )),
      if (rows.length < 10) OutlinedButton.icon(onPressed: () => setState(() => rows.add(GradedCourse())), icon: const Icon(LucideIcons.plus, size: 18), label: const Text('Add a course')),
      const SizedBox(height: 24),
      SectionTitle('Where you stand now', trailing: widget.summary.cgpa == null ? null : null),
      Row(children: [
        Expanded(child: TextField(controller: prevCgpa, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'CGPA so far', border: OutlineInputBorder()))),
        const SizedBox(width: 10),
        Expanded(child: TextField(controller: prevCredits, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Credit hours so far', border: OutlineInputBorder()))),
      ]),
      if (widget.summary.cgpa != null) Align(alignment: Alignment.centerLeft, child: TextButton.icon(onPressed: _useTranscript, icon: const Icon(LucideIcons.download, size: 16), label: const Text('Use my transcript'))),
      const SizedBox(height: 16),
      SectionTitle('A target'),
      TextField(controller: target, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Target CGPA', hintText: 'for example 3.50', border: OutlineInputBorder())),
      if (goal != null) Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: (goal.reachable ? Status.good(t.brightness) : Status.bad(t.brightness)).withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(goal.reachable ? LucideIcons.target : LucideIcons.circleAlert, color: goal.reachable ? Status.good(t.brightness) : Status.bad(t.brightness)),
            const SizedBox(width: 12),
            Expanded(child: Text(
              goal.reachable
                  ? (goal.needed <= 0 ? 'You are already above that target, whatever the grades.' : 'To finish on ${tg!.toStringAsFixed(2)} you need a semester GPA of ${_fmt(goal.needed)}${lowest(goal.needed).isEmpty ? '' : ': ${lowest(goal.needed)} or better in every course, on average'}.')
                  : '${tg!.toStringAsFixed(2)} is not reachable this semester: it needs ${_fmt(goal.needed)} and the maximum is 4.00. Straight As would reach ${_fmt(goal.best)}.',
              style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
            )),
          ]),
        ),
      ),
      const SizedBox(height: 12),
      const Muted('Nothing here is saved or sent anywhere.'),
    ]);
  }
}

class _Figure extends StatelessWidget {
  const _Figure(this.label, this.value, {this.big = false});
  final String label, value;
  final bool big;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), fg = t.colorScheme.onPrimaryContainer;
    return Column(mainAxisSize: MainAxisSize.min, children: [
      FittedBox(fit: BoxFit.scaleDown, child: Text(value, style: (big ? t.textTheme.headlineLarge : t.textTheme.headlineSmall)?.copyWith(fontWeight: FontWeight.w800, color: fg, fontFeatures: const [FontFeature.tabularFigures()]))),
      Text(label, style: t.textTheme.labelMedium?.copyWith(color: fg.withValues(alpha: 0.85))),
    ]);
  }
}

/// One course in the calculator: credit hours and grade picked with chips, no dropdowns to open.
class _GradeRow extends StatelessWidget {
  const _GradeRow({required this.index, required this.course, required this.onChanged, this.onRemove});
  final int index;
  final GradedCourse course;
  final VoidCallback onChanged;
  final VoidCallback? onRemove;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Card(child: Padding(
      padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('Course ${index + 1}', style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700))),
          if (onRemove != null) IconButton(tooltip: 'Remove this course', onPressed: onRemove, icon: Icon(LucideIcons.x, size: 18, color: t.colorScheme.onSurfaceVariant)),
        ]),
        Row(children: [
          Text('Credit hours', style: t.textTheme.labelMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
          const SizedBox(width: 10),
          Expanded(child: Wrap(spacing: 6, runSpacing: 4, children: [
            for (final c in [1, 2, 3, 4]) ChoiceChip(
              label: Text('$c'), showCheckmark: false,
              selected: course.credits == c.toDouble(),
              onSelected: (_) { course.credits = c.toDouble(); onChanged(); },
            ),
          ])),
        ]),
        const SizedBox(height: 8),
        SizedBox(
          height: 40,
          child: ListView(scrollDirection: Axis.horizontal, children: [
            for (final g in gradePoints.keys) Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                label: Text(g, style: const TextStyle(fontWeight: FontWeight.w700)), showCheckmark: false,
                selected: course.grade == g,
                onSelected: (on) { course.grade = on ? g : ''; onChanged(); },
              ),
            ),
          ]),
        ),
      ]),
    ));
  }
}

// ------------------------------------------------------------------------------------------------ transcript
class _Transcript extends StatelessWidget {
  const _Transcript({required this.summary, required this.graded});
  final Summary summary;
  final double graded;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final terms = summary.terms;
    if (terms.isEmpty && summary.cgpa == null) {
      return const EmptyState(icon: LucideIcons.award, title: 'No results yet', hint: 'They appear here once the portal publishes your grades.');
    }
    final done = terms.where((x) => x.complete && x.gpa != null).toList();
    final delta = done.length >= 2 ? done.last.gpa! - done[done.length - 2].gpa! : null;
    final courseCount = terms.fold<int>(0, (n, x) => n + x.courses.where((c) => c.grade != null).length);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
      Reveal(index: 0, child: Container(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
        decoration: BoxDecoration(color: t.colorScheme.primaryContainer, borderRadius: BorderRadius.circular(28)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('CUMULATIVE GPA', style: t.textTheme.labelSmall?.copyWith(letterSpacing: 0.8, fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer)),
              Text(_fmt(summary.cgpa), style: t.textTheme.displayMedium?.copyWith(fontWeight: FontWeight.w800, height: 1.05, color: t.colorScheme.onPrimaryContainer, fontFeatures: const [FontFeature.tabularFigures()])),
            ])),
            if (delta != null) Flexible(child: _Delta(delta: delta)),
          ]),
          if (done.length >= 2) ...[
            const SizedBox(height: 12),
            SizedBox(height: 70, width: double.infinity, child: CustomPaint(painter: _Trend(done.map((x) => x.gpa!).toList(), t.colorScheme.onPrimaryContainer))),
            const SizedBox(height: 4),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(done.first.name, style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.85))),
              Text(done.last.name, style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.85))),
            ]),
          ],
        ]),
      )),
      const SizedBox(height: 12),
      Reveal(index: 1, child: IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Expanded(child: _Tile(value: '${graded.round()}', label: 'credit hours graded')),
        const SizedBox(width: 10),
        Expanded(child: _Tile(value: '$courseCount', label: 'courses graded')),
        const SizedBox(width: 10),
        Expanded(child: _Tile(value: '${done.length}', label: done.length == 1 ? 'semester done' : 'semesters done')),
      ]))),
      const SizedBox(height: 20),
      const SectionTitle('Semesters'),
      for (final (i, term) in terms.reversed.indexed) Reveal(index: i + 2, child: Padding(padding: const EdgeInsets.only(bottom: 10), child: _TermCard(term: term, startOpen: i == 0))),
    ]);
  }
}

class _Delta extends StatelessWidget {
  const _Delta({required this.delta});
  final double delta;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final up = delta >= 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(99)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(up ? LucideIcons.trendingUp : LucideIcons.trendingDown, size: 16, color: t.colorScheme.onPrimaryContainer),
        const SizedBox(width: 6),
        Flexible(child: Text('${up ? '+' : ''}${delta.toStringAsFixed(2)} on last semester', maxLines: 2, style: t.textTheme.labelMedium?.copyWith(fontWeight: FontWeight.w700, color: t.colorScheme.onPrimaryContainer))),
      ]),
    );
  }
}

/// A line through each finished semester's GPA, scaled between 2.0 and 4.0 so a small change is still visible.
class _Trend extends CustomPainter {
  _Trend(this.values, this.color);
  final List<double> values;
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    const lo = 2.0, hi = 4.0;
    final pts = <Offset>[
      for (final (i, v) in values.indexed)
        Offset(8 + (size.width - 16) * (values.length == 1 ? 0.5 : i / (values.length - 1)), 8 + (size.height - 16) * (1 - ((v - lo) / (hi - lo)).clamp(0.0, 1.0))),
    ];
    final line = Paint()..color = color..style = PaintingStyle.stroke..strokeWidth = 3..strokeCap = StrokeCap.round..strokeJoin = StrokeJoin.round;
    canvas.drawPath(Path()..addPolygon(pts, false), line);
    for (final p in pts) {
      canvas.drawCircle(p, 5, Paint()..color = color);
    }
  }

  @override
  bool shouldRepaint(_Trend old) => old.values != values || old.color != color;
}

class _Tile extends StatelessWidget {
  const _Tile({required this.value, required this.label});
  final String value, label;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
      decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(22)),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        Text(value, style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.primary, fontFeatures: const [FontFeature.tabularFigures()])),
        Text(label, textAlign: TextAlign.center, style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      ]),
    );
  }
}

class _TermCard extends StatefulWidget {
  const _TermCard({required this.term, required this.startOpen});
  final Term term;
  final bool startOpen;
  @override
  State<_TermCard> createState() => _TermCardState();
}

class _TermCardState extends State<_TermCard> {
  late bool open = widget.startOpen;

  Color _gradeColor(ThemeData t, String? g) {
    final p = gradePoints[g];
    if (p == null) return t.colorScheme.onSurfaceVariant;
    if (p >= 3.0) return Status.good(t.brightness);
    if (p >= 2.0) return Status.warn(t.brightness);
    return Status.bad(t.brightness);
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), term = widget.term;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => setState(() => open = !open),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(term.name, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                Text(term.complete ? '${term.courses.length} courses' : 'In progress · ${term.courses.length} courses', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ])),
              if (term.gpa != null) Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(_fmt(term.gpa), style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800, fontFeatures: const [FontFeature.tabularFigures()])),
                Text('GPA', style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ]),
              const SizedBox(width: 8),
              AnimatedRotation(turns: open ? 0.5 : 0, duration: const Duration(milliseconds: 200), child: Icon(LucideIcons.chevronDown, color: t.colorScheme.onSurfaceVariant)),
            ]),
            AnimatedSize(
              duration: const Duration(milliseconds: 220), curve: Curves.easeOutCubic, alignment: Alignment.topCenter,
              child: !open ? const SizedBox(width: double.infinity) : Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Column(children: [
                  for (final (i, c) in term.courses.indexed) ...[
                    if (i > 0) Divider(height: 1, color: t.colorScheme.outlineVariant),
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      child: Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(c.title, style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
                          Text('${c.code} · ${c.credits.round()} credit hours', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
                        ])),
                        const SizedBox(width: 10),
                        c.grade == null
                            ? Text('Pending', style: t.textTheme.labelMedium?.copyWith(color: t.colorScheme.onSurfaceVariant))
                            : Container(
                                width: 44, height: 36, alignment: Alignment.center,
                                decoration: BoxDecoration(color: _gradeColor(t, c.grade).withValues(alpha: 0.14), borderRadius: BorderRadius.circular(12)),
                                child: Text(c.grade!, style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800, color: _gradeColor(t, c.grade))),
                              ),
                      ]),
                    ),
                  ],
                ]),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

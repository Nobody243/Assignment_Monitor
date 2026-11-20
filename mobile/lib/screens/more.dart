import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../data.dart';
import '../logic.dart';
import '../theme.dart';
import 'widgets.dart';

// ------------------------------------------------------------------------------------------------ exams
class ExamsPage extends StatelessWidget {
  const ExamsPage({super.key, required this.summary, required this.now});
  final Summary summary;
  final DateTime now;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness;
    final today = DateTime(now.year, now.month, now.day);
    final dated = summary.exams.where((e) => e.scheduled && e.day != null && !e.day!.isBefore(today)).toList()..sort((x, y) => x.day!.compareTo(y.day!));
    final pending = summary.exams.where((e) => !(e.scheduled && e.day != null)).toList();
    if (dated.isEmpty && pending.isEmpty) return const EmptyState(icon: LucideIcons.graduationCap, title: 'No exams yet', hint: 'They appear here when the portal publishes the date sheet.');
    final next = dated.isEmpty ? null : dated.first;
    final rest = dated.skip(1).toList();
    int days(Exam e) => e.day!.difference(today).inDays;

    Widget chip(IconData i, String label, String value) => Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
            decoration: BoxDecoration(color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(14)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [Icon(i, size: 14, color: t.colorScheme.onPrimaryContainer), const SizedBox(width: 4), Text(label, style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onPrimaryContainer))]),
              const SizedBox(height: 2),
              Text(value, style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer)),
            ]),
          ),
        );

    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
      if (next != null) Reveal(index: 0, child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: t.colorScheme.primaryContainer, borderRadius: BorderRadius.circular(28)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text('NEXT EXAM', style: t.textTheme.labelSmall?.copyWith(letterSpacing: 0.8, fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer)),
            const Spacer(),
            Text(days(next) == 0 ? 'Today' : days(next) == 1 ? 'Tomorrow' : '${days(next)} days', style: t.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer)),
          ]),
          const SizedBox(height: 10),
          Text(next.title, style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700, color: t.colorScheme.onPrimaryContainer)),
          Text('${dayLabel(next.day!)}${next.time == null ? '' : ' · ${next.time}'}', style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.85))),
          const SizedBox(height: 14),
          Row(children: [
            chip(LucideIcons.doorOpen, 'Room', next.room ?? '–'),
            const SizedBox(width: 8),
            chip(LucideIcons.rows3, 'Row', next.row ?? '–'),
            const SizedBox(width: 8),
            chip(LucideIcons.armchair, 'Seat', next.seat ?? '–'),
          ]),
        ]),
      )),
      if (rest.isNotEmpty) ...[
        const SizedBox(height: 20),
        const SectionTitle('Coming up'),
        for (final (i, e) in rest.indexed) Reveal(index: i + 1, child: Padding(padding: const EdgeInsets.only(bottom: 8), child: Card(
          clipBehavior: Clip.antiAlias,
          child: Container(
            padding: const EdgeInsets.all(14),
            child: Row(children: [
              Container(
                width: 52, height: 52, alignment: Alignment.center,
                decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(14)),
                child: Column(mainAxisSize: MainAxisSize.min, children: [Text('${e.day!.day}', style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)), Text(months[e.day!.month - 1], style: t.textTheme.labelSmall)]),
              ),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(e.title, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text([if (e.time != null) e.time!, if (e.room != null) 'Room ${e.room}', if (e.row != null && e.seat != null) 'row ${e.row}, seat ${e.seat}'].join(' · '), style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ])),
              Pill('${days(e)}d', color: days(e) <= 3 ? Status.bad(b) : null),
            ]),
          ),
        ))),
      ],
      if (pending.isNotEmpty) ...[
        const SizedBox(height: 20),
        SectionTitle('Not scheduled yet', trailing: '${pending.length}'),
        Card(child: Column(children: [
          for (final e in pending) ListTile(
            leading: Icon(LucideIcons.hourglass, color: t.colorScheme.onSurfaceVariant),
            title: Text(e.title, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: const Text('Date, room and seat are not posted yet.'),
          ),
        ])),
      ],
    ]);
  }
}

// ------------------------------------------------------------------------------------------------ results + calculator
class ResultsPage extends StatefulWidget {
  const ResultsPage({super.key, required this.summary});
  final Summary summary;
  @override
  State<ResultsPage> createState() => _ResultsState();
}

class _ResultsState extends State<ResultsPage> {
  final rows = [for (var i = 0; i < 5; i++) GradedCourse()];
  final prevCgpa = TextEditingController(), prevCredits = TextEditingController(), target = TextEditingController();

  @override
  void initState() {
    super.initState();
    for (final c in [prevCgpa, prevCredits, target]) { c.addListener(() => setState(() {})); }
  }

  @override
  void dispose() { prevCgpa.dispose(); prevCredits.dispose(); target.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final pg = double.tryParse(prevCgpa.text), pc = double.tryParse(prevCredits.text) ?? 0, tg = double.tryParse(target.text);
    final gpa = gpaOf(rows), cgpa = cgpaAfter(rows, pg, pc);
    final all = rows.fold<double>(0, (n, r) => n + (r.credits > 0 ? r.credits : 0));
    final goal = tg == null ? null : neededGpa(tg, pg, pc, all);
    String fmt(double? v) => v == null ? '–' : v.toStringAsFixed(2);
    String lowest(double need) {
      String? found;
      for (final g in gradePoints.entries) { if (g.value + 1e-9 >= need) found = g.key; }
      return found ?? '';
    }
    return ListView(padding: const EdgeInsets.all(16), children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: t.colorScheme.primaryContainer, borderRadius: BorderRadius.circular(28)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('CUMULATIVE GPA', style: t.textTheme.labelSmall?.copyWith(letterSpacing: 0.8, fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer)),
          Text(fmt(widget.summary.cgpa), style: t.textTheme.displayMedium?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer)),
          const SizedBox(height: 10),
          for (final s in widget.summary.terms.where((s) => s.complete && s.gpa != null))
            Padding(padding: const EdgeInsets.only(bottom: 8), child: Row(children: [
              SizedBox(width: 92, child: Text(s.name, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onPrimaryContainer))),
              Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: (s.gpa! / 4).clamp(0, 1).toDouble(), minHeight: 8, backgroundColor: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.15), color: t.colorScheme.onPrimaryContainer))),
              const SizedBox(width: 10),
              Text(fmt(s.gpa), style: t.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer)),
            ])),
        ]),
      ),
      const SizedBox(height: 16),
      Text('Calculator', style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 4),
      Muted('Pick credit hours and the grade you expect. Nothing is saved or sent.'),
      Card(color: t.colorScheme.primaryContainer, child: Padding(padding: const EdgeInsets.all(16), child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
        _Fig('Semester GPA', fmt(gpa)),
        _Fig(pg != null && pc > 0 ? 'New CGPA' : 'CGPA', fmt(cgpa)),
        _Fig('Credits', all.round().toString()),
      ]))),
      const SizedBox(height: 12),
      for (var i = 0; i < rows.length; i++)
        Padding(padding: const EdgeInsets.only(bottom: 8), child: Row(children: [
          SizedBox(width: 72, child: Text('Course ${i + 1}', style: t.textTheme.bodyMedium)),
          const SizedBox(width: 4),
          DropdownButton<double>(value: rows[i].credits, items: [for (final c in [0, 1, 2, 3, 4]) DropdownMenuItem(value: c.toDouble(), child: Text('$c cr'))], onChanged: (v) => setState(() => rows[i].credits = v ?? 3)),
          const SizedBox(width: 12),
          Expanded(child: DropdownButton<String>(isExpanded: true, value: rows[i].grade.isEmpty ? null : rows[i].grade, hint: const Text('Grade'), items: [for (final g in gradePoints.keys) DropdownMenuItem(value: g, child: Text('$g (${gradePoints[g]!.toStringAsFixed(2)})'))], onChanged: (v) => setState(() => rows[i].grade = v ?? ''))),
        ])),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(child: TextField(controller: prevCgpa, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'CGPA so far', border: OutlineInputBorder()))),
        const SizedBox(width: 10),
        Expanded(child: TextField(controller: prevCredits, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Credits so far', border: OutlineInputBorder()))),
      ]),
      const SizedBox(height: 10),
      TextField(controller: target, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Target CGPA (optional)', border: OutlineInputBorder())),
      if (goal != null) Padding(padding: const EdgeInsets.only(top: 12), child: Card(child: Padding(padding: const EdgeInsets.all(14), child: Text(
        goal.reachable ? (goal.needed <= 0 ? 'You are already above that target, whatever the grades.' : 'To finish on ${tg!.toStringAsFixed(2)} you need a semester GPA of ${fmt(goal.needed)}${lowest(goal.needed).isEmpty ? '' : ': ${lowest(goal.needed)} or better in every course, or a mix that averages it'}.')
            : '${tg!.toStringAsFixed(2)} is not reachable this semester: it needs ${fmt(goal.needed)} and the maximum is 4.00. Straight As would reach ${fmt(goal.best)}.',
      )))),
    ]);
  }
}

class _Fig extends StatelessWidget {
  const _Fig(this.label, this.value);
  final String label, value;
  @override
  Widget build(BuildContext context) => Column(children: [Text(value, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)), Text(label, style: Theme.of(context).textTheme.labelSmall)]);
}

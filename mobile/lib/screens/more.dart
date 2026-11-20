import 'package:flutter/material.dart';

import '../data.dart';
import '../logic.dart';
import '../model.dart';
import '../reminders.dart';
import '../source.dart' show repoName;
import '../theme.dart';
import 'widgets.dart';

/// Opens a secondary page (Timetable, Results, Settings) over the main screens.
void openPage(BuildContext context, String title, Widget body) =>
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => Scaffold(appBar: AppBar(title: Text(title)), body: SafeArea(child: body))));

// ------------------------------------------------------------------------------------------------ exams
class ExamsPage extends StatelessWidget {
  const ExamsPage({super.key, required this.summary, required this.now});
  final Summary summary;
  final DateTime now;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness;
    final today = DateTime(now.year, now.month, now.day);
    return ListView(padding: const EdgeInsets.all(16), children: [
      for (final e in summary.exams)
        Padding(padding: const EdgeInsets.only(bottom: 10), child: Card(child: Padding(padding: const EdgeInsets.all(16), child: Row(children: [
          Container(
            width: 56, height: 56, alignment: Alignment.center,
            decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(14)),
            child: e.day == null ? const Text('TBA') : Column(mainAxisSize: MainAxisSize.min, children: [Text('${e.day!.day}', style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)), Text(months[e.day!.month - 1], style: t.textTheme.labelSmall)]),
          ),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(e.title, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            if (e.scheduled) Text([if (e.time != null) e.time!, if (e.room != null) 'Room ${e.room}', if (e.row != null && e.seat != null) 'row ${e.row}, seat ${e.seat}'].join(' · '), style: t.textTheme.bodyMedium)
            else Text('Date, room and seat not posted yet.', style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
          ])),
          if (e.day != null) Pill('in ${e.day!.difference(today).inDays}d', color: e.day!.difference(today).inDays <= 3 ? Status.bad(b) : null),
        ])))),
    ]);
  }
}

// ------------------------------------------------------------------------------------------------ timetable
class TimetablePage extends StatelessWidget {
  const TimetablePage({super.key, required this.summary, required this.now});
  final Summary summary;
  final DateTime now;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final today = weekdays[now.weekday - 1];
    final days = weekdays.where((d) => summary.timetable.any((s) => s.day == d) || weekdays.indexOf(d) < 5).toList();
    return ListView(padding: const EdgeInsets.all(16), children: [
      for (final d in days) ...[
        Padding(padding: const EdgeInsets.only(top: 8, bottom: 6), child: Row(children: [
          Text(d, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700, color: d == today ? t.colorScheme.primary : null)),
          if (d == today) Padding(padding: const EdgeInsets.only(left: 8), child: Pill('today', color: t.colorScheme.primary)),
        ])),
        if (!summary.timetable.any((s) => s.day == d)) const Muted('Free'),
        for (final s in (summary.timetable.where((s) => s.day == d).toList()..sort((a, b) => a.start.compareTo(b.start))))
          Padding(padding: const EdgeInsets.only(bottom: 8), child: Card(child: ListTile(
            leading: SizedBox(width: 78, child: Text('${s.start}\n${s.end}', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600))),
            title: Text(s.course, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: s.teacher == null ? null : Text(s.teacher!),
          ))),
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
      Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Your transcript', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text('CGPA'), Text(fmt(widget.summary.cgpa), style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800))]),
        for (final s in widget.summary.terms.where((s) => s.complete)) Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(s.name), Text('GPA ${fmt(s.gpa)}')]),
      ]))),
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
          Text('Course ${i + 1}', style: t.textTheme.bodyMedium),
          const Spacer(),
          DropdownButton<double>(value: rows[i].credits, items: [for (final c in [0, 1, 2, 3, 4]) DropdownMenuItem(value: c.toDouble(), child: Text('$c cr'))], onChanged: (v) => setState(() => rows[i].credits = v ?? 3)),
          const SizedBox(width: 12),
          DropdownButton<String>(value: rows[i].grade.isEmpty ? null : rows[i].grade, hint: const Text('Grade'), items: [for (final g in gradePoints.keys) DropdownMenuItem(value: g, child: Text('$g (${gradePoints[g]!.toStringAsFixed(2)})'))], onChanged: (v) => setState(() => rows[i].grade = v ?? '')),
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

// ------------------------------------------------------------------------------------------------ settings
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key, required this.summary, required this.prefs, required this.model});
  final Summary summary;
  final Prefs prefs;
  final AppModel model;
  @override
  State<SettingsPage> createState() => _SettingsState();
}

class _SettingsState extends State<SettingsPage> {
  bool weekly = true, digest = false;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), p = widget.prefs;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text('Reminders', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, children: [
        for (final h in [48, 24, 12, 6, 3, 1])
          FilterChip(label: Text(h == 48 ? '2 days' : h == 24 ? '1 day' : '$h h'), selected: p.leads.contains(h), onSelected: (on) => p.update(() { on ? p.leads.add(h) : p.leads.remove(h); p.leads.sort((a, b) => b - a); })),
      ]),
      SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Sunday summary'), subtitle: const Text('What is due next week, exams and attendance to watch'), value: weekly, onChanged: (v) => setState(() => weekly = v)),
      SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Daily digest'), subtitle: const Text('One morning message instead of many'), value: digest, onChanged: (v) => setState(() => digest = v)),
      const Muted('Reminders are scheduled on this phone from the summary, so they work without a network. Quiet hours: 23:00 to 07:00.'),
      const Divider(height: 32),
      Text('Look', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, children: [for (final pal in palettes) ChoiceChip(label: Text(pal.label), selected: p.palette.key == pal.key, onSelected: (_) => p.update(() => p.palette = pal))]),
      const SizedBox(height: 12),
      SegmentedButton<ThemeMode>(
        segments: const [ButtonSegment(value: ThemeMode.system, label: Text('System')), ButtonSegment(value: ThemeMode.light, label: Text('Light')), ButtonSegment(value: ThemeMode.dark, label: Text('Dark'))],
        selected: {p.mode},
        onSelectionChanged: (s) => p.update(() => p.mode = s.first),
      ),
      const Divider(height: 32),
      Text('Account', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.person_outline), title: Text(widget.summary.studentName),
          subtitle: Text(widget.model.demo ? 'Demo data, nothing is read from GitHub' : 'GitHub: ${widget.model.login ?? '–'} · ${widget.model.login ?? ''}/$repoName')),
      if (!widget.model.demo) ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.sync), title: const Text('Last read from GitHub'),
          subtitle: Text(widget.model.fetchedAt == null ? 'Not yet' : '${agoLabel(widget.model.age!)} · summary made ${agoLabel(DateTime.now().difference(widget.summary.generatedAt))}')),
      if (!widget.model.demo && Reminders.supported) ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.notifications_active_outlined), title: const Text('Reminders on this phone'),
          subtitle: Text('${widget.model.scheduled} scheduled'), trailing: TextButton(onPressed: () async { await Reminders.allowed(); await widget.model.replan(); setState(() {}); }, child: const Text('Allow'))),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.lock_outline), title: Text('No portal password on this phone'), subtitle: Text('Only a GitHub sign-in for your own repository, kept in the phone\'s keystore')),
      const SizedBox(height: 8),
      OutlinedButton.icon(onPressed: () async { Navigator.of(context).popUntil((r) => r.isFirst); await widget.model.signOut(); }, icon: const Icon(Icons.logout), label: Text(widget.model.demo ? 'Leave the demo' : 'Sign out and forget this phone')),
    ]);
  }
}

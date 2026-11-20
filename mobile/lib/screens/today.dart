import 'package:flutter/material.dart';

import '../data.dart';
import '../model.dart';
import '../theme.dart';
import 'widgets.dart';

class TodayScreen extends StatelessWidget {
  const TodayScreen({super.key, required this.summary, required this.now, required this.prefs, required this.onOpenWork, required this.onOpenAttendance});
  final Summary summary;
  final DateTime now;
  final Prefs prefs;
  final VoidCallback onOpenWork, onOpenAttendance;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness;
    final work = summary.work;
    final open = work.where((w) => w.todo && w.open && w.due != null && !prefs.done.contains(w.id)).toList()..sort((a, c) => a.due!.compareTo(c.due!));
    final next = open.isEmpty ? null : open.first;
    final overdue = work.where((w) => w.overdue).length;
    final low = summary.attendance.where((c) => c.recorded && !c.ok).toList();
    final rec = summary.attendance.where((c) => c.recorded).toList();
    final presentSum = rec.fold<double>(0, (n, c) => n + c.present), totalSum = rec.fold<double>(0, (n, c) => n + c.present + c.absent);
    final double? overall = totalSum == 0 ? null : 100 * presentSum / totalSum;
    final today = weekdays[now.weekday - 1];
    final classes = summary.timetable.where((c) => c.day == today).toList()..sort((a, c) => a.start.compareTo(c.start));
    final hour = now.hour;
    final hello = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
    final checked = summary.lastCheck == null ? 'not checked yet' : 'checked ${agoText(now.difference(summary.lastCheck!))}';

    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 24), children: [
      Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('$hello, ${summary.firstName}', style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700, fontSize: 21)),
          const SizedBox(height: 2),
          Text('${dayLabel(now)} · ${summary.semester} · $checked', style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        ])),
      ]),
      const SizedBox(height: 16),
      Reveal(index: 0, child: next != null ? _Hero(work: next, now: now, prefs: prefs, onOpen: onOpenWork) : const _AllClear()),
      const SizedBox(height: 16),
      Reveal(index: 1, child: _WeekStrip(summary: summary, now: now, prefs: prefs)),
      const SizedBox(height: 12),
      Reveal(index: 2, child: Row(children: [
        Expanded(child: _Stat(value: '${open.length}', label: 'to do', color: null, onTap: onOpenWork)),
        const SizedBox(width: 10),
        Expanded(child: _Stat(value: '$overdue', label: 'overdue', color: overdue > 0 ? Status.bad(b) : null, onTap: onOpenWork)),
        const SizedBox(width: 10),
        Expanded(child: _Stat(value: overall == null ? '–' : '${overall.toStringAsFixed(0)}%', label: 'attendance', color: overall != null && overall < summary.minimum ? Status.bad(b) : null, onTap: onOpenAttendance)),
      ])),
      const SizedBox(height: 20),
      SectionTitle('Today\'s classes', trailing: classes.isEmpty ? null : '${classes.length}'),
      if (classes.isEmpty)
        const Muted('No classes today.')
      else
        Column(children: [for (final (i, c) in classes.indexed) Reveal(index: i + 3, child: _ClassTile(slot: c, now: now))]),
      const SizedBox(height: 20),
      const SectionTitle('Needs attention'),
      if (overdue == 0 && low.isEmpty && next == null)
        const Muted('Nothing needs you right now.')
      else
        Card(child: Column(children: [
          if (overdue > 0) AttentionRow(icon: Icons.error_outline, color: Status.bad(b), title: '$overdue overdue assignment${overdue > 1 ? 's' : ''}', detail: 'Not submitted. Review them.', onTap: onOpenWork),
          for (final c in low) AttentionRow(icon: Icons.event_busy_outlined, color: Status.bad(b), title: '${c.title}: ${c.percent.toStringAsFixed(0)}% attendance', detail: 'Below the ${summary.minimum}% minimum. Attend the next ${c.need.ceil()} hours.', onTap: onOpenAttendance),
        ])),
      const SizedBox(height: 20),
      const SectionTitle('Latest announcements'),
      Card(child: Column(children: [for (final n in summary.announcements.take(3)) ListTile(dense: true, title: Text(n.title, maxLines: 1, overflow: TextOverflow.ellipsis), subtitle: Text(n.course, maxLines: 1, overflow: TextOverflow.ellipsis))])),
    ]);
  }
}

class _Hero extends StatefulWidget {
  const _Hero({required this.work, required this.now, required this.prefs, required this.onOpen});
  final Work work;
  final DateTime now;
  final Prefs prefs;
  final VoidCallback onOpen;
  @override
  State<_Hero> createState() => _HeroState();
}

class _HeroState extends State<_Hero> {
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), w = widget.work, due = w.due!;
    final left = due.difference(widget.now);
    final urgent = left.inHours < 24;
    final bg = urgent ? t.colorScheme.primaryContainer : t.colorScheme.surfaceContainerHigh;
    final fg = urgent ? t.colorScheme.onPrimaryContainer : t.colorScheme.onSurface;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(28)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4), decoration: BoxDecoration(color: fg.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(99)), child: Text(urgent ? 'DUE SOON' : 'NEXT UP', style: t.textTheme.labelSmall?.copyWith(color: fg, fontWeight: FontWeight.w700, letterSpacing: 0.6))),
          const Spacer(),
          Text(countdown(due, widget.now), style: t.textTheme.headlineMedium?.copyWith(color: fg, fontWeight: FontWeight.w800, fontFeatures: const [FontFeature.tabularFigures()])),
        ]),
        const SizedBox(height: 14),
        Text(w.title, style: t.textTheme.titleLarge?.copyWith(color: fg, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Row(children: [
          Container(width: 10, height: 10, decoration: BoxDecoration(color: courseColor(w.course), shape: BoxShape.circle, border: Border.all(color: fg.withValues(alpha: 0.5)))),
          const SizedBox(width: 8),
          Expanded(child: Text('${w.course} · ${dayLabel(due)}, ${timeLabel(due)}', style: t.textTheme.bodyMedium?.copyWith(color: fg.withValues(alpha: 0.8)))),
        ]),
        if (w.extended && w.wasDue != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text('Extended from ${w.wasDue}', style: t.textTheme.bodySmall?.copyWith(color: fg.withValues(alpha: 0.8)))),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(child: FilledButton.tonal(onPressed: () {
            widget.prefs.update(() => widget.prefs.snoozed[w.id] = widget.now.add(const Duration(hours: 1)));
            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Snoozed for 1 hour. You will be reminded again.')));
          }, child: const Text('Snooze 1 h'))),
          const SizedBox(width: 10),
          Expanded(child: FilledButton(onPressed: () {
            widget.prefs.update(() => widget.prefs.done.add(w.id));
            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Okay: no more reminders for this one. The next check confirms it with the portal.')));
          }, child: const Text('Done'))),
        ]),
        TextButton(onPressed: widget.onOpen, child: const Text('See all work')),
      ]),
    );
  }
}

class _AllClear extends StatelessWidget {
  const _AllClear();
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Container(padding: const EdgeInsets.all(24), decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(28)),
      child: Row(children: [Icon(Icons.done_all, size: 32, color: Status.good(t.brightness)), const SizedBox(width: 14), Expanded(child: Text('You are all caught up. Nothing is waiting for a submission.', style: t.textTheme.titleMedium))]));
  }
}

class _ClassTile extends StatelessWidget {
  const _ClassTile({required this.slot, required this.now});
  final ClassSlot slot;
  final DateTime now;
  bool get live {
    int mins(String s) { final p = s.split(':'); return int.parse(p[0]) * 60 + int.parse(p[1]); }
    final n = now.hour * 60 + now.minute;
    return n >= mins(slot.start) && n < mins(slot.end);
  }
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: live ? t.colorScheme.primaryContainer : t.colorScheme.surfaceContainerLow, borderRadius: BorderRadius.circular(16), border: Border(left: BorderSide(color: courseColor(slot.course), width: 5))),
      child: Row(children: [
        SizedBox(width: 92, child: Text('${slot.start}–${slot.end}', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600, fontFeatures: const [FontFeature.tabularFigures()]))),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(slot.course, style: t.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
          if (slot.teacher != null) Text(slot.teacher!, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        ])),
        if (live) Pill('now', color: Status.good(t.brightness)),
      ]),
    );
  }
}

String agoText(Duration d) {
  if (d.inMinutes < 1) return 'just now';
  if (d.inMinutes < 60) return '${d.inMinutes} min ago';
  if (d.inHours < 24) return '${d.inHours} h ago';
  return '${d.inDays} d ago';
}


/// The next seven days at a glance: a dot per deadline, one for an exam.
class _WeekStrip extends StatelessWidget {
  const _WeekStrip({required this.summary, required this.now, required this.prefs});
  final Summary summary;
  final DateTime now;
  final Prefs prefs;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness;
    final start = DateTime(now.year, now.month, now.day);
    bool same(DateTime? a, DateTime d) => a != null && a.year == d.year && a.month == d.month && a.day == d.day;
    final work = summary.work.where((w) => w.todo && w.open && !prefs.done.contains(w.id)).toList();
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
      decoration: BoxDecoration(color: t.colorScheme.surfaceContainerLow, borderRadius: BorderRadius.circular(20)),
      child: Row(children: [
        for (var i = 0; i < 7; i++) Builder(builder: (_) {
          final d = start.add(Duration(days: i));
          final due = work.where((w) => same(w.due, d)).length;
          final exam = summary.exams.any((e) => same(e.day, d));
          final isToday = i == 0;
          return Expanded(child: Column(children: [
            Text(weekdays[d.weekday - 1].substring(0, 1), style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant, fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Container(
              width: 34, height: 34, alignment: Alignment.center,
              decoration: BoxDecoration(color: isToday ? t.colorScheme.primary : null, shape: BoxShape.circle),
              child: Text('${d.day}', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700, color: isToday ? t.colorScheme.onPrimary : null)),
            ),
            const SizedBox(height: 5),
            SizedBox(height: 8, child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              for (var k = 0; k < due.clamp(0, 3); k++) Container(width: 6, height: 6, margin: const EdgeInsets.symmetric(horizontal: 1.5), decoration: BoxDecoration(color: Status.warn(b), shape: BoxShape.circle)),
              if (exam) Container(width: 6, height: 6, margin: const EdgeInsets.symmetric(horizontal: 1.5), decoration: BoxDecoration(color: Status.bad(b), borderRadius: BorderRadius.circular(1.5))),
            ])),
          ]));
        }),
      ]),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.value, required this.label, required this.color, required this.onTap});
  final String value, label;
  final Color? color;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Material(
      color: t.colorScheme.surfaceContainerLow, borderRadius: BorderRadius.circular(20),
      child: InkWell(
        borderRadius: BorderRadius.circular(20), onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Column(children: [
            Text(value, style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800, color: color, fontFeatures: const [FontFeature.tabularFigures()])),
            Text(label, style: t.textTheme.labelMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
          ]),
        ),
      ),
    );
  }
}

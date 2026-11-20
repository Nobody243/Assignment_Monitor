import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../data.dart';
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
              Row(children: [Icon(i, size: 14, color: t.colorScheme.onPrimaryContainer), const SizedBox(width: 4), Flexible(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onPrimaryContainer)))]),
              const SizedBox(height: 2),
              FittedBox(fit: BoxFit.scaleDown, alignment: Alignment.centerLeft, child: Text(value, style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer))),
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
            const SizedBox(width: 8),
            Expanded(child: Align(alignment: Alignment.centerRight, child: FittedBox(fit: BoxFit.scaleDown, child: Text(days(next) == 0 ? 'Today' : days(next) == 1 ? 'Tomorrow' : '${days(next)} days', style: t.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer))))),
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
                constraints: const BoxConstraints(minWidth: 52, minHeight: 52), padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4), alignment: Alignment.center,
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

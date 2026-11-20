import 'package:flutter/material.dart';

import '../data.dart';
import '../logic.dart';
import '../theme.dart';

class AttendanceScreen extends StatelessWidget {
  const AttendanceScreen({super.key, required this.summary});
  final Summary summary;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final courses = [...summary.attendance]..sort((a, b) => (a.ok == b.ok ? a.percent.compareTo(b.percent) : (a.ok ? 1 : -1)));
    final rec = courses.where((c) => c.recorded).toList();
    final present = rec.fold<double>(0, (n, c) => n + c.present), total = rec.fold<double>(0, (n, c) => n + c.present + c.absent);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 24), children: [
      Text('Attendance', style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 4),
      Text('Against your ${summary.minimum}% minimum. Overall ${total == 0 ? '–' : '${(100 * present / total).toStringAsFixed(1)}%'}.', style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      const SizedBox(height: 14),
      for (final c in courses) Padding(padding: const EdgeInsets.only(bottom: 12), child: _CourseCard(course: c, minimum: summary.minimum)),
    ]);
  }
}

class _CourseCard extends StatefulWidget {
  const _CourseCard({required this.course, required this.minimum});
  final Course course;
  final int minimum;
  @override
  State<_CourseCard> createState() => _CourseCardState();
}

class _CourseCardState extends State<_CourseCard> {
  bool open = false;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness, c = widget.course;
    final risk = c.recorded && c.ok && c.canMiss <= 2;
    final color = !c.recorded ? t.colorScheme.onSurfaceVariant : !c.ok ? Status.bad(b) : risk ? Status.warn(b) : Status.good(b);
    final allow = semesterAllowance(c.credit, widget.minimum, c.absent, c.classHours);
    final sentence = !c.recorded ? 'No classes recorded yet.' : !c.ok ? 'Below the ${widget.minimum}% minimum. Attend the next ${c.need.ceil()} hours to get back.' : risk ? 'Close to the limit: you can miss only ${hoursText(c.canMiss)} more.' : 'Safe: you can miss ${hoursText(c.canMiss)} more and stay above ${widget.minimum}%.';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Semantics(
              label: '${c.percent.toStringAsFixed(0)} percent attendance',
              child: SizedBox(width: 64, height: 64, child: Stack(alignment: Alignment.center, children: [
                SizedBox.expand(child: CircularProgressIndicator(value: (c.percent / 100).clamp(0, 1), strokeWidth: 7, color: color, backgroundColor: color.withValues(alpha: 0.15))),
                Text('${c.percent.toStringAsFixed(0)}%', style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
              ])),
            ),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(c.title, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
              Text([if (c.teacher != null) c.teacher!, if (c.credit > 0) '${c.credit.round()} credit hours'].join(' · '), style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              const SizedBox(height: 6),
              Text(sentence, style: t.textTheme.bodyMedium?.copyWith(color: color, fontWeight: FontWeight.w500)),
            ])),
          ]),
          if (c.recorded) Padding(padding: const EdgeInsets.only(top: 12), child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('Present ${hoursText(c.present)}', style: t.textTheme.bodySmall),
            Text('Absent ${hoursText(c.absent)}', style: t.textTheme.bodySmall),
            Text('Total ${hoursText(c.present + c.absent)}', style: t.textTheme.bodySmall),
          ])),
          if (allow != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(14)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  Expanded(child: Text('Whole semester: you can miss ${hoursText(allow.max)} in total', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600))),
                ]),
                const SizedBox(height: 4),
                Text('${hoursText(allow.used)} used · ${hoursText(allow.left)} left', style: t.textTheme.bodySmall?.copyWith(color: allow.left == 0 ? Status.bad(b) : t.colorScheme.onSurfaceVariant)),
                const SizedBox(height: 8),
                ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(minHeight: 6, value: (allow.used / allow.max).clamp(0, 1), color: allow.left == 0 ? Status.bad(b) : allow.left <= allow.classLen ? Status.warn(b) : Status.good(b), backgroundColor: t.colorScheme.surfaceContainerHighest)),
                const SizedBox(height: 8),
                Text('Planned ${hoursText(allow.planned)} over 16 weeks, about ${allow.classes} classes of ${hoursText(allow.classLen)}. If fewer classes are held, the limit is ${100 - widget.minimum}% of the hours actually held.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ]),
            ),
          ],
          const SizedBox(height: 4),
          Align(alignment: Alignment.centerLeft, child: TextButton(onPressed: () => setState(() => open = !open), child: Text(open ? 'Hide classes' : 'Class by class'))),
          if (open) ...[
            for (final s in (c.m['classes'] as List).cast<Map>().reversed)
              ListTile(dense: true, contentPadding: EdgeInsets.zero, leading: Icon(((s['absent'] as num?) ?? 0) > 0 ? Icons.cancel_outlined : Icons.check_circle_outline, color: ((s['absent'] as num?) ?? 0) > 0 ? Status.bad(b) : Status.good(b)), title: Text('${s['date']}'), trailing: Text(hoursText(((s['hours'] as num?) ?? 0).toDouble()))),
          ],
        ]),
      ),
    );
  }
}

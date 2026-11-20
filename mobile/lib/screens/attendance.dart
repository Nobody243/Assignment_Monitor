import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../data.dart';
import '../logic.dart';
import '../theme.dart';
import 'widgets.dart';

class AttendanceScreen extends StatelessWidget {
  const AttendanceScreen({super.key, required this.summary});
  final Summary summary;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness;
    final courses = [...summary.attendance]..sort((a, b) => (a.ok == b.ok ? a.percent.compareTo(b.percent) : (a.ok ? 1 : -1)));
    final rec = courses.where((c) => c.recorded).toList();
    final present = rec.fold<double>(0, (n, c) => n + c.present), total = rec.fold<double>(0, (n, c) => n + c.present + c.absent);
    final overall = total == 0 ? null : 100 * present / total;
    final below = rec.where((c) => !c.ok).length;
    final close = rec.where((c) => c.ok && c.canMiss <= 2).length;
    final color = overall == null ? t.colorScheme.onSurfaceVariant : overall < summary.minimum ? Status.bad(b) : close > 0 ? Status.warn(b) : Status.good(b);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
      Reveal(index: 0, child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: t.colorScheme.surfaceContainerLow, borderRadius: BorderRadius.circular(28)),
        child: Row(children: [
          Semantics(
            label: overall == null ? 'No attendance recorded' : '${overall.toStringAsFixed(0)} percent overall attendance',
            child: SizedBox(width: 112, height: 112, child: Stack(alignment: Alignment.center, children: [
              SizedBox.expand(child: CircularProgressIndicator(value: overall == null ? 0 : (overall / 100).clamp(0, 1), strokeWidth: 11, strokeCap: StrokeCap.round, color: color, backgroundColor: color.withValues(alpha: 0.15))),
              Column(mainAxisSize: MainAxisSize.min, children: [
                Text(overall == null ? '–' : '${overall.toStringAsFixed(0)}%', style: t.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
                Text('overall', style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              ]),
            ])),
          ),
          const SizedBox(width: 20),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Minimum ${summary.minimum}%', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            _Legend(color: Status.good(b), text: '${rec.length - below - close} safe'),
            _Legend(color: Status.warn(b), text: '$close close to the limit'),
            _Legend(color: Status.bad(b), text: '$below below the minimum'),
          ])),
        ]),
      )),
      const SizedBox(height: 16),
      for (final (i, c) in courses.indexed) Reveal(index: i + 1, child: Padding(padding: const EdgeInsets.only(bottom: 10), child: _CourseCard(course: c, minimum: summary.minimum))),
    ]);
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.color, required this.text});
  final Color color;
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Row(children: [
          Container(width: 10, height: 10, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Flexible(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
        ]),
      );
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
    final sentence = !c.recorded ? 'No classes recorded yet' : !c.ok ? 'Attend the next ${c.need.ceil()} h to get back' : risk ? 'Close: you can miss only ${hoursText(c.canMiss)} more' : 'You can miss ${hoursText(c.canMiss)} more';
    final classes = c.classes.reversed.toList();
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => setState(() => open = !open),
        child: Container(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Semantics(
                label: '${c.percent.toStringAsFixed(0)} percent attendance',
                child: SizedBox(width: 56, height: 56, child: Stack(alignment: Alignment.center, children: [
                  SizedBox.expand(child: CircularProgressIndicator(value: (c.percent / 100).clamp(0, 1), strokeWidth: 6, strokeCap: StrokeCap.round, color: color, backgroundColor: color.withValues(alpha: 0.15))),
                  Text('${c.percent.toStringAsFixed(0)}%', style: t.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800)),
                ])),
              ),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(c.title, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(sentence, style: t.textTheme.bodyMedium?.copyWith(color: color, fontWeight: FontWeight.w600)),
              ])),
              AnimatedRotation(turns: open ? 0.5 : 0, duration: const Duration(milliseconds: 200), child: Icon(LucideIcons.chevronDown, color: t.colorScheme.onSurfaceVariant)),
            ]),
            AnimatedSize(
              duration: const Duration(milliseconds: 220), curve: Curves.easeOutCubic, alignment: Alignment.topCenter,
              child: !open ? const SizedBox(width: double.infinity) : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const SizedBox(height: 14),
                Text([if (c.teacher != null) c.teacher!, if (c.credit > 0) '${c.credit.round()} credit hours'].join(' · '), style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
                if (c.recorded) ...[
                  const SizedBox(height: 12),
                  Row(children: [
                    Expanded(child: _Num('Present', hoursText(c.present))),
                    const SizedBox(width: 8),
                    Expanded(child: _Num('Absent', hoursText(c.absent))),
                    const SizedBox(width: 8),
                    Expanded(child: _Num('Total', hoursText(c.present + c.absent))),
                  ]),
                ],
                if (allow != null) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(16)),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('Whole semester: you can miss ${hoursText(allow.max)} in total', style: t.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
                      const SizedBox(height: 4),
                      Text('${hoursText(allow.used)} used · ${hoursText(allow.left)} left', style: t.textTheme.bodySmall?.copyWith(color: allow.left == 0 ? Status.bad(b) : t.colorScheme.onSurfaceVariant)),
                      const SizedBox(height: 8),
                      ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(minHeight: 6, value: (allow.used / allow.max).clamp(0, 1), color: allow.left == 0 ? Status.bad(b) : allow.left <= allow.classLen ? Status.warn(b) : Status.good(b), backgroundColor: t.colorScheme.surfaceContainerHighest)),
                      const SizedBox(height: 8),
                      Text('Planned ${hoursText(allow.planned)} over 16 weeks, about ${allow.classes} classes of ${hoursText(allow.classLen)}. If fewer classes are held, the limit is ${100 - widget.minimum}% of the hours actually held.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
                    ]),
                  ),
                ],
                if (classes.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text('Class by class', style: t.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    for (final s in classes)
                      Builder(builder: (_) {
                        final gone = ((s['absent'] as num?) ?? 0) > 0;
                        final col = gone ? Status.bad(b) : Status.good(b);
                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                          child: Row(mainAxisSize: MainAxisSize.min, children: [
                            Icon(gone ? LucideIcons.x : LucideIcons.check, size: 14, color: col),
                            const SizedBox(width: 4),
                            Text('${s['date']}', style: t.textTheme.labelMedium?.copyWith(color: col, fontWeight: FontWeight.w600)),
                          ]),
                        );
                      }),
                  ]),
                ],
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

class _Num extends StatelessWidget {
  const _Num(this.label, this.value);
  final String label, value;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(14)),
      child: Column(children: [
        Text(value, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
        Text(label, style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      ]),
    );
  }
}

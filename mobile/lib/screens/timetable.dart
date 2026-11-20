import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:share_plus/share_plus.dart';

import '../data.dart';
import '../theme.dart';
import '../timetable_export.dart';
import 'widgets.dart';

enum _View { day, week }

/// The timetable as its own screen: a day view (a timeline with the gaps between classes) and a week grid, and a
/// button that saves or shares the week as PNG, JPG or PDF.
class TimetableScreen extends StatefulWidget {
  const TimetableScreen({super.key, required this.summary, required this.now});
  final Summary summary;
  final DateTime now;
  @override
  State<TimetableScreen> createState() => _TimetableScreenState();
}

class _TimetableScreenState extends State<TimetableScreen> {
  late int day = widget.now.weekday - 1;
  _View view = _View.day;
  bool saving = false;

  static int mins(String s) { final p = s.split(':'); return int.parse(p[0]) * 60 + int.parse(p[1]); }
  static String span(int m) => m >= 60 ? '${m ~/ 60} h${m % 60 == 0 ? '' : ' ${m % 60} min'}' : '$m min';

  Future<void> _export(String format) async {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final s = widget.summary;
    setState(() => saving = true);
    try {
      final name = 'Timetable ${s.semester.isEmpty ? '' : '${s.semester} '}'.trim();
      final bytes = switch (format) {
        'png' => await TimetableExport.png(s, dark: dark),
        'jpg' => await TimetableExport.jpg(s, dark: dark),
        _ => await TimetableExport.pdfFile(s, dark: dark),
      };
      final mime = switch (format) { 'png' => 'image/png', 'jpg' => 'image/jpeg', _ => 'application/pdf' };
      await SharePlus.instance.share(ShareParams(
        files: [XFile.fromData(bytes, mimeType: mime, name: '$name.$format')],
        fileNameOverrides: ['$name.$format'],
        subject: name,
      ));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not make the $format file. $e')));
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final tt = widget.summary.timetable;
    if (tt.isEmpty) return const EmptyState(icon: LucideIcons.calendarRange, title: 'No timetable yet', hint: 'It appears here once the portal has published your classes.');
    final todayIdx = widget.now.weekday - 1;
    final used = {for (final s in tt) s.day};
    final dayIdx = [for (var i = 0; i < 7; i++) if (i < 5 || used.contains(weekdays[i])) i];
    if (!dayIdx.contains(day)) day = dayIdx.first;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
        child: Row(children: [
          Expanded(child: SegmentedButton<_View>(
            showSelectedIcon: false,
            segments: const [ButtonSegment(value: _View.day, label: Text('Day'), icon: Icon(LucideIcons.list, size: 18)), ButtonSegment(value: _View.week, label: Text('Week'), icon: Icon(LucideIcons.layoutGrid, size: 18))],
            selected: {view},
            onSelectionChanged: (s) => setState(() => view = s.first),
          )),
          const SizedBox(width: 10),
          saving
              ? const SizedBox(width: 48, height: 48, child: Padding(padding: EdgeInsets.all(13), child: CircularProgressIndicator(strokeWidth: 2.5)))
              : PopupMenuButton<String>(
                  tooltip: 'Save or share the timetable',
                  onSelected: _export,
                  position: PopupMenuPosition.under,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'png', child: ListTile(dense: true, leading: Icon(LucideIcons.image), title: Text('Picture (PNG)'))),
                    PopupMenuItem(value: 'jpg', child: ListTile(dense: true, leading: Icon(LucideIcons.image), title: Text('Picture (JPG)'))),
                    PopupMenuItem(value: 'pdf', child: ListTile(dense: true, leading: Icon(LucideIcons.fileText), title: Text('Document (PDF)'))),
                  ],
                  child: Container(
                    width: 48, height: 48,
                    decoration: BoxDecoration(color: t.colorScheme.primary, shape: BoxShape.circle),
                    child: Icon(LucideIcons.download, color: t.colorScheme.onPrimary, size: 22),
                  ),
                ),
        ]),
      ),
      Expanded(child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 240),
        child: KeyedSubtree(key: ValueKey(view), child: view == _View.day ? _dayView(context, dayIdx, todayIdx) : _weekView(context, dayIdx, todayIdx)),
      )),
    ]);
  }

  // ------------------------------------------------------------------------------------------------------ day
  Widget _dayView(BuildContext context, List<int> dayIdx, int todayIdx) {
    final t = Theme.of(context);
    final tt = widget.summary.timetable;
    final slots = tt.where((s) => s.day == weekdays[day]).toList()..sort((a, b) => a.start.compareTo(b.start));
    final nowMin = widget.now.hour * 60 + widget.now.minute;
    final isToday = day == todayIdx;
    final nextIdx = isToday ? slots.indexWhere((s) => mins(s.start) > nowMin) : -1;
    final total = slots.fold<int>(0, (n, s) => n + mins(s.end) - mins(s.start));
    return Column(children: [
      SizedBox(
        height: 84,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(12, 12, 12, 4), children: [
          for (final i in dayIdx)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: () => setState(() => day = i),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 58,
                  decoration: BoxDecoration(
                    color: day == i ? t.colorScheme.primary : t.colorScheme.surfaceContainer,
                    borderRadius: BorderRadius.circular(20),
                    border: i == todayIdx && day != i ? Border.all(color: t.colorScheme.primary, width: 1.5) : null,
                  ),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Text(weekdays[i], style: t.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700, color: day == i ? t.colorScheme.onPrimary : t.colorScheme.onSurface)),
                    const SizedBox(height: 2),
                    Text('${tt.where((s) => s.day == weekdays[i]).length}', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800, color: day == i ? t.colorScheme.onPrimary : t.colorScheme.onSurfaceVariant)),
                  ]),
                ),
              ),
            ),
        ]),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
        child: Align(alignment: Alignment.centerLeft, child: Text(
          slots.isEmpty ? '${_fullDay(day)}: no classes' : '${_fullDay(day)}: ${slots.length} ${slots.length == 1 ? 'class' : 'classes'}, ${span(total)}${isToday ? '  ·  today' : ''}',
          style: t.textTheme.titleSmall?.copyWith(color: t.colorScheme.onSurfaceVariant),
        )),
      ),
      Expanded(
        child: slots.isEmpty
            ? EmptyState(icon: LucideIcons.coffee, title: isToday ? 'No classes today' : 'A free day', hint: 'Nothing is scheduled on ${_fullDay(day)}.')
            : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
                for (final (i, s) in slots.indexed) ...[
                  if (i > 0) _Gap(minutes: mins(s.start) - mins(slots[i - 1].end)),
                  Reveal(index: i, child: _ClassCard(slot: s, live: isToday && nowMin >= mins(s.start) && nowMin < mins(s.end), next: i == nextIdx, minutesLeft: isToday && nowMin >= mins(s.start) && nowMin < mins(s.end) ? mins(s.end) - nowMin : null, startsIn: i == nextIdx ? mins(s.start) - nowMin : null)),
                ],
              ]),
      ),
    ]);
  }

  /// A short code for a course, for the narrow blocks of the week grid: "Database Systems" is DS, "Software Engineering" SE.
  static String code(String course) {
    final words = course.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).toList();
    if (words.length == 1) return words.first.substring(0, words.first.length < 4 ? words.first.length : 4).toUpperCase();
    return words.take(4).map((w) => w[0].toUpperCase()).join();
  }

  static String _fullDay(int i) => const ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][i];

  // ------------------------------------------------------------------------------------------------------ week
  Widget _weekView(BuildContext context, List<int> dayIdx, int todayIdx) {
    final t = Theme.of(context);
    final tt = widget.summary.timetable;
    final startH = tt.map((s) => mins(s.start)).reduce((a, b) => a < b ? a : b) ~/ 60;
    final endH = (tt.map((s) => mins(s.end)).reduce((a, b) => a > b ? a : b) + 59) ~/ 60;
    const hourH = 64.0, timeW = 40.0;
    final courses = ({for (final s in tt) s.course}.toList()..sort());
    final nowMin = widget.now.hour * 60 + widget.now.minute;
    return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
      Container(
        padding: const EdgeInsets.fromLTRB(6, 10, 6, 6),
        decoration: BoxDecoration(color: t.colorScheme.surfaceContainer, borderRadius: BorderRadius.circular(24)),
        child: LayoutBuilder(builder: (context, c) {
          final colW = (c.maxWidth - timeW) / dayIdx.length;
          return Column(children: [
            Row(children: [
              const SizedBox(width: timeW),
              for (final i in dayIdx) SizedBox(width: colW, child: Center(child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: i == todayIdx ? BoxDecoration(color: t.colorScheme.primary, borderRadius: BorderRadius.circular(99)) : null,
                child: Text(weekdays[i], style: t.textTheme.labelMedium?.copyWith(fontWeight: FontWeight.w700, color: i == todayIdx ? t.colorScheme.onPrimary : t.colorScheme.onSurfaceVariant)),
              ))),
            ]),
            const SizedBox(height: 8),
            SizedBox(
              height: (endH - startH) * hourH + 8,
              child: Padding(padding: const EdgeInsets.only(top: 8), child: Stack(clipBehavior: Clip.none, children: [
                for (var h = 0; h <= endH - startH; h++) Positioned(left: 0, right: 0, top: h * hourH, child: Row(children: [
                  SizedBox(width: timeW, child: Transform.translate(offset: const Offset(0, -7), child: Text('${(startH + h).toString().padLeft(2, '0')}:00', style: t.textTheme.labelSmall?.copyWith(color: t.colorScheme.onSurfaceVariant)))),
                  Expanded(child: Divider(height: 1, color: t.colorScheme.outlineVariant)),
                ])),
                for (final s in tt) if (dayIdx.contains(weekdays.indexOf(s.day)))
                  Positioned(
                    left: timeW + dayIdx.indexOf(weekdays.indexOf(s.day)) * colW + 2,
                    width: colW - 4,
                    top: (mins(s.start) - startH * 60) / 60 * hourH + 1,
                    height: (mins(s.end) - mins(s.start)) / 60 * hourH - 2,
                    child: Container(
                      padding: const EdgeInsets.fromLTRB(5, 6, 3, 4),
                      decoration: BoxDecoration(color: _tint(t, courses.indexOf(s.course)), borderRadius: BorderRadius.circular(10)),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(code(s.course), maxLines: 1, overflow: TextOverflow.clip, style: t.textTheme.labelMedium?.copyWith(fontWeight: FontWeight.w800, height: 1.1, color: t.colorScheme.onSurface)),
                        if (mins(s.end) - mins(s.start) >= 75) Text(s.start, maxLines: 1, style: t.textTheme.labelSmall?.copyWith(fontSize: 9.5, color: t.colorScheme.onSurfaceVariant)),
                      ]),
                    ),
                  ),
                if (todayIdx < 7 && dayIdx.contains(todayIdx) && nowMin >= startH * 60 && nowMin <= endH * 60)
                  Positioned(left: timeW, right: 0, top: (nowMin - startH * 60) / 60 * hourH, child: Container(height: 2, color: t.colorScheme.primary)),
              ])),
            ),
          ]);
        }),
      ),
      const SizedBox(height: 16),
      Wrap(spacing: 14, runSpacing: 8, children: [
        for (final (i, c) in courses.indexed) Row(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 14, height: 14, decoration: BoxDecoration(color: _tint(t, i), borderRadius: BorderRadius.circular(5))),
          const SizedBox(width: 6),
          Text('${code(c)}  ·  $c', style: t.textTheme.bodySmall),
        ]),
      ]),
    ]);
  }

  /// A muted tint per course for the grid: the surface tones of the theme, nudged toward a hue, so it reads as one family.
  static Color _tint(ThemeData t, int i) {
    const hues = [18.0, 100.0, 210.0, 45.0, 300.0, 175.0, 60.0, 0.0];
    final dark = t.brightness == Brightness.dark;
    return HSLColor.fromAHSL(1, hues[i % hues.length], dark ? 0.22 : 0.30, dark ? 0.24 : 0.88).toColor();
  }
}

class _Gap extends StatelessWidget {
  const _Gap({required this.minutes});
  final int minutes;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    if (minutes <= 0) return const SizedBox(height: 8);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
      child: Row(children: [
        Icon(LucideIcons.coffee, size: 15, color: t.colorScheme.onSurfaceVariant),
        const SizedBox(width: 8),
        Text('Free for ${_TimetableScreenState.span(minutes)}', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        const SizedBox(width: 10),
        Expanded(child: Divider(height: 1, color: t.colorScheme.outlineVariant)),
      ]),
    );
  }
}

class _ClassCard extends StatelessWidget {
  const _ClassCard({required this.slot, required this.live, required this.next, this.minutesLeft, this.startsIn});
  final ClassSlot slot;
  final bool live, next;
  final int? minutesLeft, startsIn;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness;
    final len = _TimetableScreenState.mins(slot.end) - _TimetableScreenState.mins(slot.start);
    final fg = live ? t.colorScheme.onPrimaryContainer : t.colorScheme.onSurface;
    final sub = live ? t.colorScheme.onPrimaryContainer.withValues(alpha: 0.85) : t.colorScheme.onSurfaceVariant;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: live ? t.colorScheme.primaryContainer : t.colorScheme.surfaceContainer, borderRadius: BorderRadius.circular(24)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(width: 58, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(slot.start, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800, color: fg, fontFeatures: const [FontFeature.tabularFigures()])),
          Text(slot.end, style: t.textTheme.bodyMedium?.copyWith(color: sub, fontFeatures: const [FontFeature.tabularFigures()])),
        ])),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(slot.course, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700, color: fg)),
          const SizedBox(height: 4),
          Row(children: [
            Icon(LucideIcons.clock, size: 14, color: sub),
            const SizedBox(width: 5),
            Text(_TimetableScreenState.span(len), style: t.textTheme.bodySmall?.copyWith(color: sub)),
            if (slot.teacher != null) ...[
              const SizedBox(width: 12),
              Icon(LucideIcons.user, size: 14, color: sub),
              const SizedBox(width: 5),
              Flexible(child: Text(slot.teacher!, maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.bodySmall?.copyWith(color: sub))),
            ],
          ]),
          if (live) Padding(padding: const EdgeInsets.only(top: 8), child: Pill('Now · ${_TimetableScreenState.span(minutesLeft ?? 0)} left', color: Status.good(b))),
          if (next && !live) Padding(padding: const EdgeInsets.only(top: 8), child: Pill('Next · in ${_TimetableScreenState.span(startsIn ?? 0)}')),
        ])),
      ]),
    );
  }
}

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../data.dart';
import '../model.dart';
import 'widgets.dart';

/// Every announcement the portal posted, newest first, with a filter by course. New ones are marked until you have
/// looked at this screen.
class AnnouncementsScreen extends StatefulWidget {
  const AnnouncementsScreen({super.key, required this.summary, required this.prefs, required this.now});
  final Summary summary;
  final Prefs prefs;
  final DateTime now;
  @override
  State<AnnouncementsScreen> createState() => _AnnouncementsState();
}

class _AnnouncementsState extends State<AnnouncementsScreen> {
  String? course;   // null = all
  late final DateTime? seenAtOpen = widget.prefs.annSeen;   // what counts as new while this screen is open
  final open = <String>{};
  Timer? _readTimer;

  @override
  void dispose() { _readTimer?.cancel(); super.dispose(); }

  @override
  void initState() {
    super.initState();
    // looking at the list is what marks it read, but a moment later so the new ones are still marked on screen
    _readTimer = Timer(const Duration(milliseconds: 1200), () {
      if (!mounted) return;
      final latest = widget.summary.announcements.map((n) => n.postedAt).whereType<DateTime>().fold<DateTime?>(null, (a, b) => a == null || b.isAfter(a) ? b : a);
      if (latest != null && (widget.prefs.annSeen == null || latest.isAfter(widget.prefs.annSeen!))) widget.prefs.update(() => widget.prefs.annSeen = latest);
    });
  }

  String _when(DateTime? d) {
    if (d == null) return '';
    final diff = widget.now.difference(d);
    if (diff.inMinutes < 60) return diff.inMinutes <= 1 ? 'just now' : '${diff.inMinutes} min ago';
    if (diff.inHours < 24) return '${diff.inHours} h ago';
    if (diff.inDays < 7) return diff.inDays == 1 ? 'yesterday' : '${diff.inDays} days ago';
    return dayLabel(d);
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final all = [...widget.summary.announcements]..sort((a, b) => (b.postedAt ?? DateTime(2000)).compareTo(a.postedAt ?? DateTime(2000)));
    if (all.isEmpty) return const EmptyState(icon: LucideIcons.megaphone, title: 'No announcements yet', hint: 'Notices from your teachers appear here.');
    final courses = ({for (final n in all) n.course}.toList()..sort());
    final shown = course == null ? all : all.where((n) => n.course == course).toList();
    bool isNew(Note n) => n.postedAt != null && seenAtOpen != null && n.postedAt!.isAfter(seenAtOpen!);
    return Column(children: [
      if (courses.length > 1) SizedBox(
        height: 56,   // the chips are 48 dp tall inside this, the smallest comfortable tap target
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4), children: [
          Padding(padding: const EdgeInsets.symmetric(horizontal: 4), child: ChoiceChip(label: Text('All  ${all.length}'), selected: course == null, showCheckmark: false, onSelected: (_) => setState(() => course = null))),
          for (final c in courses) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: ChoiceChip(label: Text('$c  ${all.where((n) => n.course == c).length}'), selected: course == c, showCheckmark: false, onSelected: (_) => setState(() => course = course == c ? null : c)),
          ),
        ]),
      ),
      Expanded(child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
        for (final (i, n) in shown.indexed) Reveal(index: i, child: Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Card(
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: () => setState(() => open.contains(n.id) ? open.remove(n.id) : open.add(n.id)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    if (isNew(n)) Padding(padding: const EdgeInsets.only(top: 6, right: 10), child: Container(width: 9, height: 9, decoration: BoxDecoration(color: t.colorScheme.primary, shape: BoxShape.circle))),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(n.title, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text([n.course, _when(n.postedAt)].where((e) => e.isNotEmpty).join(' · '), style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
                    ])),
                    const SizedBox(width: 8),
                    AnimatedRotation(turns: open.contains(n.id) ? 0.5 : 0, duration: const Duration(milliseconds: 200), child: Icon(LucideIcons.chevronDown, size: 20, color: t.colorScheme.onSurfaceVariant)),
                  ]),
                  AnimatedSize(
                    duration: const Duration(milliseconds: 220), curve: Curves.easeOutCubic, alignment: Alignment.topCenter,
                    child: !open.contains(n.id) ? const SizedBox(width: double.infinity) : Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text(n.text.isEmpty ? 'No text.' : n.text, style: t.textTheme.bodyMedium?.copyWith(height: 1.4)),
                    ),
                  ),
                ]),
              ),
            ),
          ),
        )),
      ])),
    ]);
  }
}

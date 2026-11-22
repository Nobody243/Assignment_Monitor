import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:flutter/services.dart';

import '../data.dart';
import '../model.dart';
import '../theme.dart';
import 'widgets.dart';

enum _Filter { todo, extended, overdue, submitted, all }

const _filterLabels = {_Filter.todo: 'To do', _Filter.extended: 'Extended', _Filter.overdue: 'Overdue', _Filter.submitted: 'Submitted', _Filter.all: 'All'};

class WorkScreen extends StatefulWidget {
  const WorkScreen({super.key, required this.summary, required this.now, required this.prefs});
  final Summary summary;
  final DateTime now;
  final Prefs prefs;
  @override
  State<WorkScreen> createState() => _WorkState();
}

class _WorkState extends State<WorkScreen> {
  _Filter filter = _Filter.todo;

  bool _match(Work w) => switch (filter) {
        _Filter.todo => w.todo,
        _Filter.extended => w.extended && !w.submitted && w.open,
        _Filter.overdue => w.overdue,
        _Filter.submitted => w.submitted,
        _Filter.all => true,
      };

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final all = widget.summary.work;
    final rows = all.where(_match).toList()..sort((a, b) => (a.due ?? DateTime(2100)).compareTo(b.due ?? DateTime(2100)));
    int count(_Filter f) => switch (f) {
          _Filter.todo => all.where((w) => w.todo).length,
          _Filter.extended => all.where((w) => w.extended && !w.submitted && w.open).length,
          _Filter.overdue => all.where((w) => w.overdue).length,
          _Filter.submitted => all.where((w) => w.submitted).length,
          _Filter.all => all.length,
        };
    final groups = <String, List<Work>>{};
    for (final w in rows) {
      final d = w.due;
      final key = d == null ? 'No date' : w.overdue ? 'Overdue' : w.submitted ? 'Submitted' : d.difference(widget.now).inHours < 24 && d.isAfter(widget.now) ? 'Due today' : d.difference(widget.now).inDays < 7 ? 'This week' : 'Later';
      (groups[key] ??= []).add(w);
    }
    const order = ['Due today', 'This week', 'Later', 'Overdue', 'Submitted', 'No date'];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(
        height: 56,   // the chips are 48 dp tall inside this, the smallest comfortable tap target
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4), children: [
          for (final f in _Filter.values)
            Padding(padding: const EdgeInsets.symmetric(horizontal: 4), child: ChoiceChip(label: Text('${_filterLabels[f]}  ${count(f)}'), selected: filter == f, onSelected: (_) => setState(() => filter = f))),
        ]),
      ),
      Expanded(
        child: rows.isEmpty
            ? const EmptyState(icon: Icons.task_alt, title: 'Nothing here', hint: 'Try another filter above.')
            : ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
                for (final g in order)
                  if (groups[g] != null) ...[
                    Padding(padding: const EdgeInsets.only(top: 12, bottom: 6), child: Text('$g  ·  ${groups[g]!.length}', style: t.textTheme.labelLarge?.copyWith(color: t.colorScheme.onSurfaceVariant, fontWeight: FontWeight.w700))),
                    for (final (i, w) in groups[g]!.indexed) Reveal(index: i, child: _WorkTile(work: w, now: widget.now, prefs: widget.prefs)),
                  ],
              ]),
      ),
    ]);
  }
}

class _WorkTile extends StatelessWidget {
  const _WorkTile({required this.work, required this.now, required this.prefs});
  final Work work;
  final DateTime now;
  final Prefs prefs;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness, w = work, due = w.due;
    Color? c;
    String chip;
    if (w.submitted) { chip = 'Submitted'; c = Status.good(b); }
    else if (w.overdue) { chip = 'Overdue'; c = Status.bad(b); }
    else if (due != null) {
      final left = due.difference(now);
      chip = countdown(due, now);
      c = left.inHours < 3 ? Status.bad(b) : left.inHours < 24 ? Status.warn(b) : null;
    } else { chip = ''; }
    final muted = prefs.done.contains(w.id) || (prefs.snoozed[w.id]?.isAfter(now) ?? false);
    final card = Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () { HapticFeedback.selectionClick(); showModalBottomSheet(context: context, showDragHandle: true, isScrollControlled: true, builder: (_) => _Detail(work: w, now: now, prefs: prefs)); },
        child: IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Expanded(child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
              child: Row(children: [
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(w.title, style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text('${w.course} · #${w.number}', maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
                  if (due != null) Text('${dayLabel(due)} · ${timeLabel(due)}${w.extended ? '  (extended)' : ''}', style: t.textTheme.bodySmall?.copyWith(color: w.extended ? Status.warn(b) : t.colorScheme.onSurfaceVariant)),
                ])),
                const SizedBox(width: 8),
                Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  if (chip.isNotEmpty) Pill(chip, color: c),
                  if (muted) Padding(padding: const EdgeInsets.only(top: 6), child: Icon(LucideIcons.bellOff, size: 16, color: t.colorScheme.onSurfaceVariant)),
                ]),
              ]),
            )),
          ]),
        ),
      ),
    );
    Widget side(Color bg, IconData i, String label, Alignment a) => Container(
          alignment: a, padding: const EdgeInsets.symmetric(horizontal: 22),
          decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
          child: Row(mainAxisSize: MainAxisSize.min, children: [Icon(i, color: Colors.white), const SizedBox(width: 8), Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700))]),
        );
    final swipeable = w.open && !w.submitted;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: !swipeable ? card : Dismissible(
        key: ValueKey('swipe-${w.id}'),
        background: side(Status.good(b), LucideIcons.circleCheck, 'Done', Alignment.centerLeft),
        secondaryBackground: side(t.colorScheme.secondary, LucideIcons.alarmClock, 'Snooze 1 h', Alignment.centerRight),
        confirmDismiss: (dir) async {
          HapticFeedback.mediumImpact();
          final m = ScaffoldMessenger.of(context);
          m.hideCurrentSnackBar();
          if (dir == DismissDirection.startToEnd) {
            prefs.update(() => prefs.done.add(w.id));
            m.showSnackBar(SnackBar(content: const Text('Marked done. No more reminders for it.'), action: SnackBarAction(label: 'Undo', onPressed: () => prefs.update(() => prefs.done.remove(w.id)))));
          } else {
            prefs.update(() => prefs.snoozed[w.id] = now.add(const Duration(hours: 1)));
            m.showSnackBar(SnackBar(content: const Text('Snoozed for 1 hour.'), action: SnackBarAction(label: 'Undo', onPressed: () => prefs.update(() => prefs.snoozed.remove(w.id)))));
          }
          return false;   // the row stays: it only goes quiet
        },
        child: card,
      ),
    );
  }
}

class _Detail extends StatelessWidget {
  const _Detail({required this.work, required this.now, required this.prefs});
  final Work work;
  final DateTime now;
  final Prefs prefs;
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), b = t.brightness, w = work, due = w.due;
    final left = due?.difference(now);
    final late = !w.submitted && (w.overdue || (left != null && left.isNegative));
    final tone = w.submitted ? Status.good(b) : late ? Status.bad(b) : (left != null && left.inHours < 24) ? Status.warn(b) : t.colorScheme.primary;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 16 + MediaQuery.of(context).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${w.course} · assignment #${w.number}', maxLines: 1, overflow: TextOverflow.ellipsis, style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant))),
          ]),
          const SizedBox(height: 6),
          Text(w.title, style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(color: tone.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(24)),
            child: Row(children: [
              Icon(w.submitted ? LucideIcons.circleCheck : late ? LucideIcons.circleAlert : LucideIcons.timer, color: tone, size: 30),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(w.submitted ? 'Submitted' : late ? 'Overdue' : due == null ? 'No due date' : countdown(due, now), style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800, color: tone)),
                if (due != null) Text('${dayLabel(due)}, ${timeLabel(due)}', style: t.textTheme.bodyMedium),
              ])),
            ]),
          ),
          const SizedBox(height: 12),
          if (w.extended && w.wasDue != null) _Fact('Extended from', w.wasDue!),
          if (w.marks != null) _Fact('Marks', w.marks!),
          _Fact('Can submit', w.canSubmit ? 'Yes, on the portal' : 'No'),
          const SizedBox(height: 16),
          if (w.open && !w.submitted) Row(children: [
            Expanded(child: FilledButton.tonalIcon(icon: const Icon(LucideIcons.alarmClock), onPressed: () {
              prefs.update(() => prefs.snoozed[w.id] = now.add(const Duration(hours: 1)));
              Navigator.pop(context);
            }, label: const Text('Snooze 1 h'))),
            const SizedBox(width: 10),
            Expanded(child: FilledButton.icon(icon: const Icon(LucideIcons.check), onPressed: () { prefs.update(() => prefs.done.add(w.id)); Navigator.pop(context); }, label: const Text('Done'))),
          ]),
          const SizedBox(height: 10),
          Text('Submit on the portal or the PC app. This phone shows deadlines and reminds you.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        ]),
      ),
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact(this.k, this.v);
  final String k, v;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(k, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
          const SizedBox(width: 16),
          // a long value (a date with its time, a note) wraps and stays on the right instead of running off the edge
          Expanded(child: Text(v, textAlign: TextAlign.end, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );
}

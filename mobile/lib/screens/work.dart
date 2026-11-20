import 'package:flutter/material.dart';
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
        height: 52,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), children: [
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
    final cc = courseColor(w.course);
    final card = Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () { HapticFeedback.selectionClick(); showModalBottomSheet(context: context, showDragHandle: true, isScrollControlled: true, builder: (_) => _Detail(work: w, now: now, prefs: prefs)); },
        child: IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Container(width: 5, color: cc),
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
                  if (muted) Padding(padding: const EdgeInsets.only(top: 6), child: Icon(Icons.notifications_off_outlined, size: 16, color: t.colorScheme.onSurfaceVariant)),
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
        background: side(Status.good(b), Icons.check_circle_outline, 'Done', Alignment.centerLeft),
        secondaryBackground: side(t.colorScheme.secondary, Icons.snooze, 'Snooze 1 h', Alignment.centerRight),
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
    final t = Theme.of(context), w = work, due = w.due;
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(w.title, style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text('${w.course} · assignment #${w.number}', style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        const SizedBox(height: 16),
        if (due != null) _Fact('Due', '${dayLabel(due)}, ${timeLabel(due)}'),
        if (due != null && w.open) _Fact('Time left', countdown(due, now)),
        if (w.extended && w.wasDue != null) _Fact('Extended from', w.wasDue!),
        _Fact('Status', w.submitted ? 'Submitted' : w.overdue ? 'Overdue, not submitted' : 'Not submitted'),
        if (w.marks != null) _Fact('Marks', w.marks!),
        const SizedBox(height: 16),
        if (w.open) Row(children: [
          Expanded(child: FilledButton.tonal(onPressed: () {
            prefs.update(() => prefs.snoozed[w.id] = now.add(const Duration(hours: 1)));
            Navigator.pop(context);
          }, child: const Text('Snooze 1 h'))),
          const SizedBox(width: 10),
          Expanded(child: FilledButton(onPressed: () { prefs.update(() => prefs.done.add(w.id)); Navigator.pop(context); }, child: const Text('Done'))),
        ]),
        const SizedBox(height: 8),
        OutlinedButton.icon(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.open_in_new), label: Text(w.canSubmit ? 'Open the portal to submit' : 'Open the portal')),
        const SizedBox(height: 4),
        Text('Uploads stay on the PC app and the portal; the phone shows and reminds.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      ]),
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact(this.k, this.v);
  final String k, v;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
        ]),
      );
}

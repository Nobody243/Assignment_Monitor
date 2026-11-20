import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../model.dart';
import '../reminders.dart';

/// The first time the app has real data it asks, once and in this order: how you want to be reminded (and for the
/// permission to notify you), then whether to lock the app. Both can be changed later in Settings.
Future<void> runFirstRun(BuildContext context, AppModel model) async {
  await showModalBottomSheet<void>(
    context: context, isScrollControlled: true, isDismissible: false, enableDrag: false, showDragHandle: true,
    builder: (_) => ReminderSetupSheet(model: model),
  );
  if (context.mounted && !model.prefs.appLock) {
    await showDialog<void>(context: context, builder: (_) => LockOfferDialog(model: model));
  }
  model.finishFirstRun();
}

class ReminderSetupSheet extends StatefulWidget {
  const ReminderSetupSheet({super.key, required this.model});
  final AppModel model;
  @override
  State<ReminderSetupSheet> createState() => _ReminderSetupState();
}

class _ReminderSetupState extends State<ReminderSetupSheet> {
  bool? allowed;   // null until asked
  bool asking = false;

  Future<void> _allow() async {
    setState(() => asking = true);
    final ok = await Reminders.allowed();
    if (mounted) setState(() { allowed = ok; asking = false; });
    await widget.model.replan();
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), p = widget.model.prefs;
    final canNotify = Reminders.supported;
    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 16 + MediaQuery.of(context).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Set up your reminders', style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Text('The phone reminds you by itself, with no network needed. Choose how early.', style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant, height: 1.4)),
          const SizedBox(height: 16),
          Text('Remind me before a deadline', style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final h in [48, 24, 12, 6, 3, 1])
              FilterChip(
                label: Text(h == 48 ? '2 days' : h == 24 ? '1 day' : '$h h'), selected: p.leads.contains(h),
                onSelected: (on) => setState(() => p.update(() { on ? p.leads.add(h) : p.leads.remove(h); p.leads.sort((a, b) => b - a); })),
              ),
          ]),
          const SizedBox(height: 8),
          SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Sunday summary'), subtitle: const Text('Sunday at 18:00: what is due next week'), value: p.weekly, onChanged: (v) => setState(() => p.update(() => p.weekly = v))),
          SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Morning digest'), subtitle: const Text('Every day at 07:30: due today and today\'s classes'), value: p.digest, onChanged: (v) => setState(() => p.update(() => p.digest = v))),
          const SizedBox(height: 4),
          if (canNotify) Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(18)),
            child: Row(children: [
              Icon(allowed == true ? LucideIcons.bellRing : LucideIcons.bell, color: allowed == true ? t.colorScheme.primary : t.colorScheme.onSurfaceVariant),
              const SizedBox(width: 12),
              Expanded(child: Text(allowed == true ? 'Notifications are allowed.' : allowed == false ? 'Not allowed. You can allow them later in Settings, Reminders.' : 'Android needs your permission to show reminders.', style: t.textTheme.bodyMedium)),
              if (allowed != true) FilledButton.tonal(onPressed: asking ? null : _allow, child: Text(asking ? '...' : 'Allow')),
            ]),
          ),
          const SizedBox(height: 18),
          FilledButton(style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)), onPressed: () => Navigator.pop(context), child: const Text('Done')),
        ]),
      ),
    );
  }
}

class LockOfferDialog extends StatefulWidget {
  const LockOfferDialog({super.key, required this.model});
  final AppModel model;
  @override
  State<LockOfferDialog> createState() => _LockOfferState();
}

class _LockOfferState extends State<LockOfferDialog> {
  String? problem;
  bool busy = false;

  Future<void> _turnOn() async {
    setState(() { busy = true; problem = null; });
    final err = await widget.model.setAppLock(true);
    if (!mounted) return;
    if (err == null) { Navigator.pop(context); } else { setState(() { busy = false; problem = err; }); }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      icon: const Icon(LucideIcons.lock),
      title: const Text('Protect your grades?'),
      content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Your grades, seat numbers and deadlines are private. With the app lock on, the app asks for your fingerprint, face or PIN when it opens, and reminders on the lock screen say only "Assignment due soon".'),
        const SizedBox(height: 8),
        Text('You can change this any time in Settings, Security.', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
        if (problem != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text(problem!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
      ]),
      actions: [
        TextButton(onPressed: busy ? null : () => Navigator.pop(context), child: const Text('Not now')),
        FilledButton(onPressed: busy ? null : _turnOn, child: const Text('Turn on')),
      ],
    );
  }
}

import 'package:flutter/material.dart';

import '../data.dart';
import '../logic.dart';
import '../model.dart';
import '../reminders.dart';
import '../source.dart' show repoName;
import '../theme.dart';
import 'widgets.dart';

/// Settings is a short list of sections; each one opens its own page, so a page only ever holds one kind of choice.
class SettingsHub extends StatelessWidget {
  const SettingsHub({super.key, required this.summary, required this.prefs, required this.model});
  final Summary summary;
  final Prefs prefs;
  final AppModel model;

  void _open(BuildContext context, String title, Widget Function() body) =>
      Navigator.of(context).push(slideRoute<void>(Scaffold(appBar: AppBar(title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700))), body: SafeArea(child: body()))));

  String _lead(int h) => h == 48 ? '2 days' : h == 24 ? '1 day' : '$h h';

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    Widget row(IconData i, String title, String sub, Widget Function() page) => ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          leading: Container(width: 44, height: 44, decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHighest, borderRadius: BorderRadius.circular(14)), child: Icon(i, size: 22)),
          title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => _open(context, title, page),
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
      Card(child: Column(children: [
        row(Icons.notifications_outlined, 'Reminders', prefs.leads.isEmpty ? 'Off' : '${prefs.leads.map(_lead).join(', ')} before', () => RemindersSettings(prefs: prefs, model: model)),
        const Divider(height: 1, indent: 76),
        row(Icons.palette_outlined, 'Appearance', '${prefs.palette.label} · ${switch (prefs.mode) { ThemeMode.system => 'follows the phone', ThemeMode.light => 'light', ThemeMode.dark => 'dark' }}', () => AppearanceSettings(prefs: prefs)),
        const Divider(height: 1, indent: 76),
        row(Icons.person_outline, 'Account and data', model.demo ? 'Demo data' : (model.login ?? 'Signed in'), () => AccountSettings(summary: summary, model: model)),
        const Divider(height: 1, indent: 76),
        row(Icons.info_outline, 'About and privacy', 'What this app stores and sends', () => const AboutSettings()),
      ])),
    ]);
  }
}

class _Head extends StatelessWidget {
  const _Head(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: 8, bottom: 10), child: Text(text, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)));
}

// ---------------------------------------------------------------------------------------------- reminders
class RemindersSettings extends StatefulWidget {
  const RemindersSettings({super.key, required this.prefs, required this.model});
  final Prefs prefs;
  final AppModel model;
  @override
  State<RemindersSettings> createState() => _RemindersState();
}

class _RemindersState extends State<RemindersSettings> {
  @override
  Widget build(BuildContext context) {
    final p = widget.prefs, m = widget.model;
    return ListView(padding: const EdgeInsets.all(16), children: [
      const _Head('Remind me before a deadline'),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final h in [48, 24, 12, 6, 3, 1])
          FilterChip(
            label: Text(h == 48 ? '2 days' : h == 24 ? '1 day' : '$h h'),
            selected: p.leads.contains(h),
            onSelected: (on) => setState(() => p.update(() { on ? p.leads.add(h) : p.leads.remove(h); p.leads.sort((a, b) => b - a); })),
          ),
      ]),
      const SizedBox(height: 8),
      const Muted('Reminders are scheduled on this phone from the latest summary, so they work without a network.'),
      const Divider(height: 32),
      const _Head('Quiet hours'),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.bedtime_outlined), title: Text('23:00 to 07:00'), subtitle: Text('Reminders in this window arrive silently, with no sound or vibration.')),
      const Divider(height: 32),
      const _Head('Permission'),
      if (m.demo || !Reminders.supported)
        const Muted('Reminders are available on the Android app, with real data.')
      else ...[
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.notifications_active_outlined), title: Text('${m.scheduled} reminders scheduled'), subtitle: const Text('Allow notifications so they can appear.'),
            trailing: FilledButton.tonal(onPressed: () async { await Reminders.allowed(); await m.replan(); if (mounted) setState(() {}); }, child: const Text('Allow'))),
      ],
    ]);
  }
}

// ---------------------------------------------------------------------------------------------- appearance
class AppearanceSettings extends StatefulWidget {
  const AppearanceSettings({super.key, required this.prefs});
  final Prefs prefs;
  @override
  State<AppearanceSettings> createState() => _AppearanceState();
}

class _AppearanceState extends State<AppearanceSettings> {
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), p = widget.prefs;
    return ListView(padding: const EdgeInsets.all(16), children: [
      const _Head('Colour'),
      Row(children: [
        for (final pal in palettes)
          Expanded(child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => setState(() => p.update(() => p.palette = pal)),
            child: Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Column(children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 52, height: 52,
                decoration: BoxDecoration(color: pal.seed, shape: BoxShape.circle, border: Border.all(color: p.palette.key == pal.key ? t.colorScheme.onSurface : Colors.transparent, width: 3)),
                child: p.palette.key == pal.key ? const Icon(Icons.check, color: Colors.white) : null,
              ),
              const SizedBox(height: 6),
              Text(pal.label, style: t.textTheme.labelMedium),
            ])),
          )),
      ]),
      const Divider(height: 32),
      const _Head('Theme'),
      SegmentedButton<ThemeMode>(
        segments: const [ButtonSegment(value: ThemeMode.system, label: Text('System')), ButtonSegment(value: ThemeMode.light, label: Text('Light')), ButtonSegment(value: ThemeMode.dark, label: Text('Dark'))],
        selected: {p.mode},
        onSelectionChanged: (s) => setState(() => p.update(() => p.mode = s.first)),
      ),
    ]);
  }
}

// ---------------------------------------------------------------------------------------------- account
class AccountSettings extends StatelessWidget {
  const AccountSettings({super.key, required this.summary, required this.model});
  final Summary summary;
  final AppModel model;
  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      const _Head('Signed in'),
      ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.person_outline), title: Text(summary.studentName),
          subtitle: Text(model.demo ? 'Demo data, nothing is read from GitHub' : 'GitHub: ${model.login ?? '–'}')),
      if (!model.demo) ...[
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.folder_outlined), title: const Text('Reading from'), subtitle: Text('${model.login ?? ''}/$repoName')),
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.sync), title: const Text('Last read from GitHub'),
            subtitle: Text(model.fetchedAt == null ? 'Not yet' : '${agoLabel(model.age!)} · summary made ${agoLabel(DateTime.now().difference(summary.generatedAt))}')),
      ],
      const Divider(height: 32),
      OutlinedButton.icon(
        onPressed: () async { Navigator.of(context).popUntil((r) => r.isFirst); await model.signOut(); },
        icon: const Icon(Icons.logout),
        label: Text(model.demo ? 'Leave the demo' : 'Sign out and forget this phone'),
      ),
      const SizedBox(height: 8),
      const Muted('Signing out deletes the sign-in, the saved summary and every scheduled reminder from this phone.'),
    ]);
  }
}

// ---------------------------------------------------------------------------------------------- about
class AboutSettings extends StatelessWidget {
  const AboutSettings({super.key});
  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: const [
      _Head('What the phone holds'),
      ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.lock_outline), title: Text('No portal password'), subtitle: Text('The phone never sees it and never contacts the portal.')),
      ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.key_outlined), title: Text('A GitHub sign-in'), subtitle: Text('Kept in the phone\'s secure storage, used only to read your own repository.')),
      ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.save_outlined), title: Text('The last summary'), subtitle: Text('Stored on the phone so the app opens offline.')),
      Divider(height: 32),
      _Head('Sharing'),
      Muted('No analytics and no crash reporting. Nothing is sent anywhere except the request to GitHub that reads your summary file.'),
      Divider(height: 32),
      _Head('App'),
      ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.phone_android_outlined), title: Text('Assignment Monitor for phones'), subtitle: Text('Version 1.0.0')),
    ]);
  }
}

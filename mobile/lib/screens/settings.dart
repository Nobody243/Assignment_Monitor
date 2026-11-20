import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show Clipboard, ClipboardData;
import 'package:share_plus/share_plus.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../alerts.dart';
import '../background.dart';
import '../data.dart';
import '../logic.dart';
import '../model.dart';
import '../reminders.dart';
import '../source.dart' show repoName;
import '../theme.dart';
import 'cloud_setup_screens.dart' show CloudSettingsPage;   // phone-only Cloud checks
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
          trailing: const Icon(LucideIcons.chevronRight, size: 20),
          onTap: () => _open(context, title, page),
        );
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
      Card(child: Column(children: [
        row(LucideIcons.bell, 'Reminders', prefs.leads.isEmpty ? 'Off' : '${prefs.leads.map(_lead).join(', ')} before', () => RemindersSettings(prefs: prefs, model: model)),
        const Divider(height: 1, indent: 76),
        row(LucideIcons.palette, 'Appearance', '${prefs.palette.label} · ${switch (prefs.mode) { ThemeMode.system => 'follows the phone', ThemeMode.light => 'light', ThemeMode.dark => 'dark' }}', () => AppearanceSettings(prefs: prefs)),
        const Divider(height: 1, indent: 76),
        row(LucideIcons.calendarPlus, 'Calendar', 'Add deadlines and exams to your calendar', () => CalendarSettings(summary: summary)),
        const Divider(height: 1, indent: 76),
        row(LucideIcons.shieldCheck, 'Security', model.prefs.appLock ? 'App lock is on' : 'App lock is off', () => SecuritySettings(model: model)),
        const Divider(height: 1, indent: 76),
        if (!model.demo) ...[
          row(LucideIcons.cloud, 'Cloud checks', 'Run, change the portal login, or turn off', () => CloudSettingsPage(model: model)),
          const Divider(height: 1, indent: 76),
        ],
        row(LucideIcons.userRound, 'Account and data', model.demo ? 'Demo data' : (model.login ?? 'Signed in'), () => AccountSettings(summary: summary, model: model)),
        const Divider(height: 1, indent: 76),
        row(LucideIcons.info, 'About and privacy', 'What this app stores and sends', () => AboutSettings(summary: summary, model: model)),
      ])),
      const SizedBox(height: 28),
      OutlinedButton.icon(
        style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52), foregroundColor: Status.bad(t.brightness), side: BorderSide(color: Status.bad(t.brightness).withValues(alpha: 0.5))),
        onPressed: () => _confirmSignOut(context),
        icon: const Icon(LucideIcons.logOut, size: 20),
        label: Text(model.demo ? 'Leave the demo' : 'Sign out'),
      ),
      const SizedBox(height: 8),
      Center(child: Text('Phone app 1.0.0', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant))),
    ]);
  }

  Future<void> _confirmSignOut(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(model.demo ? 'Leave the demo?' : 'Sign out?'),
        content: Text(model.demo ? 'You will go back to the first screen.' : 'This deletes the sign-in, the saved summary and every scheduled reminder from this phone. Your data on GitHub and the PC is not touched.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(model.demo ? 'Leave' : 'Sign out')),
        ],
      ),
    );
    if (ok == true) await model.signOut();
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
      const _Head('Summaries and alerts'),
      SwitchListTile(
        contentPadding: EdgeInsets.zero, title: const Text('Sunday summary'),
        subtitle: const Text('Sunday at 18:00: what is due next week, exams, and attendance to watch'),
        value: p.weekly, onChanged: (v) => setState(() => p.update(() => p.weekly = v)),
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero, title: const Text('Morning digest'),
        subtitle: const Text('Every day at 07:30: what is due today, today\'s classes, an exam in the next three days'),
        value: p.digest, onChanged: (v) => setState(() => p.update(() => p.digest = v)),
      ),
      if (Reminders.isAndroid) SwitchListTile(
        contentPadding: EdgeInsets.zero, title: const Text('Updates while the app is closed'),
        subtitle: const Text('About every two hours the phone checks GitHub and tells you about a new announcement, assignment, extension, mark, exam seat or result. Android may delay a check to save battery.'),
        value: p.alerts, onChanged: (v) { setState(() => p.update(() => p.alerts = v)); BackgroundCheck.apply(on: v); },
      ),
      const Divider(height: 32),
      const _Head('Quiet hours'),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.moon), title: Text('23:00 to 07:00'), subtitle: Text('Deadline reminders in this window arrive silently, with no sound or vibration.')),
      const Divider(height: 32),
      const _Head('Permission'),
      if (m.demo || !Reminders.supported)
        const Muted('Reminders are available on the Android app, with real data.')
      else ...[
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.bellRing), title: Text('${m.scheduled} reminders scheduled'), subtitle: const Text('Allow notifications so they can appear.'),
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
      ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.userRound), title: Text(summary.studentName),
          subtitle: Text(model.demo ? 'Demo data, nothing is read from GitHub' : 'GitHub: ${model.login ?? '–'}')),
      if (!model.demo) ...[
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.folderGit2), title: const Text('Reading from'), subtitle: Text('${model.login ?? ''}/$repoName')),
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.refreshCw), title: const Text('Last read from GitHub'),
            subtitle: Text(model.fetchedAt == null ? 'Not yet' : '${agoLabel(model.age!)} · summary made ${agoLabel(DateTime.now().difference(summary.generatedAt))}')),
      ],
    ]);
  }
}

// ---------------------------------------------------------------------------------------------- about
class AboutSettings extends StatelessWidget {
  const AboutSettings({super.key, required this.summary, required this.model});
  final Summary summary;
  final AppModel model;
  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      const _Head('What the phone holds'),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.lock), title: Text('No portal password'), subtitle: Text('The phone never sees it and never contacts the portal.')),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.keyRound), title: Text('A GitHub sign-in'), subtitle: Text('Kept in the phone\'s secure storage, used only to read your own repository.')),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.hardDrive), title: Text('The last summary'), subtitle: Text('Stored on the phone so the app opens offline.')),
      const Divider(height: 32),
      const _Head('Sharing'),
      const Muted('No analytics and no crash reporting. Nothing is sent anywhere except the request to GitHub that reads your summary file.'),
      const Divider(height: 32),
      const _Head('App'),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.smartphone), title: Text('Assignment Monitor for phones'), subtitle: Text('Version $appVersion')),
      ListTile(
        contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.clipboardCopy), title: const Text('Copy support info'),
        subtitle: const Text('Versions, freshness and counts for a bug report. No name, grades or sign-in.'),
        onTap: () async {
          final text = supportInfo(summary, platform: kIsWeb ? 'web' : defaultTargetPlatform.name, lastRead: model.fetchedAt, error: model.error, reminders: model.scheduled);
          await Clipboard.setData(ClipboardData(text: text));
          if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied. Paste it into your message.')));
        },
      ),
    ]);
  }
}

// ---------------------------------------------------------------------------------------------- calendar
/// Hands the deadlines and exams to the phone's calendar as an .ics file (the share sheet offers the calendar app).
class CalendarSettings extends StatelessWidget {
  const CalendarSettings({super.key, required this.summary});
  final Summary summary;

  Future<void> _share(BuildContext context) async {
    final ics = calendarIcs(summary, DateTime.now());
    try {
      await SharePlus.instance.share(ShareParams(
        files: [XFile.fromData(Uint8List.fromList(utf8.encode(ics)), mimeType: 'text/calendar', name: 'Assignment Monitor.ics')],
        fileNameOverrides: const ['Assignment Monitor.ics'],
        subject: 'Assignment Monitor: deadlines and exams',
      ));
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not make the calendar file. $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final deadlines = summary.work.where((w) => w.todo && w.open && w.due != null).length;
    final exams = summary.exams.where((e) => e.scheduled && e.day != null).length;
    return ListView(padding: const EdgeInsets.all(16), children: [
      const _Head('Add to your calendar'),
      Text('Makes one calendar file with $deadlines open deadline${deadlines == 1 ? '' : 's'} and $exams exam${exams == 1 ? '' : 's'}. Each deadline is a 30 minute block ending at the due time, with an alarm an hour before; exams carry the room and seat. Open the file in your calendar app to add them.',
          style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant, height: 1.4)),
      const SizedBox(height: 16),
      FilledButton.icon(
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        onPressed: deadlines + exams == 0 ? null : () => _share(context),
        icon: const Icon(LucideIcons.calendarPlus, size: 20),
        label: const Text('Make the calendar file'),
      ),
      const SizedBox(height: 12),
      const Muted('The file is a snapshot. Deadlines that change later (an extension, say) need a new file; the desktop app can keep a calendar feed up to date.'),
    ]);
  }
}

// ---------------------------------------------------------------------------------------------- security
class SecuritySettings extends StatefulWidget {
  const SecuritySettings({super.key, required this.model});
  final AppModel model;
  @override
  State<SecuritySettings> createState() => _SecurityState();
}

class _SecurityState extends State<SecuritySettings> {
  String? problem;
  bool busy = false;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), m = widget.model;
    return ListView(padding: const EdgeInsets.all(16), children: [
      const _Head('App lock'),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Ask for my fingerprint, face or PIN'),
        subtitle: const Text('When the app opens, and when you come back to it after more than 30 seconds away. It uses the same lock as the rest of your phone; the app never sees your fingerprint or PIN.'),
        value: m.prefs.appLock,
        onChanged: busy ? null : (v) async {
          setState(() { busy = true; problem = null; });
          final err = await m.setAppLock(v);
          if (mounted) setState(() { busy = false; problem = err; });
        },
      ),
      if (problem != null) Padding(padding: const EdgeInsets.only(top: 4), child: Text(problem!, style: TextStyle(color: t.colorScheme.error))),
      const Divider(height: 32),
      const _Head('What the lock protects'),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.eyeOff), title: Text('Your grades, seat numbers and deadlines'), subtitle: Text('They stay hidden behind the lock screen. Reminders still arrive, and they show only the assignment title.')),
      const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.lock), title: Text('Sign-in token'), subtitle: Text('Kept in the phone\'s secure storage whether or not the lock is on.')),
    ]);
  }
}

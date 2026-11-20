import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../model.dart';
import 'intro.dart' show BrandMark;
import '../source.dart' show DeviceCode, repoName;

/// First run: sign in to GitHub (device flow) or look at the demo. Also shown while the first summary is awaited.
class SignInScreen extends StatelessWidget {
  const SignInScreen({super.key, required this.model});
  final AppModel model;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final c = model.code;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: ListView(padding: const EdgeInsets.all(24), shrinkWrap: true, children: [
              Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(32),
                  color: t.colorScheme.primaryContainer,
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const BrandMark(size: 60),
                  const SizedBox(height: 18),
                  Text('Assignment\nMonitor', style: t.textTheme.headlineLarge?.copyWith(fontWeight: FontWeight.w800, height: 1.05, color: t.colorScheme.onPrimaryContainer)),
                  const SizedBox(height: 8),
                  Text('Never miss a deadline again.', style: t.textTheme.titleMedium?.copyWith(color: t.colorScheme.onPrimaryContainer.withValues(alpha: 0.85))),
                ]),
              ),
              const SizedBox(height: 22),
              for (final (icon, text) in const [
                (LucideIcons.timer, 'Live countdowns and reminders that work offline'),
                (LucideIcons.calendarCheck, 'Attendance: exactly how many hours you can still miss'),
                (LucideIcons.lock, 'Reads from your own private GitHub repository. Your portal password never touches the phone.'),
              ])
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(icon, size: 20, color: t.colorScheme.primary),
                    const SizedBox(width: 12),
                    Expanded(child: Text(text, style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant))),
                  ]),
                ),
              const SizedBox(height: 16),
              if (model.phase == Phase.waiting) ..._waiting(context) else if (c != null) ..._code(context, c) else ..._start(context),
            ]),
          ),
        ),
      ),
    );
  }

  List<Widget> _start(BuildContext context) => [
        if (model.error != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(model.error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
        FilledButton.icon(onPressed: model.phase == Phase.signingIn ? null : model.signIn, icon: const Icon(LucideIcons.logIn), label: const Text('Sign in with GitHub')),
        const SizedBox(height: 10),
        OutlinedButton(onPressed: model.useDemo, child: const Text('Look around with demo data')),
        const SizedBox(height: 16),
        Text('You need Cloud checks switched on in the desktop app first (Settings, Cloud checks). That is what puts the summary in your repository.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
      ];

  List<Widget> _code(BuildContext context, DeviceCode c) {
    final t = Theme.of(context);
    return [
      Text('Enter this code on GitHub', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 12),
      InkWell(
        onTap: () { Clipboard.setData(ClipboardData(text: c.userCode)); ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Code copied'))); },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 18), alignment: Alignment.center,
          decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(16)),
          child: Text(c.userCode, style: t.textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800, letterSpacing: 4, fontFeatures: const [FontFeature.tabularFigures()])),
        ),
      ),
      const SizedBox(height: 14),
      FilledButton.icon(onPressed: () { final u = Uri.tryParse(c.uri); if (u != null && u.scheme == 'https' && u.host == 'github.com') launchUrl(u, mode: LaunchMode.externalApplication); }, icon: const Icon(LucideIcons.externalLink), label: const Text('Open GitHub')),
      const SizedBox(height: 10),
      Row(children: [
        const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
        const SizedBox(width: 12),
        Expanded(child: Text('Waiting for you to approve. You can also approve it from the GitHub app on another phone.', style: t.textTheme.bodySmall)),
      ]),
      TextButton(onPressed: model.cancelSignIn, child: const Text('Cancel')),
    ];
  }

  List<Widget> _waiting(BuildContext context) {
    final t = Theme.of(context);
    return [
      Text('Signed in as ${model.login ?? ''}', style: t.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      Text('No summary yet in ${model.login ?? 'your'}/$repoName. It appears after the next cloud check (they run twice a day). To get it now, open the repository on GitHub, Actions, run the check by hand.',
          style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      if (model.error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(model.error!, style: TextStyle(color: t.colorScheme.error))),
      const SizedBox(height: 16),
      FilledButton.icon(onPressed: model.refreshing ? null : model.refresh, icon: const Icon(LucideIcons.refreshCw), label: Text(model.refreshing ? 'Checking' : 'Check again')),
      const SizedBox(height: 8),
      TextButton(onPressed: model.signOut, child: const Text('Sign out')),
    ];
  }
}

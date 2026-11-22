import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../model.dart';
import 'intro.dart' show BrandMark;
import '../source.dart' show DeviceCode, repoName;
import 'cloud_setup_screens.dart' show CloudSetupWizard;   // setup from the phone

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
                (LucideIcons.lock, 'Your portal password never reaches the phone. It only reads a small summary file from your own private GitHub repository.'),
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
        Text('Your deadlines, attendance, exams, results and timetable are read from your desktop app or your own private GitHub repository, so they open in a second, and reminders come from there too. The phone only reads: nothing here can change anything on the portal.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
        const SizedBox(height: 12),
        ..._cloudOptions(context),
        TextButton(onPressed: model.useDemo, child: const Text('Look around with demo data')),
      ];

  /// The ways to use the GitHub cloud checks: a read-only token (recommended), setting them up from the phone, or a GitHub code.
  List<Widget> _cloudOptions(BuildContext context) => [
        // the safest way in is the default: a token that can only read the one repository
        FilledButton.icon(
          onPressed: model.phase == Phase.signingIn ? null : () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => TokenSignInPage(model: model))),
          icon: const Icon(LucideIcons.shieldCheck), label: const Text('Sign in (read-only, recommended)'),
        ),
        const SizedBox(height: 10),
        // new here, or no PC: the phone sets up the checks itself (lib/screens/cloud_setup_screens.dart)
        OutlinedButton.icon(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => CloudSetupWizard(model: model))),
          icon: const Icon(LucideIcons.smartphone), label: const Text('Set up from this phone'),
        ),
        const SizedBox(height: 4),
        TextButton(onPressed: model.phase == Phase.signingIn ? null : model.signIn, child: const Text('Sign in with a GitHub code instead')),
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
      Text(model.cloudFirstCheck
              ? 'Your first check is running on GitHub. It takes about three minutes. Your deadlines appear here when it is done; you can close the app meanwhile.'
              : 'No summary yet in ${model.login ?? 'your'}/$repoName. It appears after the next cloud check (they run twice a day). To get it now, open the repository on GitHub, Actions, run the check by hand.',
          style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant)),
      if (model.error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(model.error!, style: TextStyle(color: t.colorScheme.error))),
      const SizedBox(height: 16),
      FilledButton.icon(onPressed: model.refreshing ? null : model.refresh, icon: const Icon(LucideIcons.refreshCw), label: Text(model.refreshing ? 'Checking' : (model.cloudFirstCheck ? 'Check now' : 'Check again'))),
      const SizedBox(height: 8),
      TextButton(onPressed: model.signOut, child: const Text('Sign out')),
    ];
  }
}


/// The tighter way to sign in: a token that can read one repository and nothing else. The steps are on the screen, and the
/// GitHub page opens with the name, description, permission and expiry already filled in.
class TokenSignInPage extends StatefulWidget {
  const TokenSignInPage({super.key, required this.model});
  final AppModel model;
  @override
  State<TokenSignInPage> createState() => _TokenSignInState();
}

class _TokenSignInState extends State<TokenSignInPage> {
  final field = TextEditingController();
  bool show = false;

  static final createUrl = Uri.parse('https://github.com/settings/personal-access-tokens/new'
      '?name=Assignment+Monitor+phone&description=Read-only+access+for+the+Assignment+Monitor+phone+app&expires_in=365&contents=read');

  @override
  void initState() { super.initState(); widget.model.addListener(_changed); }

  @override
  void dispose() { widget.model.removeListener(_changed); field.dispose(); super.dispose(); }

  void _changed() {
    if (!mounted) return;
    setState(() {});
    // signed in (or waiting for the first summary): the app's own screens take over
    if (widget.model.phase == Phase.ready || widget.model.phase == Phase.waiting) Navigator.of(context).popUntil((r) => r.isFirst);
  }

  Widget _step(BuildContext context, int n, String text) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(width: 26, height: 26, alignment: Alignment.center, decoration: BoxDecoration(color: Theme.of(context).colorScheme.primaryContainer, shape: BoxShape.circle),
              child: Text('$n', style: TextStyle(fontWeight: FontWeight.w800, color: Theme.of(context).colorScheme.onPrimaryContainer))),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.4))),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context), m = widget.model;
    final busy = m.phase == Phase.signingIn;
    return Scaffold(
      appBar: AppBar(title: const Text('Read-only token', style: TextStyle(fontWeight: FontWeight.w700))),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text('GitHub\'s normal sign-in gives the app access to all your repositories, even though it only reads one file. A fine-grained token can be limited to that one repository, read-only.',
              style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant, height: 1.4)),
          const SizedBox(height: 18),
          _step(context, 1, 'Open the GitHub page below. The name, a one-year expiry and the Contents read-only permission are already filled in.'),
          _step(context, 2, 'Under Repository access choose "Only select repositories", then pick assignment-monitor-cloud.'),
          _step(context, 3, 'Create the token, copy it, and paste it here.'),
          const SizedBox(height: 4),
          OutlinedButton.icon(
            onPressed: () => launchUrl(createUrl, mode: LaunchMode.externalApplication),
            icon: const Icon(LucideIcons.externalLink, size: 18), label: const Text('Open GitHub token page'),
          ),
          const SizedBox(height: 18),
          TextField(
            controller: field, obscureText: !show, enableSuggestions: false, autocorrect: false, enabled: !busy,
            decoration: InputDecoration(
              labelText: 'Token', hintText: 'github_pat_...', border: const OutlineInputBorder(),
              suffixIcon: IconButton(tooltip: show ? 'Hide' : 'Show', icon: Icon(show ? LucideIcons.eyeOff : LucideIcons.eye, size: 20), onPressed: () => setState(() => show = !show)),
            ),
          ),
          const SizedBox(height: 6),
          Align(alignment: Alignment.centerLeft, child: TextButton.icon(
            onPressed: busy ? null : () async { final d = await Clipboard.getData('text/plain'); if (d?.text != null) setState(() => field.text = d!.text!.trim()); },
            icon: const Icon(LucideIcons.clipboardPaste, size: 18), label: const Text('Paste'),
          )),
          if (m.error != null) Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(m.error!, style: TextStyle(color: t.colorScheme.error))),
          FilledButton.icon(
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
            onPressed: busy ? null : () => m.signInWithToken(field.text),
            icon: busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(LucideIcons.logIn, size: 20),
            label: Text(busy ? 'Checking' : 'Sign in'),
          ),
          const SizedBox(height: 14),
          Text('The token is kept in this phone\'s secure storage and deleted when you sign out. The app never shows or logs it.',
              style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        ]),
      ),
    );
  }
}

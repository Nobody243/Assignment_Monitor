import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show Clipboard, ClipboardData;
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:url_launcher/url_launcher.dart';

import '../cloud_setup.dart';
import '../logic.dart' show agoLabel;
import '../model.dart';
import '../portal.dart' show PortalCredentials;
import '../source.dart' show DeviceCode, GithubAuth, SourceError, repoName;
import '../theme.dart' show Status;

/// Test hooks: how the screens reach GitHub. The defaults talk to the real one.
CloudClient Function(String token) cloudClientFactory = (token) => CloudClient(token);
GithubAuth Function() cloudAuthFactory = () => GithubAuth();

// The portal password is typed here and goes straight into CloudSetup (sealed there). It lives only in the text field's
// controller, which is cleared when the setup works and when the screen goes away. Nothing in this file stores or logs it.

// ================================================================================================ the wizard
enum _Page { intro, github, portal, progress }

/// "Set up from this phone": the whole Cloud checks setup, from the phone. Steps: what will happen, GitHub sign-in (device
/// code), the portal login, then the progress of the setup. When it works the app is signed in and waits for the first check.
class CloudSetupWizard extends StatefulWidget {
  const CloudSetupWizard({super.key, required this.model, this.prefill});
  final AppModel model;

  /// The portal login already saved on the phone (Full app): used instead of asking for it a second time.
  final PortalCredentials? prefill;
  @override
  State<CloudSetupWizard> createState() => _WizardState();
}

class _WizardState extends State<CloudSetupWizard> {
  _Page page = _Page.intro;
  final enrollment = TextEditingController();
  final password = TextEditingController();
  String campus = '1';
  bool show = false, cancelled = false, consent = false;
  DeviceCode? code;
  String? token, login, error, enrollmentError, passwordError;
  final done = <CloudStep>{};
  CloudStep? running;
  CloudError? failure;

  @override
  void initState() {
    super.initState();
    final p = widget.prefill;
    if (p != null) { enrollment.text = p.enrollment; password.text = p.password; campus = p.instituteId; }
  }

  @override
  void dispose() {
    cancelled = true;
    password.clear();       // the password never outlives this screen
    password.dispose();
    enrollment.dispose();
    super.dispose();
  }

  // ---- step 2: GitHub
  Future<void> _github() async {
    setState(() { page = _Page.github; error = null; code = null; cancelled = false; });
    try {
      final auth = cloudAuthFactory();
      final c = await auth.start(scope: 'repo workflow');
      if (!mounted) return;
      setState(() => code = c);
      final t = await auth.approved(c, cancelled: () => cancelled);
      final l = await auth.login(t);
      if (!mounted) return;
      setState(() { token = t; login = l; code = null; page = _Page.portal; });
    } on SourceError catch (e) {
      if (mounted && !cancelled) setState(() { error = e.message; code = null; });
    } catch (_) {
      if (mounted && !cancelled) setState(() { error = 'Could not reach GitHub. Check the connection and try again.'; code = null; });
    }
  }

  // ---- step 3: the portal login
  void _portalNext() {
    final e = enrollmentProblem(enrollment.text), p = passwordProblem(password.text);
    setState(() { enrollmentError = e; passwordError = p; });
    if (e == null && p == null) unawaited(_run());
  }

  // ---- step 4: the setup
  Future<void> _run() async {
    setState(() { page = _Page.progress; failure = null; done.clear(); running = null; });
    final m = widget.model;
    try {
      final r = await CloudSetup(cloudClientFactory(token!)).run(
        enrollment: enrollment.text, password: password.text, campusId: campus,
        progress: (s, d) { if (mounted) setState(() { if (d) { done.add(s); running = null; } else { running = s; } }); },
      );
      password.clear();       // sealed and sent; nothing to keep
      await m.adoptSession(token!, r.login);
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } on CloudError catch (e) {
      if (mounted) setState(() { failure = e; running = null; });
    } catch (_) {
      if (mounted) setState(() { failure = CloudError('Something went wrong while setting up. Try again.'); running = null; });
    }
  }

  void _back() {
    if (page == _Page.github) { cancelled = true; setState(() { page = _Page.intro; code = null; error = null; }); }
    else if (page == _Page.portal) { setState(() => page = _Page.intro); }
    else if (page == _Page.progress && failure != null) { setState(() => page = _Page.portal); }
  }

  @override
  Widget build(BuildContext context) {
    final inProgress = page == _Page.progress && failure == null;
    return PopScope(
      canPop: page == _Page.intro,
      onPopInvokedWithResult: (didPop, _) { if (!didPop && !inProgress) _back(); },
      child: Scaffold(
        appBar: AppBar(
          title: Text('Set up from this phone', style: const TextStyle(fontWeight: FontWeight.w700)),
          leading: inProgress ? const SizedBox.shrink() : null,
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: ListView(padding: const EdgeInsets.all(20), children: switch (page) {
                _Page.intro => _intro(context),
                _Page.github => _githubPage(context),
                _Page.portal => _portal(context),
                _Page.progress => _progress(context),
              }),
            ),
          ),
        ),
      ),
    );
  }

  Widget _stepHead(BuildContext context, int n, String title) {
    final t = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(children: [
        Container(width: 28, height: 28, alignment: Alignment.center, decoration: BoxDecoration(color: t.colorScheme.primaryContainer, shape: BoxShape.circle),
            child: Text('$n', style: TextStyle(fontWeight: FontWeight.w800, color: t.colorScheme.onPrimaryContainer))),
        const SizedBox(width: 12),
        Expanded(child: Text(title, style: t.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800))),
      ]),
    );
  }

  Widget _point(BuildContext context, IconData icon, String text) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.4))),
        ]),
      );

  // ---- 1: what happens
  List<Widget> _intro(BuildContext context) {
    final t = Theme.of(context);
    return [
      _stepHead(context, 1, 'What this does'),
      _point(context, LucideIcons.cloud, 'GitHub checks the university portal for you, twice a day, on its own machines. The desktop app is not needed.'),
      _point(context, LucideIcons.folderGit2, 'It runs in a private repository in your own GitHub account (assignment-monitor-cloud). This app reads the result from there.'),
      _point(context, LucideIcons.keyRound, 'You will sign in to GitHub with a code, then type your portal login once. The login is encrypted on this phone and sent to GitHub\'s secret store in your own repository. It is never sent to us, and this phone does not keep it.'),
      _point(context, LucideIcons.shieldAlert, 'GitHub\'s approval screen will say this app wants "full control of private repositories" and to "update GitHub Action workflows". That is GitHub\'s wording for the two permissions it needs to create the repository and its schedule, and GitHub cannot limit it to one repository. The app only ever touches assignment-monitor-cloud, the sign-in is kept in this phone\'s secure storage, and you can remove the access any time in GitHub, Settings, Applications.'),
      _point(context, LucideIcons.clock, 'It takes about a minute, and the first check about three more.'),
      const SizedBox(height: 4),
      CheckboxListTile(
        contentPadding: EdgeInsets.zero, controlAffinity: ListTileControlAffinity.leading, value: consent,
        onChanged: (v) => setState(() => consent = v ?? false),
        title: Text('I understand. My portal login goes, encrypted, into the secrets of my own private GitHub repository.', style: t.textTheme.bodyMedium?.copyWith(height: 1.35)),
      ),
      const SizedBox(height: 12),
      FilledButton.icon(
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        onPressed: consent ? _github : null,
        icon: const Icon(LucideIcons.arrowRight, size: 20), label: const Text('Continue'),
      ),
    ];
  }

  // ---- 2: GitHub
  List<Widget> _githubPage(BuildContext context) {
    final t = Theme.of(context);
    final c = code;
    return [
      _stepHead(context, 2, 'Sign in to GitHub'),
      if (error != null) ...[
        Text(error!, style: TextStyle(color: t.colorScheme.error, height: 1.4)),
        const SizedBox(height: 14),
        FilledButton.icon(style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)), onPressed: _github, icon: const Icon(LucideIcons.refreshCw, size: 20), label: const Text('Try again')),
      ] else if (c == null) ...[
        const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
        const Center(child: Text('Asking GitHub for a code')),
      ] else ...[
        Text('Enter this code on GitHub. Its screen will sound alarming ("full control of private repositories"): that is GitHub\'s standard wording for the "repo" and "workflow" permissions the phone needs to create your private repository and its schedule. Approve both.', style: t.textTheme.bodyMedium?.copyWith(height: 1.4)),
        const SizedBox(height: 14),
        InkWell(
          onTap: () { Clipboard.setData(ClipboardData(text: c.userCode)); ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Code copied'))); },
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 18), alignment: Alignment.center,
            decoration: BoxDecoration(color: t.colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(16)),
            child: FittedBox(fit: BoxFit.scaleDown, child: Text(c.userCode, style: t.textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800, letterSpacing: 4, fontFeatures: const [FontFeature.tabularFigures()]))),
          ),
        ),
        const SizedBox(height: 14),
        FilledButton.icon(
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          onPressed: () { final u = Uri.tryParse(c.uri); if (u != null && u.scheme == 'https' && u.host == 'github.com') launchUrl(u, mode: LaunchMode.externalApplication); },
          icon: const Icon(LucideIcons.externalLink, size: 20), label: const Text('Open GitHub'),
        ),
        const SizedBox(height: 12),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
          const SizedBox(width: 12),
          Expanded(child: Text('Waiting for you to approve. You can also approve it from the GitHub app on another phone.', style: t.textTheme.bodySmall)),
        ]),
      ],
      TextButton(onPressed: _back, child: const Text('Cancel')),
    ];
  }

  // ---- 3: portal login
  List<Widget> _portal(BuildContext context) {
    final t = Theme.of(context);
    return [
      _stepHead(context, 3, 'Your portal login'),
      Text('Signed in to GitHub as ${login ?? ''}. Now the login you use on the Bahria portal. It is encrypted here and sent to your own repository\'s secrets. It is not stored on this phone.',
          style: t.textTheme.bodyMedium?.copyWith(height: 1.4)),
      const SizedBox(height: 16),
      TextField(
        controller: enrollment, keyboardType: TextInputType.number, autocorrect: false, enableSuggestions: false, textInputAction: TextInputAction.next,
        decoration: InputDecoration(labelText: 'Enrollment number', hintText: '01-123456-001', errorText: enrollmentError, errorMaxLines: 3, border: const OutlineInputBorder()),
      ),
      const SizedBox(height: 14),
      TextField(
        controller: password, obscureText: !show, autocorrect: false, enableSuggestions: false, textInputAction: TextInputAction.done,
        onSubmitted: (_) => _portalNext(),
        decoration: InputDecoration(
          labelText: 'Portal password', errorText: passwordError, errorMaxLines: 3, border: const OutlineInputBorder(),
          suffixIcon: IconButton(tooltip: show ? 'Hide password' : 'Show password', icon: Icon(show ? LucideIcons.eyeOff : LucideIcons.eye, size: 20), onPressed: () => setState(() => show = !show)),
        ),
      ),
      const SizedBox(height: 14),
      DropdownButtonFormField<String>(
        initialValue: campus, isExpanded: true, itemHeight: null,
        decoration: const InputDecoration(labelText: 'Campus', border: OutlineInputBorder()),
        items: [for (final (name, id) in cloudCampuses) DropdownMenuItem(value: id, child: Text(name))],
        onChanged: (v) => setState(() => campus = v ?? campus),
      ),
      const SizedBox(height: 20),
      FilledButton.icon(
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        onPressed: _portalNext, icon: const Icon(LucideIcons.cloudUpload, size: 20), label: const Text('Set up Cloud checks'),
      ),
      TextButton(onPressed: _back, child: const Text('Back')),
    ];
  }

  // ---- 4: progress
  List<Widget> _progress(BuildContext context) {
    final t = Theme.of(context);
    const labels = {
      CloudStep.repo: 'Your private repository',
      CloudStep.workflow: 'The schedule (workflow)',
      CloudStep.secrets: 'Your login, encrypted',
      CloudStep.check: 'The first check',
    };
    return [
      _stepHead(context, 4, failure == null ? 'Setting up' : 'Setup stopped'),
      for (final s in CloudStep.values)
        Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Row(children: [
            SizedBox(width: 24, height: 24, child: done.contains(s)
                ? Icon(LucideIcons.circleCheck, size: 22, color: Status.good(t.brightness))
                : failure?.step == s
                    ? Icon(LucideIcons.circleX, size: 22, color: t.colorScheme.error)
                    : running == s ? const Padding(padding: EdgeInsets.all(3), child: CircularProgressIndicator(strokeWidth: 2)) : Icon(LucideIcons.circle, size: 22, color: t.colorScheme.outline)),
            const SizedBox(width: 12),
            Expanded(child: Text(labels[s]!, style: t.textTheme.bodyLarge?.copyWith(fontWeight: failure?.step == s ? FontWeight.w700 : null))),
          ]),
        ),
      if (failure != null) ...[
        const SizedBox(height: 6),
        Text(failure!.message, key: const ValueKey('cloud-failure'), style: TextStyle(color: t.colorScheme.error, height: 1.4)),
        const SizedBox(height: 16),
        FilledButton.icon(style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)), onPressed: _run, icon: const Icon(LucideIcons.refreshCw, size: 20), label: const Text('Retry')),
        if (failure!.status == 401) ...[
          const SizedBox(height: 8),
          OutlinedButton(onPressed: _github, child: const Text('Sign in to GitHub again')),
        ],
        TextButton(onPressed: _back, child: const Text('Change my login')),
      ] else
        Text('This takes about a minute. You can leave the app; the setup continues only while it is open.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
    ];
  }
}

// ================================================================================================ Settings > Cloud checks
/// The Cloud checks page in Settings: status, run a check now, change the portal login, turn off.
class CloudSettingsPage extends StatefulWidget {
  const CloudSettingsPage({super.key, required this.model});
  final AppModel model;
  @override
  State<CloudSettingsPage> createState() => _CloudSettingsState();
}

class _CloudSettingsState extends State<CloudSettingsPage> {
  CloudStatus? status;
  String? problem;
  bool loading = true, busy = false;

  AppModel get m => widget.model;
  String get repo => '${m.login ?? ''}/$repoName';

  @override
  void initState() { super.initState(); unawaited(_load()); }

  Future<CloudClient?> _client() async {
    final t = await m.cloudToken();
    return t == null ? null : cloudClientFactory(t);
  }

  Future<void> _load() async {
    setState(() { loading = true; problem = null; });
    try {
      final c = await _client();
      if (c == null || m.login == null) throw CloudError('Not signed in.');
      final s = await c.status(m.login!);
      if (mounted) setState(() { status = s; loading = false; });
    } on CloudError catch (e) {
      // a read-only sign-in cannot see the workflow: that is "not set up from this phone", not a failure
      if (mounted) setState(() { status = e.status == 404 || e.status == 403 ? CloudStatus(repo: repo, enabled: false) : null; problem = e.status == 404 || e.status == 403 ? null : e.message; loading = false; });
    } catch (_) {
      if (mounted) setState(() { problem = 'Could not reach GitHub.'; loading = false; });
    }
  }

  void _say(String text) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text))); }

  Future<void> _runNow() async {
    setState(() => busy = true);
    try {
      final c = await _client();
      await CloudSetup(c!).runNow(repo);
      _say('Check started. It takes about three minutes; the app updates when it is done.');
      await Future<void>.delayed(const Duration(seconds: 3));
      if (mounted) await _load();
    } on CloudError catch (e) {
      _say(e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _changeLogin() async {
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => ChangePortalLoginPage(model: m)));
    if (ok == true) _say('Portal login updated. It is used from the next check.');
  }

  Future<void> _turnOff() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Turn off Cloud checks?'),
        content: const Text('This deletes the secrets (your portal login) and the schedule from your repository. Checks stop. The repository itself stays on GitHub; you can delete it there. This app keeps showing the last summary.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Turn off')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => busy = true);
    try {
      final c = await _client();
      await CloudSetup(c!).teardown(repo);
      _say('Cloud checks are off. The repository is still on GitHub.');
      if (mounted) await _load();
    } on CloudError catch (e) {
      _say(e.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  String _runText(CloudRun r) {
    final ago = agoLabel(DateTime.now().difference(r.when));
    if (r.running) return 'Running now · started $ago';
    return r.ok ? 'Last check worked · $ago' : 'Last check failed (${r.conclusion ?? 'stopped'}) · $ago';
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final s = status;
    return ListView(padding: const EdgeInsets.all(16), children: [
      if (loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
      if (!loading && problem != null) ...[
        Text(problem!, style: TextStyle(color: t.colorScheme.error)),
        const SizedBox(height: 10),
        OutlinedButton.icon(onPressed: _load, icon: const Icon(LucideIcons.refreshCw, size: 18), label: const Text('Try again')),
      ],
      if (!loading && s != null && s.enabled) ...[
        ListTile(
          contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.cloud),
          title: const Text('Cloud checks are on'),
          subtitle: Text(s.run == null ? 'No check has run yet.' : _runText(s.run!)),
        ),
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.folderGit2), title: const Text('Repository'), subtitle: Text(s.repo)),
        const Divider(height: 24),
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.play), title: const Text('Run a check now'), subtitle: const Text('Reads the portal on GitHub and updates this app.'), enabled: !busy, onTap: _runNow),
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(LucideIcons.keyRound), title: const Text('Change portal login'), subtitle: const Text('Type it again; it replaces the encrypted copy on GitHub.'), enabled: !busy, onTap: _changeLogin),
        ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.power, color: Status.bad(t.brightness)), title: Text('Turn off', style: TextStyle(color: Status.bad(t.brightness))), subtitle: const Text('Removes the secrets and the schedule from your repository.'), enabled: !busy, onTap: _turnOff),
      ],
      if (!loading && s != null && !s.enabled) ...[
        const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(LucideIcons.cloudOff), title: Text('Not set up from this phone'), subtitle: Text('If the desktop app runs your checks, nothing is needed here. With only a phone, set it up now.')),
        const SizedBox(height: 8),
        FilledButton.icon(
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          onPressed: () async { await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => CloudSetupWizard(model: m))); if (mounted) await _load(); },
          icon: const Icon(LucideIcons.cloudUpload, size: 20), label: const Text('Set up Cloud checks'),
        ),
      ],
      if (busy) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()),
    ]);
  }
}

/// Type the portal login again; only the two secrets are replaced. The password is cleared as soon as it has been sent.
class ChangePortalLoginPage extends StatefulWidget {
  const ChangePortalLoginPage({super.key, required this.model});
  final AppModel model;
  @override
  State<ChangePortalLoginPage> createState() => _ChangeLoginState();
}

class _ChangeLoginState extends State<ChangePortalLoginPage> {
  final enrollment = TextEditingController();
  final password = TextEditingController();
  bool show = false, busy = false;
  String? enrollmentError, passwordError, error;

  @override
  void dispose() { password.clear(); password.dispose(); enrollment.dispose(); super.dispose(); }

  Future<void> _save() async {
    final e = enrollmentProblem(enrollment.text), p = passwordProblem(password.text);
    setState(() { enrollmentError = e; passwordError = p; error = null; });
    if (e != null || p != null) return;
    setState(() => busy = true);
    try {
      final token = await widget.model.cloudToken();
      await CloudSetup(cloudClientFactory(token!)).changeLogin(repo: '${widget.model.login}/$repoName', enrollment: enrollment.text, password: password.text);
      password.clear();
      if (mounted) Navigator.of(context).pop(true);
    } on CloudError catch (e) {
      if (mounted) setState(() { error = e.message; busy = false; });
    } catch (_) {
      if (mounted) setState(() { error = 'Could not reach GitHub.'; busy = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Change portal login', style: TextStyle(fontWeight: FontWeight.w700))),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text('The new login is encrypted on this phone and replaces the old one in your repository\'s secrets. This phone does not keep it.', style: t.textTheme.bodyMedium?.copyWith(height: 1.4)),
          const SizedBox(height: 16),
          TextField(
            controller: enrollment, enabled: !busy, keyboardType: TextInputType.number, autocorrect: false, enableSuggestions: false,
            decoration: InputDecoration(labelText: 'Enrollment number', hintText: '01-123456-001', errorText: enrollmentError, errorMaxLines: 3, border: const OutlineInputBorder()),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: password, enabled: !busy, obscureText: !show, autocorrect: false, enableSuggestions: false,
            decoration: InputDecoration(
              labelText: 'Portal password', errorText: passwordError, errorMaxLines: 3, border: const OutlineInputBorder(),
              suffixIcon: IconButton(tooltip: show ? 'Hide password' : 'Show password', icon: Icon(show ? LucideIcons.eyeOff : LucideIcons.eye, size: 20), onPressed: () => setState(() => show = !show)),
            ),
          ),
          if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, key: const ValueKey('change-login-error'), style: TextStyle(color: t.colorScheme.error))),
          const SizedBox(height: 18),
          FilledButton.icon(
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
            onPressed: busy ? null : _save,
            icon: busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(LucideIcons.save, size: 20),
            label: Text(busy ? 'Saving' : 'Save'),
          ),
        ]),
      ),
    );
  }
}

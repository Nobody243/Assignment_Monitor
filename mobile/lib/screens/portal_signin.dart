import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../model.dart';
import '../portal.dart';
import 'signin.dart' show TokenSignInPage;

/// Standalone sign-in: the phone talks to the university portal itself. One short form, one button. When the portal says no,
/// the screen says why in a sentence and, where a retry cannot help (a captcha, a changed page), offers the other way in.
class PortalSignInPage extends StatefulWidget {
  const PortalSignInPage({super.key, required this.model});
  final AppModel model;
  @override
  State<PortalSignInPage> createState() => _PortalSignInState();
}

class _PortalSignInState extends State<PortalSignInPage> {
  final enrollment = TextEditingController(), password = TextEditingController();
  String institute = campuses.first.$2;
  bool show = false, busy = false;
  SignInResult? failed;
  int? connected;

  @override
  void dispose() { enrollment.dispose(); password.dispose(); super.dispose(); }

  Future<void> _go() async {
    setState(() { busy = true; failed = null; });
    final r = await widget.model.connectPortal(PortalCredentials(enrollment.text, password.text, institute));
    if (!mounted) return;
    setState(() { busy = false; failed = r.result.ok ? null : r.result; connected = r.result.ok ? r.courses : null; });
    if (r.result.ok) {
      widget.model.beginPortalMode();
      if (mounted) Navigator.of(context).popUntil((x) => x.isFirst);   // the app's own screens take over
    }
  }

  bool get _retryWontHelp => failed?.problem == SignInProblem.blocked || failed?.problem == SignInProblem.unexpected;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('University sign-in', style: TextStyle(fontWeight: FontWeight.w700))),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text('Use the same enrollment number and password as the university portal. They stay in this phone\'s secure storage and are sent only to the portal.',
              style: t.textTheme.bodyMedium?.copyWith(color: t.colorScheme.onSurfaceVariant, height: 1.4)),
          const SizedBox(height: 18),
          TextField(
            controller: enrollment, enabled: !busy, keyboardType: TextInputType.text, autocorrect: false, enableSuggestions: false,
            textInputAction: TextInputAction.next, autofillHints: const [AutofillHints.username],
            decoration: const InputDecoration(labelText: 'Enrollment number', hintText: '01-135232-062', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: password, enabled: !busy, obscureText: !show, autocorrect: false, enableSuggestions: false,
            autofillHints: const [AutofillHints.password],
            decoration: InputDecoration(
              labelText: 'Password', border: const OutlineInputBorder(),
              suffixIcon: IconButton(tooltip: show ? 'Hide' : 'Show', icon: Icon(show ? LucideIcons.eyeOff : LucideIcons.eye, size: 20), onPressed: () => setState(() => show = !show)),
            ),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: institute, isExpanded: true,
            decoration: const InputDecoration(labelText: 'Campus', border: OutlineInputBorder()),
            items: [for (final c in campuses) DropdownMenuItem(value: c.$2, child: Text(c.$1, overflow: TextOverflow.ellipsis))],
            onChanged: busy ? null : (v) => setState(() => institute = v ?? institute),
          ),
          const SizedBox(height: 18),
          if (failed != null) ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: t.colorScheme.errorContainer, borderRadius: BorderRadius.circular(16)),
              child: Text(failed!.message, style: TextStyle(color: t.colorScheme.onErrorContainer, height: 1.35)),
            ),
            const SizedBox(height: 12),
          ],
          if (connected != null)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: t.colorScheme.primaryContainer, borderRadius: BorderRadius.circular(16)),
              child: Row(children: [
                Icon(LucideIcons.circleCheck, color: t.colorScheme.onPrimaryContainer),
                const SizedBox(width: 12),
                Expanded(child: Text(connected == 0 ? 'Signed in.' : 'Signed in. ${connected!} course${connected == 1 ? '' : 's'} found.', style: TextStyle(fontWeight: FontWeight.w700, color: t.colorScheme.onPrimaryContainer))),
              ]),
            )
          else
            FilledButton.icon(
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
              onPressed: busy ? null : _go,
              icon: busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(LucideIcons.logIn, size: 20),
              label: Text(busy ? 'Signing in. This can take a minute' : 'Sign in'),
            ),
          if (_retryWontHelp) ...[
            const SizedBox(height: 10),
            // the other way in, so nobody is stuck: the same data through their own GitHub cloud checks
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).pushReplacement(MaterialPageRoute<void>(builder: (_) => TokenSignInPage(model: widget.model))),
              icon: const Icon(LucideIcons.cloud, size: 18), label: const Text('Use my GitHub cloud checks instead'),
            ),
          ],
        ]),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../model.dart';
import 'intro.dart';

/// Shown over everything while the app is locked. It asks the phone to verify as soon as it appears, and again from the
/// button if that was cancelled.
class LockScreen extends StatefulWidget {
  const LockScreen({super.key, required this.model});
  final AppModel model;
  @override
  State<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends State<LockScreen> {
  bool asking = false, failed = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _ask());
  }

  Future<void> _ask() async {
    if (asking || !mounted) return;
    setState(() { asking = true; failed = false; });
    final ok = await widget.model.unlock();
    if (mounted) setState(() { asking = false; failed = !ok; });
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const BrandMark(size: 88),
              const SizedBox(height: 22),
              Text('Locked', style: t.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              Text(failed ? 'That did not unlock it. Try again.' : 'Your grades and deadlines are hidden until you unlock.', textAlign: TextAlign.center, style: t.textTheme.bodyMedium?.copyWith(color: failed ? t.colorScheme.error : t.colorScheme.onSurfaceVariant)),
              const SizedBox(height: 24),
              FilledButton.icon(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 52), padding: const EdgeInsets.symmetric(horizontal: 28)),
                onPressed: asking ? null : _ask,
                icon: const Icon(LucideIcons.lockOpen, size: 20),
                label: const Text('Unlock'),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

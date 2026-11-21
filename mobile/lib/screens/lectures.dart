import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:share_plus/share_plus.dart';

import '../data.dart';
import '../model.dart';
import '../portal_files.dart';
import 'widgets.dart';

/// Runs a portal file job behind a small "working" dialog, and says how it went. Used by Lectures and by the assignment
/// sheet, so a download, an upload and a delete all look and fail the same way.
Future<T?> runFileJob<T>(BuildContext context, String working, Future<T> Function() job) async {
  final messenger = ScaffoldMessenger.of(context);
  final nav = Navigator.of(context, rootNavigator: true);
  showDialog<void>(
    context: context, barrierDismissible: false,
    builder: (_) => PopScope(canPop: false, child: AlertDialog(
      content: Row(children: [
        const SizedBox(width: 26, height: 26, child: CircularProgressIndicator(strokeWidth: 3)),
        const SizedBox(width: 18),
        Expanded(child: Text(working)),
      ]),
    )),
  );
  try {
    return await job();
  } on FileProblem catch (e) {
    messenger.showSnackBar(SnackBar(content: Text(e.message), duration: const Duration(seconds: 6)));
    return null;
  } catch (e) {
    // the reason in a few words (no page text, no links), so a failure can be told apart from a lost connection
    final why = e is StateError ? e.message : e is ArgumentError ? '${e.message}' : e.runtimeType.toString();
    messenger.showSnackBar(SnackBar(content: Text('That did not work ($why). Try again.'), duration: const Duration(seconds: 7)));
    return null;
  } finally {
    nav.pop();
  }
}

/// Hands a saved file to Android's share sheet (open it in a viewer, save it to Drive or Files, send it).
Future<void> openSavedFile(SavedFile f) => SharePlus.instance.share(ShareParams(files: [XFile(f.path)], subject: f.name));

class LecturesScreen extends StatelessWidget {
  const LecturesScreen({super.key, required this.summary, required this.model});
  final Summary summary;
  final AppModel model;

  @override
  Widget build(BuildContext context) {
    if (!model.portalMode) {
      return EmptyState(
        icon: LucideIcons.bookOpen, title: model.demo ? 'Lectures are not in the demo' : 'Lectures need your university login',
        hint: model.demo
            ? 'Leave the demo and sign in with your university login, and the lecture notes and files of every course appear here to download.'
            : 'Open Settings, then University login. The lecture notes and files of every course then appear here to download.',
      );
    }
    final all = summary.lectures;
    if (all.isEmpty) {
      if (model.syncSkipped.contains('lectures')) {
        return const EmptyState(icon: LucideIcons.bookOpen, title: 'The lecture notes could not be read', hint: 'The portal did not give them back this time. Pull down to try again.');
      }
      return const EmptyState(icon: LucideIcons.bookOpen, title: 'No lecture notes yet', hint: 'They appear here when your teachers upload them to the portal. Pull down to check again.');
    }
    final byCourse = <String, List<Lecture>>{};
    for (final l in all) { byCourse.putIfAbsent(l.course, () => []).add(l); }
    final t = Theme.of(context);
    return ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
      for (final (i, e) in byCourse.entries.indexed)
        Reveal(index: i, child: Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Card(
            clipBehavior: Clip.antiAlias,
            child: ExpansionTile(
              shape: const Border(), collapsedShape: const Border(), initiallyExpanded: byCourse.length == 1,
              title: Text(e.key, style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('${e.value.length} ${e.value.length == 1 ? 'entry' : 'entries'}, ${e.value.fold<int>(0, (n, l) => n + l.files.length)} files',
                  style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
              children: [for (final l in e.value) _Week(lecture: l, model: model)],
            ),
          ),
        )),
    ]);
  }
}

class _Week extends StatelessWidget {
  const _Week({required this.lecture, required this.model});
  final Lecture lecture;
  final AppModel model;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context);
    final l = lecture;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l.kind == 'misc' ? l.title : 'Week ${l.week}: ${l.title}', style: t.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        if (l.files.isEmpty) Text('No files in this week.', style: t.textTheme.bodySmall?.copyWith(color: t.colorScheme.onSurfaceVariant)),
        for (final f in l.files)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), alignment: Alignment.centerLeft),
              icon: const Icon(LucideIcons.download, size: 18),
              label: Text(f.filename.isEmpty ? f.label : f.filename, maxLines: 1, overflow: TextOverflow.ellipsis),
              onPressed: () async {
                final saved = await runFileJob(context, 'Downloading ${f.filename.isEmpty ? f.label : f.filename}', () => model.withPortalFiles((files) =>
                    files.lectureFile(course: l.course, week: l.week, title: l.title, kind: l.kind, filename: f.filename, label: f.label)));
                if (saved != null) await openSavedFile(saved);
              },
            ),
          ),
      ]),
    );
  }
}

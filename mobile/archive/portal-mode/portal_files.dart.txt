import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'portal.dart';
import 'portal_parse.dart';
import 'portal_sync.dart';

/// Files to and from the university portal, on the phone: lecture notes and assignment briefs down, a submission up (and
/// deleted). The same flows as the desktop app (`lms_scraper.py`), done in the signed-in WebView. Links on the portal
/// expire daily, so a file is found again in the live page every time it is fetched; nothing keeps an old link.
class SavedFile {
  const SavedFile(this.path, this.name, this.bytes);
  final String path, name;
  final int bytes;
}

class FileProblem implements Exception {
  FileProblem(this.message);
  final String message;
  @override
  String toString() => message;
}

class SubmitOutcome {
  const SubmitOutcome({required this.ok, required this.message, this.deleted = false});
  final bool ok, deleted;
  final String message;
}

const _mime = {
  '.pdf': 'application/pdf', '.zip': 'application/zip', '.doc': 'application/msword',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.xls': 'application/vnd.ms-excel',
  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
};

class PortalFiles {
  PortalFiles(this.portal, this.folder, {this.pause = const Duration(milliseconds: 300)});
  final Portal portal;

  /// Where downloads go (the app's own storage, not shared with other apps).
  final Directory folder;
  final Duration pause;

  PortalBrowser get _b => portal.browser;

  // ------------------------------------------------------------------------------------------------ downloads

  /// One lecture (or miscellaneous) file. The course page is read again to find the file's current link, matched by file
  /// name, then link, then label, exactly as the desktop does.
  Future<SavedFile> lectureFile({required String course, required Object? week, required String title, required String kind,
      required String filename, required String label, int index = 0}) async {
    await portal.lmsPage(kind == 'misc' ? miscUrl : lecturesUrl);
    var html = await portal.selectCourse(course);
    Map<String, dynamic>? hit;
    // The list can still be filling in when the page has "loaded", so a miss is looked at again a few times before it is called
    // missing. Weeks and titles are compared loosely (case, spacing), and a file is found by its name, then by its position in
    // the week, then by its label when that is unique.
    for (var attempt = 0; attempt < 4 && hit == null; attempt++) {
      if (attempt > 0) { await Future<void>.delayed(pause * 6); html = await _b.html(); }
      hit = _findLectureFile(kind == 'misc' ? parseMisc(html, course) : parseLectures(html, course), week: week, title: title, filename: filename, label: label, index: index);
    }
    if (hit == null) throw FileProblem('That file is not listed on the portal right now (${safeName(course, 40)}). Pull down on Lectures and try again.');
    final sub = kind == 'misc' ? 'Miscellaneous' : 'Week ${'$week'.padLeft(2, '0')}';
    return _save(hit['href'] as String, [safeName(course), '$sub - ${safeName(title, 60)}'], filename.isNotEmpty ? filename : '');
  }

  static String _norm(Object? s) => '$s'.toLowerCase().replaceAll(RegExp(r'\s+'), ' ').trim();

  /// The file's current entry in the live list, or null. Public for testing.
  static Map<String, dynamic>? findForTest(List<Map<String, dynamic>> live, {required Object? week, required String title, required String filename, required String label, required int index}) =>
      _findLectureFile(live, week: week, title: title, filename: filename, label: label, index: index);

  static Map<String, dynamic>? _findLectureFile(List<Map<String, dynamic>> live,
      {required Object? week, required String title, required String filename, required String label, required int index}) {
    List<Map<String, dynamic>> filesOf(bool Function(Map<String, dynamic>) keep) =>
        [for (final x in live) if (keep(x)) for (final f in (x['files'] as List? ?? const [])) (f as Map).cast<String, dynamic>()];
    final sameWeek = _norm(week), sameTitle = _norm(title);
    // The week and title together are the safe identity: there a file is found by its name, then its label when that is unique, then
    // its position. If the portal has since renumbered a week (title alone) the same three apply; if it has edited a title (week
    // alone) only the exact file name is trusted, so a different week's file is never taken for this one.
    final tiers = <(List<Map<String, dynamic>>, bool)>[
      (filesOf((x) => _norm(x['week']) == sameWeek && _norm(x['title']) == sameTitle), true),
      (filesOf((x) => _norm(x['title']) == sameTitle), true),
      (filesOf((x) => _norm(x['week']) == sameWeek), false),
    ];
    for (final (pool, loose) in tiers) {
      if (pool.isEmpty) continue;
      if (filename.isNotEmpty) {
        final byName = pool.where((f) => _norm(f['filename']) == _norm(filename)).firstOrNull;
        if (byName != null) return byName;
      }
      if (!loose) continue;
      final byLabel = pool.where((f) => _norm(f['label']) == _norm(label)).toList();
      if (byLabel.length == 1) return byLabel.first;
      if (index >= 0 && index < pool.length) return pool[index];
      if (pool.length == 1) return pool.first;
    }
    return null;
  }

  /// An assignment's brief (or solution / your submission / the returned work), looked up in the live course table.
  Future<SavedFile> assignmentFile({required String course, required String id, required String kind, required String title, required Object? number}) async {
    final html = await _openCourse(course);
    final row = parseCourseTable(html, course).where((a) => a['id'] == id).firstOrNull;
    final f = (row?['files'] as Map?)?[kind] as Map?;
    if (f == null) throw FileProblem('That file is no longer on the portal.');
    final no = '$number'.trim();
    final sub = (RegExp(r'^\d+$').hasMatch(no) ? '${no.padLeft(2, '0')} - ' : '') + safeName(title, 60);
    return _save(f['href'] as String, [safeName(course), 'Assignments', sub], '${f['filename'] ?? ''}'.isNotEmpty ? '${f['filename']}' : '${safeName(title, 60)} - $kind');
  }

  Future<SavedFile> _save(String href, List<String> parts, String name) async {
    final url = Uri.parse('$lmsBase/Student/').resolve(href).toString();
    final got = await _b.fetchFile(url);
    final type = got.contentType.toLowerCase();
    if (got.status >= 400 || (type.contains('text/html') && got.bytes.length < 200000)) {
      throw FileProblem('The portal did not hand the file over (${got.status == 200 ? 'it sent a web page' : 'error ${got.status}'}). Try again.');
    }
    var fileName = name;
    final m = RegExp(r'''filename\*?=(?:UTF-8'')?"?([^";]+)''', caseSensitive: false).firstMatch(got.disposition);
    if (m != null && m.group(1)!.contains('.')) {
      final served = safeName(Uri.decodeComponent(m.group(1)!.trim()), 120);
      if (fileName.isEmpty) { fileName = served; } else if (!fileName.contains('.')) { fileName += served.substring(served.lastIndexOf('.')); }
    }
    if (fileName.isEmpty) fileName = 'file';
    final dir = Directory([folder.path, ...parts].join(Platform.pathSeparator));
    await dir.create(recursive: true);
    final target = File('${dir.path}${Platform.pathSeparator}$fileName');
    await target.writeAsBytes(got.bytes, flush: true);
    return SavedFile(target.path, fileName, got.bytes.length);
  }

  // ------------------------------------------------------------------------------------------------ submissions

  /// The course page with the course chosen, waiting (up to ~18 s) for the table to show.
  Future<String> _openCourse(String course) async {
    await portal.lmsPage(assignmentsUrl);
    return portal.selectCourse(course);
  }

  static String _q(String s) => jsonEncode(s);

  Future<int> _rowIndex(String no, String title) async {
    final r = await _b.js('''
(() => {
  const clean = t => t.replace(/\\s+/g, ' ').trim();
  const rows = [...document.querySelectorAll('table tr')];
  return rows.findIndex(r => r.cells.length >= 8 && r.querySelector('td') && clean(r.cells[0].innerText) === ${_q(no)} && clean(r.cells[1].innerText) === ${_q(title)});
})()''');
    return r is num ? r.toInt() : -1;
  }

  /// Shows a modal the way the page's own click would (the portal ignores synthetic mouse clicks), returning its id
  /// selector, or '' if the row offers no such button.
  Future<String> _openModal(int row, String anchorPrefix) async {
    final target = await _b.js('''
(() => {
  const tr = document.querySelectorAll('table tr')[$row];
  const a = tr && tr.querySelector('a[data-target^="$anchorPrefix"]');
  if (!a) return '';
  const id = a.getAttribute('data-target');
  window.jQuery(id).modal('show');
  return id;
})()''');
    if (target is! String || target.isEmpty) return '';
    for (var i = 0; i < 20; i++) {
      final shown = await _b.js('(() => { const m = document.querySelector(${_q(target)}); return !!m && m.offsetParent !== null; })()');
      if (shown == true) { await Future<void>.delayed(pause); return target; }
      await Future<void>.delayed(pause);
    }
    return '';
  }

  Future<String> _flash() async {
    final r = await _b.js("Array.from(document.querySelectorAll('.alert')).map(e => (e.innerText || '').replace(/\\s+/g, ' ').trim()).filter(Boolean).join(' | ')");
    return r is String ? r : '';
  }

  Future<Map<String, dynamic>?> _fresh(String course, String id) async {
    var rows = parseCourseTable(await _b.html(), course);
    var hit = rows.where((a) => a['id'] == id).firstOrNull;
    if (hit == null) {
      rows = parseCourseTable(await portal.selectCourse(course), course);
      hit = rows.where((a) => a['id'] == id).firstOrNull;
    }
    return hit;
  }

  Future<int> _waitForRow(String course, String no, String title) async {
    await _openCourse(course);
    for (var i = 0; i < 60; i++) {
      final idx = await _rowIndex(no, title);
      if (idx >= 0) return idx;
      await Future<void>.delayed(pause);
    }
    throw FileProblem('The assignment was not found on the portal (it may have been removed or renamed).');
  }

  Future<void> _deleteHere(int row) async {
    final modal = await _openModal(row, '#modal-delete-assignment-submission');
    if (modal.isEmpty) throw FileProblem('The portal does not offer to delete a submission here (none yet, or the deadline has passed).');
    await _b.jsThenSettle("(() => { const b = document.querySelector(${_q('$modal a.btn[href*="assignmentSubmissionDelete"]')}); if (b) b.click(); })()", timeout: const Duration(seconds: 60));
  }

  /// Removes the student's submission, if the portal still offers Delete.
  Future<SubmitOutcome> deleteSubmission({required String course, required String id, required String title, required Object? number}) async {
    try {
      final row = await _waitForRow(course, '$number'.trim(), title.trim());
      await _deleteHere(row);
      final fresh = await _fresh(course, id);
      return fresh != null && fresh['is_submitted'] != true
          ? const SubmitOutcome(ok: true, message: 'The submission was deleted.', deleted: true)
          : const SubmitOutcome(ok: false, message: 'The portal did not confirm the deletion.', deleted: true);
    } on FileProblem catch (e) {
      return SubmitOutcome(ok: false, message: e.message);
    }
  }

  /// Uploads [bytes] as the submission. With [replace] the old one is deleted first. Everything that can be checked is
  /// checked before anything is deleted; nothing is sent unless the portal itself offers the button.
  Future<SubmitOutcome> submit({required String course, required String id, required String title, required Object? number,
      required String path, required Uint8List bytes, bool replace = false}) async {
    final upload = submissionUploadName(path);
    final bad = checkSubmissionFileBytes(upload, bytes.length);
    if (bad.isNotEmpty) return SubmitOutcome(ok: false, message: bad);
    final ext = upload.contains('.') ? upload.substring(upload.lastIndexOf('.')) : '';
    var deleted = false;
    try {
      var row = await _waitForRow(course, '$number'.trim(), title.trim());
      if (replace) {
        await _deleteHere(row);
        deleted = true;
        row = await _rowIndex('$number'.trim(), title.trim());
        if (row < 0) { await portal.selectCourse(course); row = await _rowIndex('$number'.trim(), title.trim()); }
      }
      final modal = await _openModal(row, '#modal-assignment-solution');
      if (modal.isEmpty) {
        return SubmitOutcome(ok: false, deleted: deleted, message: deleted
            ? 'The old submission was removed but the portal is not offering a new upload.'
            : 'The portal is not accepting a submission here (deadline passed or already submitted).');
      }
      final shown = await _b.js('(() => { const i = document.querySelector(${_q('$modal input[name="assignmentTitle"]')}); return i ? i.value.trim() : ""; })()');
      if ('$shown' != title.trim()) return SubmitOutcome(ok: false, deleted: deleted, message: "The portal's form is for a different assignment than the one chosen; nothing was sent.");
      await _b.attachFile('$modal input[type="file"]', upload, _mime[ext] ?? 'application/octet-stream', bytes);
      await _b.jsThenSettle("(() => { const b = document.querySelector(${_q('$modal button[type="submit"]')}); if (b) b.click(); })()", timeout: const Duration(minutes: 3));
      final flash = await _flash();
      final fresh = await _fresh(course, id);
      if ((fresh != null && fresh['is_submitted'] == true) || flash.toLowerCase().contains('uploaded successfully')) {
        return const SubmitOutcome(ok: true, message: 'Uploaded; the portal lists your submission.');
      }
      final said = flash.isEmpty ? '' : ' (it said: "${flash.length > 150 ? flash.substring(0, 150) : flash}")';
      return SubmitOutcome(ok: false, deleted: deleted, message: 'The portal did not confirm the upload$said.${deleted ? ' Your old submission was removed, so please upload again.' : ''}');
    } on FileProblem catch (e) {
      return SubmitOutcome(ok: false, deleted: deleted, message: e.message);
    }
  }
}

import 'dart:convert';

import 'data.dart' show Summary;
import 'portal.dart';
import 'portal_parse.dart';

/// One full read of the portal, on the phone: the same pages in the same order as the desktop app's `run_sync`, turned into
/// the same `summary.json` the cloud check writes, so every screen of the app works unchanged on it. Nothing here keeps a
/// portal link: a file is downloaded by looking the course up again at that moment (the links expire).
const cmsBase = 'https://$cmsHost';
const lmsBase = 'https://$lmsHost';
const announcementsUrl = '$lmsBase/Student/Announcements.php';
const lecturesUrl = '$lmsBase/Student/LectureNotes.php';
const miscUrl = '$lmsBase/Student/Miscellaneous.php';
const attendanceUrl = '$cmsBase/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx';
const resultsUrl = '$cmsBase/Sys/Student/Exams/ExamResult.aspx';
const examsUrl = '$cmsBase/Sys/Student/ExamSeatingPlan/ExamSeats';
const timetableUrl = '$cmsBase/Sys/Student/CourseRegistration/TimeTable.aspx';

class PortalSync {
  PortalSync(this.portal, {this.minimumAttendance = 75, DateTime Function()? now, this.retryPause = const Duration(seconds: 3)}) : _now = now ?? DateTime.now;

  /// How long to wait before reading an empty-looking page once more.
  final Duration retryPause;
  final Portal portal;
  final int minimumAttendance;
  final DateTime Function() _now;

  /// Reads everything. [say] is told what is happening ("Reading attendance"). A part that fails is skipped and named in
  /// `skipped`, so one slow page never loses the rest; a course that fails inside a part is skipped on its own. After each part
  /// [onPartial] gets the summary as far as it is read (the parts not read yet keep what [previous] had), so the screens can
  /// fill in while the rest is still being read. With [only] set to some of the section names (assignments, attendance, exams,
  /// results, timetable, announcements, lectures) just those are read and everything else keeps what [previous] had: that is
  /// what a screen's own refresh does. `report` says, per part, what came back and how long it took.
  Future<({Summary summary, List<String> skipped, List<String> report})> run({
    void Function(String)? say, String campus = '', Map<String, dynamic>? previous, Future<void> Function(Summary)? onPartial,
    Set<String>? only, void Function(int done, int total)? onProgress,
  }) async {
    // The everyday full check leaves the lecture notes out unless there are none yet: they change rarely and cost two page loads
    // per course (the Lectures screen's own refresh reads them). A screen's refresh reads just its own part.
    final lecturesKnown = previous?['lectures'] is List && (previous!['lectures'] as List).isNotEmpty;
    bool want(String k) => only != null ? only.contains(k) : (k != 'lectures' || !lecturesKnown);
    const all = ['assignments', 'attendance', 'exams', 'results', 'timetable', 'announcements', 'lectures'];
    final total = all.where(want).length;
    var finished = 0;
    void tell(String s) => say?.call(s);
    final skipped = <String>[], report = <String>[];
    final read = <String>{};

    final meta = <String, dynamic>{'campus': campus};
    var courses = <PortalCourse>[];
    final assignments = <Json>[], announcements = <Json>[], lectures = <Json>[];
    var attendance = <Json>[], exams = <Json>[];
    Json? results, timetable;

    Map<String, dynamic> build() {
      meta['last_sync'] = _now().toIso8601String();
      final s = buildSummary(
        meta: meta, assignments: assignments, attendance: attendance, exams: exams, timetable: timetable,
        results: results, announcements: announcements, lectures: lectures, minimum: minimumAttendance, now: _now(),
      );
      // what is not read yet keeps the last full read, so a section never blinks empty while the rest loads
      if (previous != null) {
        for (final k in ['assignments', 'attendance', 'exams', 'timetable', 'results', 'announcements', 'lectures']) {
          if (!read.contains(k) && previous[k] != null) s[k] = previous[k];
        }
        if (!read.contains('assignments') && previous['student'] != null) s['student'] = previous['student'];
      }
      return s;
    }

    bool had(String key) {
      final v = previous?[key];
      if (v is List) return v.isNotEmpty;
      if (v is Map) return (v['semesters'] is List && (v['semesters'] as List).isNotEmpty) || (v['sessions'] is List && (v['sessions'] as List).isNotEmpty);
      return false;
    }

    /// [empty] says whether what was read looks empty. An empty page is read once more after a pause (it may have been taken before
    /// the portal filled it in); if it is still empty and the last full read had data, the earlier data is kept rather than replaced
    /// by nothing, and the report says so. Only parts that replace their data can use this.
    Future<void> part(String name, String key, Future<String> Function() f, {bool Function()? empty}) async {
      if (!want(key)) return;   // a section refresh reads only its own part
      tell(name);
      onProgress?.call(finished, total);
      final began = DateTime.now();
      try {
        var what = await f();
        if (empty != null && empty()) {
          await Future<void>.delayed(retryPause);
          what = await f();
          if (empty() && had(key)) {
            report.add('$key: the portal page came back empty, so the earlier data was kept');
            return;
          }
        }
        read.add(key);
        report.add('$key: $what (${(DateTime.now().difference(began).inMilliseconds / 1000).toStringAsFixed(1)} s)');
        if (onPartial != null) await onPartial(Summary(build()));
      } catch (e) {
        skipped.add(key);
        report.add('$key: could not be read (${e is StateError ? e.message : e.runtimeType})');
      } finally {
        finished++;
        onProgress?.call(finished, total);
      }
    }

    /// One course at a time; a course that fails is noted and the next one still runs.
    Future<void> eachCourse(String what, Future<void> Function(PortalCourse) f) async {
      var failed = 0;
      for (final c in courses) {
        try { await f(c); } catch (_) { failed++; }
      }
      if (failed > 0) report.add('$what: $failed of ${courses.length} courses could not be read');
      if (failed == courses.length && courses.isNotEmpty) throw StateError('no course could be read');
    }

    if (!want('assignments') && (want('announcements') || want('lectures'))) {
      // the courses are needed to read each one's announcements or lecture notes
      tell('Looking up your courses');
      try { courses = await portal.courses(); } catch (_) {/* reported below */}
      if (courses.isEmpty) throw StateError('No courses were found. Sign in again, or try later.');
    }

    await part('Reading your courses and assignments', 'assignments', () async {
      courses = await portal.courses();
      final head = await portal.browser.js('''
JSON.stringify({name: ((document.querySelector('a.dropdown-toggle span.hidden-xs') || {}).innerText || '').trim(),
  semester: (() => { const s = document.querySelector('#semesterId'); return s && s.selectedOptions.length ? s.selectedOptions[0].textContent.trim() : ''; })()})''');
      final h = jsonDecode(head as String) as Map<String, dynamic>;
      final name = '${h['name']}'.trim();
      meta['student_name'] = name.isNotEmpty && name == name.toUpperCase() ? titleCase(name) : name;
      meta['semester'] = '${h['semester']}';
      await eachCourse('assignments', (c) async { assignments.addAll(parseCourseTable(await portal.selectCourse(c.name), c.name)); });
      return '${assignments.length} assignments in ${courses.length} courses';
    });
    if (want('assignments') && courses.isEmpty) throw StateError('No courses were found. Sign in again, or try later.');

    await part('Reading attendance', 'attendance', () async { attendance = await _attendance(previous?['attendance']); return '${attendance.length} courses'; }, empty: () => attendance.isEmpty);
    await part('Reading exam seats', 'exams', () async { exams = await _exams(); return '${exams.length} rows'; }, empty: () => exams.isEmpty);
    await part('Reading results', 'results', () async { results = parseResults(await portal.cmsPage(resultsUrl, ready: "document.querySelector('table caption')", readySeconds: 6)); return '${(results!['semesters'] as List).length} semesters'; }, empty: () => (results?['semesters'] as List? ?? const []).isEmpty);
    await part('Reading the timetable', 'timetable', () async { timetable = parseTimetable(await portal.cmsPage(timetableUrl, ready: "document.querySelector('td.event')", readySeconds: 8)); return '${(timetable!['sessions'] as List).length} classes'; }, empty: () => (timetable?['sessions'] as List? ?? const []).isEmpty);
    await part('Reading announcements', 'announcements', () async {
      await portal.lmsPage(announcementsUrl);
      await eachCourse('announcements', (c) async { announcements.addAll(parseAnnouncements(await portal.selectCourse(c.name), c.name)); });
      return '${announcements.length} announcements';
    });
    await part('Reading lecture notes', 'lectures', () async {
      await portal.lmsPage(lecturesUrl);
      await eachCourse('lecture notes', (c) async {
        var html = await portal.selectCourse(c.name);
        var rows = parseLectures(html, c.name);
        if (rows.isEmpty) { await Future<void>.delayed(const Duration(seconds: 2)); html = await portal.browser.html(); rows = parseLectures(html, c.name); }   // a table that fills in late
        if (rows.isEmpty) report.add('lecture page for ${c.name}: ${await _shape()}');   // what the page looked like, to see why nothing was found
        lectures.addAll(rows);
      });
      await portal.lmsPage(miscUrl);
      await eachCourse('miscellaneous files', (c) async { lectures.addAll(parseMisc(await portal.selectCourse(c.name), c.name)); });
      return '${lectures.length} entries';
    });

    return (summary: Summary(build()), skipped: skipped, report: report);
  }

  /// What the current page is made of (counts and names only, no text from it): for finding out why a reader found nothing.
  Future<String> _shape() async {
    try {
      final raw = await portal.browser.js('''
JSON.stringify({host: location.host, path: location.pathname, tables: document.querySelectorAll('table').length,
  rows: document.querySelectorAll('table tr').length, links: document.querySelectorAll('a[href*="Download"]').length,
  selects: Array.from(document.querySelectorAll('select')).map(s => s.id + ':' + s.options.length).join(','), width: window.innerWidth})''');
      return '$raw';
    } catch (_) {
      return 'unreadable';
    }
  }

  Future<List<Json>> _attendance(Object? previous) async {
    final courses = parseAttendance(await portal.cmsPage(attendanceUrl, ready: "Array.from(document.querySelectorAll('tr')).some(r => r.cells.length >= 12)", readySeconds: 10));
    // a course whose hours have not changed since the last read keeps the class-by-class list it had (each list is a page load)
    final old = <String, Map<String, dynamic>>{
      for (final c in (previous is List ? previous : const [])) if (c is Map && c['code'] != null) '${c['code']}': c.cast<String, dynamic>(),
    };
    for (final c in courses) {
      final was = old['${c['code']}'];
      final same = was != null && was['present'] == c['present'] && was['absent'] == c['absent'] && was['classes'] is List && (was['classes'] as List).isNotEmpty;
      if (same) { c['sessions'] = [for (final s in was['classes'] as List) if (s is Map) s.cast<String, dynamic>()]; continue; }
      final url = '${c['detail_url']}';
      if (url.isEmpty) { c['sessions'] = <Json>[]; continue; }
      try {
        final d = parseAttendanceDetail(await portal.cmsPage(Uri.parse(attendanceUrl).resolve(url).toString(), ready: "document.querySelector(\"[id*='AttendanceDetails']\")", readySeconds: 6));
        c['sessions'] = d['sessions'];
      } catch (_) {
        c['sessions'] = was?['classes'] ?? <Json>[];   // the totals are still right; keep the older class list if there is one
      }
    }
    return courses;
  }

  Future<List<Json>> _exams() async {
    final page = await portal.cmsPage(examsUrl, ready: "document.querySelector(\"[id*='ExamSeats']\")", readySeconds: 6);
    final raw = await portal.browser.js('''
JSON.stringify(Array.from(document.querySelectorAll('#BodyPH_ddlExamTypeFilter option')).map(o => [o.value, (o.innerText || '').trim()]).filter(x => x[0] && x[1]))''');
    final types = [for (final e in jsonDecode('${raw ?? '[]'}') as List) ((e as List)[0] as String, e[1] as String)];
    if (types.isEmpty) return parseExamSeats(page, 'Exam');
    final out = <Json>[];
    for (final (i, t) in types.indexed) {
      out.addAll(parseExamSeats(i == 0 ? page : await portal.selectOption('#BodyPH_ddlExamTypeFilter', t.$1), t.$2));
    }
    return out;
  }
}

/// Python's str.title() for an all-capitals name ("MUHAMMAD SAAD" becomes "Muhammad Saad").
String titleCase(String s) => s.toLowerCase().replaceAllMapped(RegExp(r'(^|[^a-z])([a-z])'), (m) => '${m.group(1)}${m.group(2)!.toUpperCase()}');

/// The summary the phone screens read (the same shape as `summary.py` makes on the PC, schema 1), plus the lecture list
/// (added for the phone's own Lectures page; the file links are left out because they expire).
Map<String, dynamic> buildSummary({
  required Map<String, dynamic> meta, required List<Json> assignments, required List<Json> attendance, required List<Json> exams,
  required Json? timetable, required Json? results, required List<Json> announcements, required List<Json> lectures,
  required int minimum, required DateTime now,
}) {
  String? iso(DateTime? d) => d?.toIso8601String().split('.').first;
  final asg = <Json>[];
  for (final a in assignments) {
    final info = classify(a, now);
    final due = deadlineOf(a);
    final (canAdd, canReplace) = submissionActions('${a['action'] ?? ''}');
    final files = a['files'];
    asg.add({
      'id': a['id'], 'course': a['course'], 'title': a['title'], 'number': a['assign_no'], 'due_at': iso(due),
      'extended': a['is_extended'] == true, 'was_due': (a['original_due_date'] ?? '') == '' ? null : a['original_due_date'],
      'submitted': a['is_submitted'] == true, 'open': isOpenPending(a), 'urgency': info['key'],
      'marks': (a['marks'] ?? '') == '' ? null : a['marks'], 'can_submit': canAdd || canReplace,
      'has_brief': files is Map && files['brief'] != null && files['brief'] != '' && files['brief'] != false,
    });
  }

  final att = <Json>[];
  for (final c in attendance) {
    final p = (c['present'] as num?)?.toDouble() ?? 0, ab = (c['absent'] as num?)?.toDouble() ?? 0;
    final m = attendanceMargin(p, p + ab, minimum.toDouble());
    final sessions = [for (final s in (c['sessions'] as List? ?? const [])) if (s is Map) s.cast<String, dynamic>()];
    att.add({
      'code': c['code'], 'title': c['title'], 'credit_hours': (c['credit_hours'] ?? '') == '' ? null : c['credit_hours'],
      'teacher': (c['teacher'] ?? '') == '' ? null : c['teacher'], 'present': p, 'absent': ab,
      'percent': m['percent'], 'ok': m['ok'] == true, 'can_miss': m['can_miss'], 'need': m['need'],
      'classes': [for (final s in sessions.length > 12 ? sessions.sublist(sessions.length - 12) : sessions)
        {'date': s['date'], 'hours': s['hours'], 'present': s['present'], 'absent': s['absent']}],
    });
  }

  final ex = [for (final e in exams) {
    'title': e['title'], 'type': (e['exam_type'] ?? '') == '' ? null : e['exam_type'], 'date': (e['date'] ?? '') == '' ? null : e['date'],
    'time': (e['start_time'] ?? '') == '' ? null : e['start_time'], 'room': (e['room'] ?? '') == '' ? null : e['room'],
    'row': (e['row'] ?? '') == '' ? null : e['row'], 'seat': (e['column'] ?? '') == '' ? null : e['column'], 'scheduled': e['scheduled'] == true,
  }];

  final tt = [for (final s in (timetable?['sessions'] as List? ?? const [])) if (s is Map) {
    'day': s['day'], 'start': s['start'], 'end': s['end'], 'course': s['course'], 'teacher': (s['teacher'] ?? '') == '' ? null : s['teacher'],
  }];

  Json? res;
  if (results != null && (results['semesters'] as List? ?? const []).isNotEmpty) {
    final sems = [for (final s in results['semesters'] as List) (s as Map).cast<String, dynamic>()];
    final done = sems.where((s) => s['complete'] == true && s['cgpa'] != null).toList();
    res = {
      'cgpa': done.isEmpty ? null : done.last['cgpa'],
      'semesters': [for (final s in sems) {
        'name': s['name'], 'gpa': s['gpa'], 'cgpa': s['cgpa'], 'complete': s['complete'] == true,
        'courses': [for (final c in (s['courses'] as List? ?? const [])) if (c is Map) {
          'code': c['code'], 'title': c['title'], 'credits': c['credits'], 'grade': (c['grade'] ?? '') == '' ? null : c['grade']}],
      }],
    };
  }

  String clip(Object? t, int n) { final s = '${t ?? ''}'.trim(); return s.length > n ? s.substring(0, n) : s; }
  final ann = [for (final a in announcements.take(30)) {
    'id': a['id'], 'course': a['course'], 'title': clip(a['title'], 120), 'text': clip(a['text'], 600), 'posted_at': a['posted_at'] ?? a['first_seen'],
  }];

  final lec = [for (final l in lectures) {
    'id': l['id'], 'course': l['course'], 'week': l['week'], 'title': l['title'], 'kind': l['kind'] ?? 'lecture',
    'files': [for (final f in (l['files'] as List? ?? const [])) if (f is Map) {'label': f['label'], 'filename': f['filename']}],
  }];

  return {
    'schema': 1,
    'generated_at': iso(now),
    'app_version': null,
    'student': {'name': meta['student_name'], 'semester': meta['semester'], 'campus': (meta['campus'] ?? '') == '' ? null : meta['campus']},
    'last_check': meta['last_sync'],
    'minimum_attendance': minimum,
    'assignments': asg,
    'attendance': att,
    'exams': ex,
    'timetable': tt,
    'results': res,
    'announcements': ann,
    'lectures': lec,
  };
}

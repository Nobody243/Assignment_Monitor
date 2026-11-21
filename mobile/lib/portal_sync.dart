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
  PortalSync(this.portal, {this.minimumAttendance = 75, DateTime Function()? now}) : _now = now ?? DateTime.now;
  final Portal portal;
  final int minimumAttendance;
  final DateTime Function() _now;

  /// Reads everything. [say] is told what is happening ("Reading attendance"); a part that fails is skipped and named in
  /// [skipped], so one slow page never loses the rest.
  Future<({Summary summary, List<String> skipped})> run({void Function(String)? say, String campus = ''}) async {
    void tell(String s) => say?.call(s);
    final skipped = <String>[];
    Future<T?> part<T>(String name, Future<T> Function() f) async {
      tell(name);
      try { return await f(); } catch (e) { skipped.add(name); return null; }
    }

    final meta = <String, dynamic>{'campus': campus};
    var courses = <PortalCourse>[];
    final assignments = <Json>[];
    final announcements = <Json>[];
    final lectures = <Json>[];

    await part('Reading your courses and assignments', () async {
      courses = await portal.courses();
      final head = await portal.browser.js('''
JSON.stringify({name: ((document.querySelector('a.dropdown-toggle span.hidden-xs') || {}).innerText || '').trim(),
  semester: (() => { const s = document.querySelector('#semesterId'); return s && s.selectedOptions.length ? s.selectedOptions[0].textContent.trim() : ''; })()})''');
      final h = jsonDecode(head as String) as Map<String, dynamic>;
      final name = '${h['name']}'.trim();
      meta['student_name'] = name.isNotEmpty && name == name.toUpperCase() ? titleCase(name) : name;
      meta['semester'] = '${h['semester']}';
      for (final c in courses) {
        assignments.addAll(parseCourseTable(await portal.selectCourse(c.name), c.name));
      }
    });
    if (courses.isEmpty) throw StateError('No courses were found. Sign in again, or try later.');

    final attendance = await part('Reading attendance', _attendance) ?? <Json>[];
    final exams = await part('Reading exam seats', _exams) ?? <Json>[];
    final results = await part('Reading results', () async => parseResults(await portal.cmsPage(resultsUrl)));
    final timetable = await part('Reading the timetable', () async => parseTimetable(await portal.cmsPage(timetableUrl)));
    await part('Reading announcements', () async {
      await portal.lmsPage(announcementsUrl);
      for (final c in courses) { announcements.addAll(parseAnnouncements(await portal.selectCourse(c.name), c.name)); }
    });
    await part('Reading lecture notes', () async {
      await portal.lmsPage(lecturesUrl);
      for (final c in courses) { lectures.addAll(parseLectures(await portal.selectCourse(c.name), c.name)); }
      await portal.lmsPage(miscUrl);
      for (final c in courses) { lectures.addAll(parseMisc(await portal.selectCourse(c.name), c.name)); }
    });

    meta['last_sync'] = _now().toIso8601String();
    final s = buildSummary(
      meta: meta, assignments: assignments, attendance: attendance, exams: exams, timetable: timetable,
      results: results, announcements: announcements, lectures: lectures, minimum: minimumAttendance, now: _now(),
    );
    return (summary: Summary(s), skipped: skipped);
  }

  Future<List<Json>> _attendance() async {
    final courses = parseAttendance(await portal.cmsPage(attendanceUrl));
    for (final c in courses) {
      final url = '${c['detail_url']}';
      if (url.isEmpty) { c['sessions'] = <Json>[]; continue; }
      try {
        final d = parseAttendanceDetail(await portal.cmsPage(Uri.parse(attendanceUrl).resolve(url).toString()));
        c['sessions'] = d['sessions'];
      } catch (_) {
        c['sessions'] = <Json>[];   // the totals are still right; only the class-by-class list is missing
      }
    }
    return courses;
  }

  Future<List<Json>> _exams() async {
    final page = await portal.cmsPage(examsUrl);
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

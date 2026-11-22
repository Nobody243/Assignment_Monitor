import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

// Tolerant readers: the file comes from another program (and another version of it), so a missing key, a null or a value
// of the wrong type must give a sensible default, never an exception on a screen.
String _str(Object? v, [String d = '']) => v is String ? v : (v == null ? d : '$v');
String? _strOrNull(Object? v) => v == null ? null : (v is String ? v : '$v');
double _num(Object? v, [double d = 0]) => v is num ? v.toDouble() : (v is String ? (double.tryParse(v) ?? d) : d);
bool _bool(Object? v, [bool d = false]) => v is bool ? v : d;
DateTime? _date(Object? v) => v is String ? DateTime.tryParse(v) : null;
Map<String, dynamic> _map(Object? v) => v is Map ? Map<String, dynamic>.from(v) : const {};
List<Map<String, dynamic>> _list(Object? v) => v is List ? [for (final x in v) if (x is Map) Map<String, dynamic>.from(x)] : const [];

/// What the phone reads: summary.json (see ../DESIGN.md and ../../summary.py).
class Summary {
  Summary(this.raw);
  final Map<String, dynamic> raw;

  static Future<Summary> load() async => Summary(jsonDecode(await rootBundle.loadString('assets/summary.json')) as Map<String, dynamic>);

  DateTime get generatedAt => _date(raw['generated_at']) ?? DateTime.now();
  DateTime? get lastCheck => _date(raw['last_check']);
  String get studentName => _str(_map(raw['student'])['name'], 'Student').trim().isEmpty ? 'Student' : _str(_map(raw['student'])['name'], 'Student');
  String get firstName => studentName.split(' ').first;
  String get semester => _str(_map(raw['student'])['semester']);
  int get minimum => _num(raw['minimum_attendance'], 75).round();

  List<Work> get work => [for (final a in _list(raw['assignments'])) Work(a)];
  List<Course> get attendance => [for (final a in _list(raw['attendance'])) Course(a)];
  List<Exam> get exams => [for (final e in _list(raw['exams'])) Exam(e)];
  List<ClassSlot> get timetable => [for (final t in _list(raw['timetable'])) ClassSlot(t)].where((c) => c.valid).toList();
  List<Lecture> get lectures => [for (final l in _list(raw['lectures'])) Lecture(l)];
  List<Note> get announcements => [for (final a in _list(raw['announcements'])) Note(a)];
  List<Term> get terms => [for (final s in _list(_map(raw['results'])['semesters'])) Term(s)];
  double? get cgpa => raw['results'] == null ? null : (_map(raw['results'])['cgpa'] is num ? (_map(raw['results'])['cgpa'] as num).toDouble() : null);
}

/// The demo clock: the fixture was made at one moment; the prototype pretends that moment is "now" and lets time pass
/// from there, so countdowns look right whenever the prototype is opened.
class Clock {
  Clock(DateTime base) : _base = base, _start = DateTime.now();
  Clock.real() : _base = null, _start = DateTime.now();
  final DateTime? _base;
  final DateTime _start;
  DateTime now() => _base == null ? DateTime.now() : _base.add(DateTime.now().difference(_start));
}

class Work {
  Work(this.m);
  final Map<String, dynamic> m;
  String get course => _str(m['course'], 'Course');
  String get title => _str(m['title'], 'Assignment');
  String get id => _str(m['id'], '$course#$title');
  String get number => _str(m['number']);
  DateTime? get due => _date(m['due_at']);
  bool get submitted => _bool(m['submitted']);
  bool get extended => _bool(m['extended']);
  String? get wasDue => _strOrNull(m['was_due']);
  bool get open => _bool(m['open']);
  String? get marks => _strOrNull(m['marks']);
  String get urgency => _str(m['urgency']);
  bool get canSubmit => _bool(m['can_submit']);
  bool get hasBrief => _bool(m['has_brief']);
  bool get overdue => !submitted && urgency == 'missed';
  bool get todo => !submitted && !overdue;
}

/// A week of lecture notes (or a miscellaneous file) the phone read from the portal. Links are not kept: they expire.
class Lecture {
  Lecture(this.m);
  final Map<String, dynamic> m;
  String get course => _str(m['course'], 'Course');
  String get title => _str(m['title'], 'Lecture');
  String get kind => _str(m['kind'], 'lecture');
  Object? get week => m['week'];
  List<({String label, String filename, int index})> get files => [for (final (i, f) in _list(m['files']).indexed) (label: _str(f['label'], 'Download'), filename: _str(f['filename']), index: f['index'] is num ? (f['index'] as num).toInt() : i)];
}

class Course {
  Course(this.m);
  final Map<String, dynamic> m;
  String get code => _str(m['code']);
  String get title => _str(m['title'], 'Course');
  String? get teacher => _strOrNull(m['teacher']);
  double get credit => _num(m['credit_hours']);
  double get present => _num(m['present']);
  double get absent => _num(m['absent']);
  double get percent => _num(m['percent']);
  bool get ok => _bool(m['ok'], true);
  double get canMiss => _num(m['can_miss']);
  double get need => _num(m['need']);
  bool get recorded => present + absent > 0;
  List<Map<String, dynamic>> get classes => _list(m['classes']);
  List<double> get classHours => [for (final c in classes) _num(c['hours'])];
}

class Exam {
  Exam(this.m);
  final Map<String, dynamic> m;
  String get title => _str(m['title'], 'Exam');
  String? get type => _strOrNull(m['type']);
  String? get date => _strOrNull(m['date']);
  String? get time => _strOrNull(m['time']);
  String? get room => _strOrNull(m['room']);
  String? get row => _strOrNull(m['row']);
  String? get seat => _strOrNull(m['seat']);
  bool get scheduled => _bool(m['scheduled']);
  /// 'dd/mm/yyyy' as the portal prints it.
  DateTime? get day {
    final p = (date ?? '').split('/');
    if (p.length != 3) return null;
    return DateTime.tryParse('${p[2]}-${p[1].padLeft(2, '0')}-${p[0].padLeft(2, '0')}');
  }
}

class ClassSlot {
  ClassSlot(this.m);
  final Map<String, dynamic> m;
  String get day => _str(m['day']);
  String get start => _str(m['start']);
  String get end => _str(m['end']);
  String get course => _str(m['course'], 'Class');
  String? get teacher => _strOrNull(m['teacher']);

  /// A class needs a weekday and two readable times to be placed on the grid; anything else is left out.
  bool get valid => weekdays.contains(day) && _time.hasMatch(start) && _time.hasMatch(end);
  static final _time = RegExp(r'^\d{1,2}:\d{2}$');
}

class Note {
  Note(this.m);
  final Map<String, dynamic> m;
  String get title => _str(m['title'], 'Announcement');
  String get course => _str(m['course']);
  String get text => _str(m['text']);
  String get id => _str(m['id'], '$title|$course');
  DateTime? get postedAt => _date(m['posted_at']);
}

class Term {
  Term(this.m);
  final Map<String, dynamic> m;
  String get name => _str(m['name'], 'Semester');
  double? get gpa => m['gpa'] is num ? (m['gpa'] as num).toDouble() : null;
  bool get complete => _bool(m['complete']);
  double? get cgpa => m['cgpa'] is num ? (m['cgpa'] as num).toDouble() : null;
  List<CourseResult> get courses => [for (final c in _list(m['courses'])) CourseResult(c)];
}

class CourseResult {
  CourseResult(this.m);
  final Map<String, dynamic> m;
  String get code => _str(m['code']);
  String get title => _str(m['title']);
  double get credits => _num(m['credits']);
  String? get grade => _strOrNull(m['grade']);
}

/// "9h 32m", "2 days", "35 min", "overdue": the same wording as the desktop app.
String countdown(DateTime due, DateTime now) {
  final d = due.difference(now);
  if (d.isNegative) return 'overdue';
  if (d.inMinutes < 60) return '${d.inMinutes.clamp(1, 59)} min';
  if (d.inHours < 48) return '${d.inHours}h ${d.inMinutes % 60}m';
  return '${d.inDays} days';
}

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

String dayLabel(DateTime d) => '${weekdays[d.weekday - 1]} ${d.day} ${months[d.month - 1]}';
String timeLabel(DateTime d) {
  final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
  return '$h:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'am' : 'pm'}';
}

import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

/// What the phone reads: summary.json (see ../DESIGN.md and ../../summary.py). The prototype reads the bundled fixture.
class Summary {
  Summary(this.raw);
  final Map<String, dynamic> raw;

  static Future<Summary> load() async => Summary(jsonDecode(await rootBundle.loadString('assets/summary.json')) as Map<String, dynamic>);

  DateTime get generatedAt => DateTime.parse(raw['generated_at'] as String);
  DateTime? get lastCheck => raw['last_check'] == null ? null : DateTime.tryParse(raw['last_check'] as String);
  String get studentName => ((raw['student'] as Map)['name'] ?? 'Student') as String;
  String get firstName => studentName.split(' ').first;
  String get semester => ((raw['student'] as Map)['semester'] ?? '') as String;
  int get minimum => (raw['minimum_attendance'] ?? 75) as int;

  List<Work> get work => [for (final a in raw['assignments'] as List) Work(a as Map<String, dynamic>)];
  List<Course> get attendance => [for (final a in raw['attendance'] as List) Course(a as Map<String, dynamic>)];
  List<Exam> get exams => [for (final e in raw['exams'] as List) Exam(e as Map<String, dynamic>)];
  List<ClassSlot> get timetable => [for (final t in raw['timetable'] as List) ClassSlot(t as Map<String, dynamic>)];
  List<Note> get announcements => [for (final a in raw['announcements'] as List) Note(a as Map<String, dynamic>)];
  List<Term> get terms => raw['results'] == null ? [] : [for (final s in (raw['results'] as Map)['semesters'] as List) Term(s as Map<String, dynamic>)];
  double? get cgpa => raw['results'] == null ? null : ((raw['results'] as Map)['cgpa'] as num?)?.toDouble();
}

/// The demo clock: the fixture was made at one moment; the prototype pretends that moment is "now" and lets time pass
/// from there, so countdowns look right whenever the prototype is opened.
class Clock {
  Clock(DateTime base) : _base = base, _start = DateTime.now();
  final DateTime _base;
  final DateTime _start;
  DateTime now() => _base.add(DateTime.now().difference(_start));
}

class Work {
  Work(this.m);
  final Map<String, dynamic> m;
  String get id => m['id'] as String;
  String get course => m['course'] as String;
  String get title => m['title'] as String;
  String get number => (m['number'] ?? '') as String;
  DateTime? get due => m['due_at'] == null ? null : DateTime.parse(m['due_at'] as String);
  bool get submitted => m['submitted'] as bool;
  bool get extended => m['extended'] as bool;
  String? get wasDue => m['was_due'] as String?;
  bool get open => m['open'] as bool;
  String? get marks => m['marks'] as String?;
  String get urgency => (m['urgency'] ?? '') as String;
  bool get canSubmit => m['can_submit'] as bool;
  bool get overdue => !submitted && urgency == 'missed';
  bool get todo => !submitted && !overdue;
}

class Course {
  Course(this.m);
  final Map<String, dynamic> m;
  String get code => m['code'] as String;
  String get title => m['title'] as String;
  String? get teacher => m['teacher'] as String?;
  double get credit => double.tryParse((m['credit_hours'] ?? '') as String) ?? 0;
  double get present => (m['present'] as num).toDouble();
  double get absent => (m['absent'] as num).toDouble();
  double get percent => (m['percent'] as num).toDouble();
  bool get ok => m['ok'] as bool;
  double get canMiss => (m['can_miss'] as num).toDouble();
  double get need => (m['need'] as num).toDouble();
  bool get recorded => present + absent > 0;
  List<double> get classHours => [for (final c in m['classes'] as List) ((c as Map)['hours'] as num?)?.toDouble() ?? 0];
}

class Exam {
  Exam(this.m);
  final Map<String, dynamic> m;
  String get title => m['title'] as String;
  String? get type => m['type'] as String?;
  String? get date => m['date'] as String?;
  String? get time => m['time'] as String?;
  String? get room => m['room'] as String?;
  String? get row => m['row'] as String?;
  String? get seat => m['seat'] as String?;
  bool get scheduled => m['scheduled'] as bool;
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
  String get day => m['day'] as String;
  String get start => m['start'] as String;
  String get end => m['end'] as String;
  String get course => m['course'] as String;
  String? get teacher => m['teacher'] as String?;
}

class Note {
  Note(this.m);
  final Map<String, dynamic> m;
  String get title => m['title'] as String;
  String get course => m['course'] as String;
  String get text => (m['text'] ?? '') as String;
}

class Term {
  Term(this.m);
  final Map<String, dynamic> m;
  String get name => m['name'] as String;
  double? get gpa => (m['gpa'] as num?)?.toDouble();
  bool get complete => m['complete'] as bool;
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

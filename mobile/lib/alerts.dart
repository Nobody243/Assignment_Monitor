import 'data.dart';
import 'logic.dart';

/// Everything the phone says or exports that is worked out from a summary, as plain functions with no plugin in sight, so
/// each is tested without a phone. The wording follows the desktop app.
const appVersion = '1.0.4';   // keep in step with pubspec.yaml

typedef AlertText = ({String title, String body});

String _short(String s, int n) => s.length <= n ? s : '${s.substring(0, n - 1)}…';
String _day(DateTime d) => '${weekdays[d.weekday - 1]} ${d.day} ${months[d.month - 1]}';
String _clock(DateTime d) => timeLabel(d);
bool _sameDay(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;

// ------------------------------------------------------------------------------------------------ Sunday summary
/// The week ahead, or null when there is nothing to say. Goes out on Sunday evening.
AlertText? weeklySummary(Summary s, DateTime now) {
  final horizon = now.add(const Duration(days: 8));
  final coming = [for (final w in s.work) if (w.todo && w.open && w.due != null && w.due!.isAfter(now) && !w.due!.isAfter(horizon)) w]..sort((a, b) => a.due!.compareTo(b.due!));
  final papers = [for (final e in s.exams) if (e.scheduled && e.day != null && !e.day!.isBefore(DateTime(now.year, now.month, now.day)) && !e.day!.isAfter(horizon)) e]..sort((a, b) => a.day!.compareTo(b.day!));
  final risks = <String>[];
  for (final c in s.attendance) {
    if (!c.recorded) continue;
    if (!c.ok) {
      risks.add('${c.title}: ${c.percent.round()}%, below ${s.minimum}%');
    } else if (c.canMiss <= 1.5) {
      risks.add('${c.title}: ${c.percent.round()}%, can miss only ${hoursText(c.canMiss)}');
    }
  }
  if (coming.isEmpty && papers.isEmpty && risks.isEmpty) return null;
  final lines = <String>[];
  if (coming.isNotEmpty) {
    lines.add('Due next week (${coming.length}):');
    for (final w in coming.take(6)) { lines.add('- ${_short(w.title, 38)} (${_short(w.course, 24)}), ${_day(w.due!)} ${_clock(w.due!)}'); }
    if (coming.length > 6) lines.add('... and ${coming.length - 6} more');
  }
  if (papers.isNotEmpty) lines.add('Exams (${papers.length}): ${papers.take(3).map((e) => '${_short(e.title, 28)} ${_day(e.day!)}').join(', ')}');
  if (risks.isNotEmpty) lines.add('Attendance to watch: ${risks.take(3).join('; ')}');
  final bits = [
    if (coming.isNotEmpty) '${coming.length} due',
    if (papers.isNotEmpty) '${papers.length} exam${papers.length == 1 ? '' : 's'}',
    if (risks.isNotEmpty) '${risks.length} attendance',
  ];
  return (title: 'Your week ahead: ${bits.join(', ')}', body: lines.join('\n'));
}

// ------------------------------------------------------------------------------------------------ daily digest
/// One morning message instead of many: what is due today, the classes, and an exam in the next three days.
AlertText? dailyDigest(Summary s, DateTime now) {
  final today = [for (final w in s.work) if (w.todo && w.open && w.due != null && _sameDay(w.due!, now) && w.due!.isAfter(now)) w]..sort((a, b) => a.due!.compareTo(b.due!));
  final dayName = weekdays[now.weekday - 1];
  final classes = [for (final c in s.timetable) if (c.day == dayName) c]..sort((a, b) => a.start.compareTo(b.start));
  final soon = [for (final e in s.exams) if (e.scheduled && e.day != null) if (!e.day!.isBefore(DateTime(now.year, now.month, now.day)) && e.day!.difference(DateTime(now.year, now.month, now.day)).inDays <= 3) e];
  if (today.isEmpty && classes.isEmpty && soon.isEmpty) return null;
  final lines = <String>[];
  if (today.isNotEmpty) lines.add('Due today: ${today.take(4).map((w) => '${_short(w.title, 30)} at ${_clock(w.due!)}').join('; ')}');
  if (classes.isNotEmpty) lines.add('Classes: ${classes.take(4).map((c) => '${c.start} ${_short(c.course, 26)}').join('; ')}');
  if (soon.isNotEmpty) lines.add('Exam soon: ${soon.take(2).map((e) => '${_short(e.title, 28)} ${_day(e.day!)}${e.time == null ? '' : ' ${e.time}'}').join('; ')}');
  final bits = [if (today.isNotEmpty) '${today.length} due', if (classes.isNotEmpty) '${classes.length} class${classes.length == 1 ? '' : 'es'}', if (soon.isNotEmpty) 'exam soon'];
  return (title: 'Today: ${bits.join(', ')}', body: lines.join('\n'));
}

// ------------------------------------------------------------------------------------------------ what changed
class Change {
  const Change(this.key, this.title, this.body);
  final String key;
  final String title, body;
}

/// What is new in [now] compared with [before]: announcements, assignments, extensions, marks, exam seats and grades.
/// The phone checks in the background and tells you about these.
List<Change> changesBetween(Summary before, Summary now) {
  final out = <Change>[];
  final oldNotes = {for (final n in before.announcements) n.id};
  for (final n in now.announcements) {
    if (!oldNotes.contains(n.id)) out.add(Change('note:${n.id}', 'New announcement: ${_short(n.title, 60)}', n.course));
  }
  final oldWork = {for (final w in before.work) w.id: w};
  for (final w in now.work) {
    final was = oldWork[w.id];
    final due = w.due == null ? '' : ', due ${_day(w.due!)} ${_clock(w.due!)}';
    if (was == null) {
      if (!w.submitted) out.add(Change('work:${w.id}', 'New assignment: ${_short(w.title, 60)}', '${w.course}$due'));
      continue;
    }
    if (w.extended && !was.extended) out.add(Change('ext:${w.id}', 'Deadline extended: ${_short(w.title, 60)}', '${w.course}, now ${w.due == null ? 'later' : '${_day(w.due!)} ${_clock(w.due!)}'}'));
    if ((was.marks ?? '').isEmpty && (w.marks ?? '').isNotEmpty) out.add(Change('marks:${w.id}', 'Marks posted: ${_short(w.title, 60)}', '${w.course}: ${w.marks}'));
  }
  final oldExams = {for (final e in before.exams) e.title: e};
  for (final e in now.exams) {
    final was = oldExams[e.title];
    if (e.scheduled && (was == null || !was.scheduled)) {
      out.add(Change('exam:${e.title}', 'Exam date posted: ${_short(e.title, 50)}', [if (e.day != null) _day(e.day!), if (e.time != null) e.time!, if (e.room != null) 'room ${e.room}', if (e.row != null && e.seat != null) 'row ${e.row}, seat ${e.seat}'].join(' · ')));
    } else if (was != null && was.scheduled && e.scheduled && (was.seat != e.seat || was.room != e.room) && e.seat != null) {
      out.add(Change('seat:${e.title}', 'Exam seat changed: ${_short(e.title, 50)}', 'room ${e.room ?? '–'}, row ${e.row ?? '–'}, seat ${e.seat}'));
    }
  }
  final oldGrades = <String, String?>{for (final t in before.terms) for (final c in t.courses) '${t.name}|${c.code}': c.grade};
  for (final t in now.terms) {
    for (final c in t.courses) {
      final k = '${t.name}|${c.code}';
      if (c.grade != null && oldGrades.containsKey(k) && oldGrades[k] == null) out.add(Change('grade:$k', 'Result posted: ${_short(c.title, 50)}', '${c.grade} (${t.name})'));
    }
  }
  return out;
}

/// At most [max] notifications; the rest are folded into one so a big change does not bury the phone.
List<AlertText> messagesFor(List<Change> changes, {int max = 4}) {
  if (changes.length <= max) return [for (final c in changes) (title: c.title, body: c.body)];
  return [
    for (final c in changes.take(max - 1)) (title: c.title, body: c.body),
    (title: '${changes.length - (max - 1)} more updates', body: changes.skip(max - 1).map((c) => c.title).take(6).join('\n')),
  ];
}

// ------------------------------------------------------------------------------------------------ calendar
String _esc(String s) => s.replaceAll('\\', '\\\\').replaceAll(';', '\\;').replaceAll(',', '\\,').replaceAll('\r', '').replaceAll('\n', '\\n');
String _stamp(DateTime d) => '${d.year.toString().padLeft(4, '0')}${d.month.toString().padLeft(2, '0')}${d.day.toString().padLeft(2, '0')}'
    'T${d.hour.toString().padLeft(2, '0')}${d.minute.toString().padLeft(2, '0')}${d.second.toString().padLeft(2, '0')}';
String _date(DateTime d) => '${d.year.toString().padLeft(4, '0')}${d.month.toString().padLeft(2, '0')}${d.day.toString().padLeft(2, '0')}';

/// RFC 5545 folding: lines over 75 octets continue on the next line after a space.
String _fold(String line) {
  final bytes = line.codeUnits;
  if (bytes.length <= 75) return line;
  final b = StringBuffer();
  var i = 0;
  var first = true;
  while (i < line.length) {
    final take = first ? 75 : 74;
    final end = (i + take) > line.length ? line.length : i + take;
    if (!first) b.write('\r\n ');
    b.write(line.substring(i, end));
    i = end;
    first = false;
  }
  return b.toString();
}

/// An .ics file with every open deadline (a 30 minute block ending at the deadline, with an alarm an hour before) and
/// every scheduled exam. Times are floating local times, so they land where the phone's calendar expects them.
String calendarIcs(Summary s, DateTime now) {
  final lines = <String>[
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Assignment Monitor//Phone//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    'X-WR-CALNAME:Assignment Monitor',
  ];
  void event(String uid, DateTime start, DateTime end, String summary, String description, {bool allDay = false, bool alarm = false}) {
    lines.addAll(['BEGIN:VEVENT', 'UID:$uid@assignment-monitor', 'DTSTAMP:${_stamp(now.toUtc())}Z']);
    if (allDay) {
      lines.addAll(['DTSTART;VALUE=DATE:${_date(start)}', 'DTEND;VALUE=DATE:${_date(start.add(const Duration(days: 1)))}']);
    } else {
      lines.addAll(['DTSTART:${_stamp(start)}', 'DTEND:${_stamp(end)}']);
    }
    lines.add('SUMMARY:${_esc(summary)}');
    if (description.isNotEmpty) lines.add('DESCRIPTION:${_esc(description)}');
    if (alarm) lines.addAll(['BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:${_esc(summary)}', 'TRIGGER:-PT1H', 'END:VALARM']);
    lines.add('END:VEVENT');
  }
  for (final w in s.work) {
    if (!w.todo || !w.open || w.due == null) continue;
    event('work-${w.id.hashCode.abs()}', w.due!.subtract(const Duration(minutes: 30)), w.due!, 'Due: ${w.title}', '${w.course}${w.number.isEmpty ? '' : ' · assignment ${w.number}'}', alarm: true);
  }
  for (final e in s.exams) {
    if (!e.scheduled || e.day == null) continue;
    final t = _examTime(e.time);
    final where = [if (e.room != null) 'Room ${e.room}', if (e.row != null && e.seat != null) 'row ${e.row}, seat ${e.seat}'].join(', ');
    if (t == null) {
      event('exam-${e.title.hashCode.abs()}', e.day!, e.day!, 'Exam: ${e.title}', where, allDay: true);
    } else {
      final start = DateTime(e.day!.year, e.day!.month, e.day!.day, t.$1, t.$2);
      event('exam-${e.title.hashCode.abs()}', start, start.add(const Duration(hours: 2)), 'Exam: ${e.title}', where, alarm: true);
    }
  }
  lines.add('END:VCALENDAR');
  return '${lines.map(_fold).join('\r\n')}\r\n';
}

/// "09:00 AM", "9:00", "2:30 pm" to (hour, minute), or null when it cannot be read.
(int, int)? _examTime(String? s) {
  final m = RegExp(r'^\s*(\d{1,2}):(\d{2})\s*([AaPp][Mm])?\s*$').firstMatch(s ?? '');
  if (m == null) return null;
  var h = int.parse(m.group(1)!);
  final min = int.parse(m.group(2)!);
  final ap = m.group(3)?.toLowerCase();
  if (ap == 'pm' && h < 12) h += 12;
  if (ap == 'am' && h == 12) h = 0;
  if (h > 23 || min > 59) return null;
  return (h, min);
}

// ------------------------------------------------------------------------------------------------ support info
/// What to paste into a bug report: versions, freshness and counts. No name, no course titles, no grades, no token.
String supportInfo(Summary? s, {required String platform, DateTime? lastRead, DateTime? now, String? error, int reminders = 0}) {
  final at = now ?? DateTime.now();
  String ago(DateTime? d) => d == null ? 'never' : agoLabel(at.difference(d));
  final b = StringBuffer()
    ..writeln('Assignment Monitor for phones $appVersion')
    ..writeln('Platform: $platform')
    ..writeln('Summary schema: ${s == null ? 'none' : (s.raw['schema'] ?? '?')}')
    ..writeln('Desktop app that made it: ${s?.raw['app_version'] ?? '?'}')
    ..writeln('Summary made: ${s == null ? 'never' : ago(s.generatedAt)}')
    ..writeln('Last read from GitHub: ${ago(lastRead)}')
    ..writeln('Counts: ${s?.work.length ?? 0} assignments, ${s?.attendance.length ?? 0} courses with attendance, ${s?.exams.length ?? 0} exams, '
        '${s?.timetable.length ?? 0} classes, ${s?.announcements.length ?? 0} announcements, ${s?.terms.length ?? 0} semesters')
    ..writeln('Reminders scheduled: $reminders')
    ..writeln('Last problem: ${error ?? 'none'}');
  return b.toString();
}

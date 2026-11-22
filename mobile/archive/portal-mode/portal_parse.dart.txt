/// The portal's HTML pages as data: a Dart port of campus.py, results.py, deadlines.py and the pure parts of
/// lms_scraper.py, function for function, so the phone can read the pages itself. Pure Dart (no Flutter, no network).
/// Output maps use the same keys as the Python dicts; dates are DateTime where Python returns datetime and ISO
/// strings where Python does (posted_at). Nothing here throws on empty or malformed HTML: it returns empty results.
/// The same HTML snippets are checked in tests/ (Python) and test/portal_parse_test.dart (Dart).
library;

import 'dart:convert';

import 'package:html/dom.dart';
import 'package:html/parser.dart' as html_parser;

typedef Json = Map<String, dynamic>;

// ---------------------------------------------------------------------------- small helpers
final _ws = RegExp(r'\s+');
final _percent = RegExp(r'(-?\d+(?:\.\d+)?)\s*%');
final _number = RegExp(r'-?\d+(?:\.\d+)?');
final _digits = RegExp(r'^[0-9]+$');

/// Whitespace collapsed to single spaces and trimmed (Python `_clean`).
String cleanText(String? text) => (text ?? '').replaceAll(_ws, ' ').trim();

/// The cleaned text of each direct `td` of a table row (Python `_cells`).
List<String> cellTexts(Element row) => [for (final c in _kids(row, const {'td'})) cleanText(c.text)];

/// The first number in [text], or [fallback] (Python campus `_num`).
double firstNumber(String? text, [double fallback = 0.0]) {
  final m = _number.firstMatch(text ?? '');
  return m == null ? fallback : double.parse(m.group(0)!);
}

Document? _doc(String? page) {
  try {
    return html_parser.parse(page ?? '');
  } catch (_) {
    return null;
  }
}

List<Element> _kids(Element e, Set<String> names) => [for (final c in e.children) if (names.contains(c.localName)) c];

bool _inTable(Element e, bool Function(Element) pred) {
  for (var p = e.parent; p != null; p = p.parent) {
    if (p.localName == 'table' && pred(p)) return true;
  }
  return false;
}

/// Rows (`tr`) that sit inside a table matching [pred] (XPath `//table[...]//tr`), in document order.
List<Element> _rows(Document? d, [bool Function(Element) pred = _anyTable]) =>
    d == null ? const [] : [for (final tr in d.querySelectorAll('tr')) if (_inTable(tr, pred)) tr];

bool _anyTable(Element _) => true;

bool _isDigits(String s) => _digits.hasMatch(s);

// Python str.isupper() / str.title(), which the teacher names rely on.
bool _isUpper(String s) => s == s.toUpperCase() && s != s.toLowerCase();

String _title(String s) {
  final b = StringBuffer();
  var inWord = false;
  for (final r in s.runes) {
    final ch = String.fromCharCode(r);
    if (ch.toLowerCase() != ch.toUpperCase()) {
      b.write(inWord ? ch.toLowerCase() : ch.toUpperCase());
      inWord = true;
    } else {
      b.write(ch);
      inWord = false;
    }
  }
  return b.toString();
}

String _stripChars(String s, String chars, {bool left = true, bool right = true}) {
  var a = 0, z = s.length;
  if (left) while (a < z && chars.contains(s[a])) {a++;}
  if (right) while (z > a && chars.contains(s[z - 1])) {z--;}
  return s.substring(a, z);
}

/// Python round(x, n) for n 1 or 2: exact ties go to the even digit, which toStringAsFixed would not do.
double _round(double x, int n) {
  if (!x.isFinite) return x;
  final tie = x * (1 << (n + 1));
  if (tie == tie.truncateToDouble() && tie.abs() % 2 == 1) {
    var p = 1.0;
    for (var i = 0; i < n; i++) {
      p *= 10;
    }
    final scaled = x * p, lo = scaled.floorToDouble();
    return (lo % 2 == 0 ? lo : lo + 1) / p;
  }
  return double.parse(x.toStringAsFixed(n));
}

/// Dart's List.sort is not guaranteed stable; Python's is.
List<T> _stableSorted<T>(Iterable<T> items, int Function(T, T) cmp) {
  final indexed = items.toList().asMap().entries.toList();
  indexed.sort((a, b) {
    final c = cmp(a.value, b.value);
    return c != 0 ? c : a.key.compareTo(b.key);
  });
  return [for (final e in indexed) e.value];
}

const _monthNames = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];

/// A month number from a full name or, failing that, its first three letters (strptime %B, then %b); 0 if neither.
int _monthOf(String name) {
  final n = name.toLowerCase();
  final full = _monthNames.indexOf(n);
  if (full >= 0) return full + 1;
  if (n.length < 3) return 0;
  return _monthNames.indexWhere((m) => m.startsWith(n.substring(0, 3))) + 1;
}

/// A DateTime only when the parts form a real date and time (datetime() raises otherwise).
DateTime? _mk(int y, int mo, int d, [int h = 0, int mi = 0, int s = 0]) {
  if (y < 1 || mo < 1 || mo > 12 || d < 1 || h < 0 || h > 23 || mi < 0 || mi > 59 || s < 0 || s > 59) return null;
  final dt = DateTime(y, mo, d, h, mi, s);
  return dt.month == mo && dt.day == d ? dt : null;
}

int _hour12(int h, String meridiem) => h % 12 + (meridiem.toLowerCase() == 'pm' ? 12 : 0);

String _p2(int n) => n.toString().padLeft(2, '0');

/// Python's urllib.parse.unquote: %XX runs decoded as UTF-8 (bad bytes replaced), malformed escapes left alone.
String _unquote(String s) => s.replaceAllMapped(RegExp(r'(?:%[0-9A-Fa-f]{2})+'), (m) {
      final t = m.group(0)!;
      final bytes = [for (var i = 0; i < t.length; i += 3) int.parse(t.substring(i + 1, i + 3), radix: 16)];
      return utf8.decode(bytes, allowMalformed: true);
    });

/// Python's lenient base64.b64decode: characters outside the alphabet are skipped, parsing stops at complete
/// padding, and null means it would have raised.
List<int>? _b64decode(String s) {
  if (s.runes.any((r) => r > 127)) return null;
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  final out = <int>[];
  var quad = 0, left = 0, pads = 0;
  for (var i = 0; i < s.length; i++) {
    final ch = s[i];
    if (ch == '=') {
      if (quad >= 2 && quad + ++pads >= 4) {
        quad = 0;
        return out;
      }
      continue;
    }
    final v = alphabet.indexOf(ch);
    if (v < 0) continue;
    pads = 0;
    switch (quad) {
      case 0:
        quad = 1;
        left = v;
      case 1:
        quad = 2;
        out.add(((left << 2) | (v >> 4)) & 0xff);
        left = v & 0x0f;
      case 2:
        quad = 3;
        out.add(((left << 4) | (v >> 2)) & 0xff);
        left = v & 0x03;
      default:
        quad = 0;
        out.add(((left << 6) | v) & 0xff);
        left = 0;
    }
  }
  return quad == 0 ? out : null;
}

/// base64 of the key padded the way the Python callers do, decoded as UTF-8 text; null when it cannot be read.
String? _decodeKey(String raw) {
  final bytes = _b64decode(raw + '=' * ((4 - raw.length % 4) % 4));
  return bytes == null ? null : utf8.decode(bytes, allowMalformed: true);
}

/// SHA-1 as lower-case hex (hashlib.sha1(...).hexdigest()); the record ids must equal the desktop's.
String sha1Hex(String text) {
  const mask = 0xFFFFFFFF;
  int rotl(int x, int n) => ((x << n) | (x >> (32 - n))) & mask;
  final bytes = utf8.encode(text);
  final padded = <int>[...bytes, 0x80];
  while (padded.length % 64 != 56) {
    padded.add(0);
  }
  final bits = bytes.length * 8;
  for (var i = 7; i >= 0; i--) {
    padded.add((bits >> (i * 8)) & 0xff);
  }
  var h0 = 0x67452301, h1 = 0xEFCDAB89, h2 = 0x98BADCFE, h3 = 0x10325476, h4 = 0xC3D2E1F0;
  final w = List<int>.filled(80, 0);
  for (var off = 0; off < padded.length; off += 64) {
    for (var i = 0; i < 16; i++) {
      final j = off + i * 4;
      w[i] = (padded[j] << 24) | (padded[j + 1] << 16) | (padded[j + 2] << 8) | padded[j + 3];
    }
    for (var i = 16; i < 80; i++) {
      w[i] = rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
    }
    var a = h0, b = h1, c = h2, d = h3, e = h4;
    for (var i = 0; i < 80; i++) {
      final int f, k;
      if (i < 20) {
        f = (b & c) | (~b & mask & d);
        k = 0x5A827999;
      } else if (i < 40) {
        f = b ^ c ^ d;
        k = 0x6ED9EBA1;
      } else if (i < 60) {
        f = (b & c) | (b & d) | (c & d);
        k = 0x8F1BBCDC;
      } else {
        f = b ^ c ^ d;
        k = 0xCA62C1D6;
      }
      final t = (rotl(a, 5) + f + e + k + w[i]) & mask;
      e = d;
      d = c;
      c = rotl(b, 30);
      b = a;
      a = t;
    }
    h0 = (h0 + a) & mask;
    h1 = (h1 + b) & mask;
    h2 = (h2 + c) & mask;
    h3 = (h3 + d) & mask;
    h4 = (h4 + e) & mask;
  }
  return [h0, h1, h2, h3, h4].map((h) => h.toRadixString(16).padLeft(8, '0')).join();
}

// ---------------------------------------------------------------------------- attendance
/// The CMS 'Attendance' page: one row per registered course with present/absent/total hours and a 'Detail' link.
List<Json> parseAttendance(String pageHtml) {
  final out = <Json>[];
  for (final row in _rows(_doc(pageHtml))) {
    final cells = cellTexts(row);
    if (cells.length < 12 || cells[1].isEmpty || cells[0] == '#') continue;
    final presentTxt = cells[9];
    final present = firstNumber(presentTxt), absent = firstNumber(cells[10]), total = firstNumber(cells[11]);
    final m = _percent.firstMatch(presentTxt);
    final percent = m != null ? double.parse(m.group(1)!) : (total != 0 ? _round(present / total * 100, 2) : 0.0);
    final links = row.querySelectorAll('a[href]');
    out.add({
      'code': cells[1],
      'title': cells[2],
      'credit_hours': cells[3],
      'class': cells[6],
      'teacher': _isUpper(cells[7]) ? _title(cells[7]) : cells[7],
      'fee_status': cells[8],
      'present': present,
      'absent': absent,
      'total': total,
      'percent': percent,
      'detail_url': links.isEmpty ? '' : links.first.attributes['href'] ?? '',
    });
  }
  return out;
}

/// The CMS 'Attendance Summary' page for one course: course info plus one row per class held.
Json parseAttendanceDetail(String pageHtml) {
  final d = _doc(pageHtml);
  final info = <String, String>{};
  for (final row in _rows(d, (t) => !(t.attributes['id'] ?? '').contains('AttendanceDetails'))) {
    final cells = [for (final c in _kids(row, const {'th', 'td'})) cleanText(c.text)];
    for (var i = 0; i < cells.length - 1; i += 2) {
      if (cells[i].isNotEmpty) info[cells[i].toLowerCase().replaceAll(' ', '_')] = cells[i + 1];
    }
  }
  final sessions = <Json>[];
  for (final row in _rows(d, (t) => (t.attributes['id'] ?? '').contains('AttendanceDetails'))) {
    final cells = cellTexts(row);
    if (cells.length < 8 || !_isDigits(cells[0])) continue;
    var remarks = '', topics = '';
    final m = RegExp(r'Remarks:\s*(.*?)\s*Topics Covered:\s*(.*)$', caseSensitive: false, dotAll: true).firstMatch(cells[4]);
    if (m != null) {
      remarks = m.group(1)!.trim();
      topics = m.group(2)!.trim();
    } else {
      topics = cells[4];
    }
    sessions.add({
      'date': cells[1],
      'type': cells[2],
      'room': cells[3],
      'remarks': remarks.toUpperCase() == 'N/A' ? '' : remarks,
      'topics': topics,
      'hours': firstNumber(cells[5]),
      'present': firstNumber(cells[6]),
      'absent': firstNumber(cells[7]),
    });
  }
  return {'title': info['title'] ?? '', 'teacher': info['teacher_name'] ?? '', 'contact_hours': info['contact_hours'] ?? '', 'sessions': sessions};
}

/// How far a course is from the minimum percentage. can_miss: hours that can still be missed while staying at or
/// above the minimum. need: consecutive present hours required to get back to it (0 when already there).
Json attendanceMargin(double present, double total, double minimum) {
  if (total <= 0) return {'percent': 0.0, 'can_miss': 0.0, 'need': 0.0, 'ok': true};
  final pct = present / total * 100, frac = minimum / 100.0;
  if (pct >= minimum) {
    final canMiss = frac > 0 ? present / frac - total : double.infinity;
    final r = _round(canMiss, 1);
    return {'percent': _round(pct, 2), 'can_miss': r > 0 ? r : 0.0, 'need': 0.0, 'ok': true};
  }
  final need = frac < 1 ? (frac * total - present) / (1 - frac) : double.infinity;
  return {'percent': _round(pct, 2), 'can_miss': 0.0, 'need': _round(need, 1), 'ok': false};
}

/// 'Monday, 31 August 2026' -> DateTime, or null.
DateTime? sessionDate(String? text) {
  final m = RegExp(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})').firstMatch(text ?? '');
  if (m == null) return null;
  final mo = _monthOf(m.group(2)!);
  return mo == 0 ? null : _mk(int.parse(m.group(3)!), mo, int.parse(m.group(1)!));
}

// ---------------------------------------------------------------------------- exams
/// The CMS 'Exam Seating Plan' grid for one exam type. Unscheduled courses have an empty date.
List<Json> parseExamSeats(String pageHtml, [String examType = '']) {
  final out = <Json>[];
  for (final row in _rows(_doc(pageHtml), (t) => (t.attributes['id'] ?? '').contains('ExamSeats'))) {
    final cells = cellTexts(row);
    if (cells.length < 12 || !_isDigits(cells[0])) continue;
    String na(String v) => v.toUpperCase() == 'N/A' ? '' : v;
    final item = <String, dynamic>{
      'title': cells[1], 'class': cells[2], 'date': cells[3], 'session': cells[4], 'start_time': cells[5],
      'room': na(cells[6]), 'row': na(cells[7]), 'column': na(cells[8]), 'status': na(cells[9]),
      'fee_defaulter': cells[10].toLowerCase().startsWith('y'), 'surveys': cells[11], 'exam_type': examType,
    };
    item['id'] = '$examType#${item['title']}'.replaceAll(' ', '_');
    item['scheduled'] = (item['date'] as String).isNotEmpty;
    out.add(item);
  }
  return out;
}

/// '26/10/2026' + '09:00 AM' -> DateTime (date only when the time is missing), or null.
DateTime? examDatetime(Json exam) {
  final d = (exam['date'] ?? '').toString().trim();
  if (d.isEmpty) return null;
  final t = (exam['start_time'] ?? '').toString().trim();
  final both = '$d $t'.trim();
  final dm = RegExp(r'^(\d{1,2})/(\d{1,2})/(\d{4})');
  // %d/%m/%Y %I:%M %p, then %H:%M, then the date alone; the whole string must be consumed
  var m = RegExp(r'^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{1,2})\s+(am|pm)$', caseSensitive: false).firstMatch(both);
  if (m != null) {
    final h = int.parse(m.group(4)!);
    if (h >= 1 && h <= 12) {
      final r = _mk(int.parse(m.group(3)!), int.parse(m.group(2)!), int.parse(m.group(1)!), _hour12(h, m.group(6)!), int.parse(m.group(5)!));
      if (r != null) return r;
    }
  }
  m = RegExp(r'^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{1,2})$').firstMatch(both);
  if (m != null) {
    final r = _mk(int.parse(m.group(3)!), int.parse(m.group(2)!), int.parse(m.group(1)!), int.parse(m.group(4)!), int.parse(m.group(5)!));
    if (r != null) return r;
  }
  m = dm.firstMatch(d);
  if (m != null && m.end == d.length) return _mk(int.parse(m.group(3)!), int.parse(m.group(2)!), int.parse(m.group(1)!));
  return null;
}

int _daysBetween(DateTime a, DateTime b) => DateTime.utc(a.year, a.month, a.day).difference(DateTime.utc(b.year, b.month, b.day)).inDays;

/// Scheduled exams from today onwards, soonest first, each with 'when' (DateTime) and 'days' attached.
List<Json> upcomingExams(List<Json> exams, [DateTime? now]) {
  now ??= DateTime.now();
  final out = <Json>[];
  for (final e in exams) {
    final dt = examDatetime(e);
    if (dt == null) continue;
    final days = _daysBetween(dt, now);
    if (days < 0) continue;
    out.add({...e, 'when': dt, 'days': days});
  }
  return _stableSorted(out, (a, b) => (a['when'] as DateTime).compareTo(b['when'] as DateTime));
}

String seatText(Json exam) {
  final bits = <String>[];
  final room = (exam['room'] ?? '').toString(), row = (exam['row'] ?? '').toString(), col = (exam['column'] ?? '').toString();
  if (room.isNotEmpty) bits.add('Room $room');
  if (row.isNotEmpty && col.isNotEmpty) bits.add('row $row, seat $col');
  return bits.join(' · ');
}

// ---------------------------------------------------------------------------- announcements
/// The LMS 'Announcements' table for one course.
List<Json> parseAnnouncements(String pageHtml, String course) {
  final out = <Json>[];
  for (final row in _rows(_doc(pageHtml))) {
    final cells = cellTexts(row);
    if (cells.length < 4 || !_isDigits(cells[0])) continue;
    final title = cells[1], text = cells[2], posted = cells[3];
    if (text.isEmpty && title.isEmpty) continue;
    out.add({
      'id': sha1Hex('$course|$title|$text|$posted').substring(0, 12),
      'course': course,
      'title': title,
      'text': text,
      'posted': posted,
      'posted_at': postedIso(posted),
    });
  }
  return out;
}

/// '28-09-2026 11:27:40am' -> '2026-09-28T11:27:40', or '' when unparseable.
String postedIso(String? text) {
  final t = (text ?? '').trim().toLowerCase().replaceAll('am', ' am').replaceAll('pm', ' pm').replaceAll(_ws, ' ');
  for (final re in [
    RegExp(r'^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})\s+(am|pm)$'),
    RegExp(r'^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{1,2})()\s+(am|pm)$'),
    RegExp(r'^(\d{1,2})-(\d{1,2})-(\d{4})()()()()$'),
  ]) {
    final m = re.firstMatch(t);
    if (m == null) continue;
    final hasTime = m.group(4)!.isNotEmpty;
    var h = 0;
    if (hasTime) {
      final h12 = int.parse(m.group(4)!);
      if (h12 < 1 || h12 > 12) continue;
      h = _hour12(h12, m.group(7)!);
    }
    final s = (m.group(6) ?? '').isEmpty ? 0 : int.parse(m.group(6)!);
    final mi = (m.group(5) ?? '').isEmpty ? 0 : int.parse(m.group(5)!);
    final dt = _mk(int.parse(m.group(3)!), int.parse(m.group(2)!), int.parse(m.group(1)!), h, mi, s);
    if (dt == null) continue;
    return '${dt.year.toString().padLeft(4, '0')}-${_p2(dt.month)}-${_p2(dt.day)}T${_p2(dt.hour)}:${_p2(dt.minute)}:${_p2(dt.second)}';
  }
  return '';
}

// ---------------------------------------------------------------------------- lecture notes
final _safe = RegExp(r'[^A-Za-z0-9 ._()&+-]+');

/// A file-system-safe version of a course or lecture title.
String safeName(String? text, [int limit = 80]) {
  var t = _stripChars((text ?? '').replaceAll(_safe, ' '), ' .');
  t = t.replaceAll(_ws, ' ');
  if (t.length > limit) t = t.substring(0, limit);
  t = _stripChars(t, ' .', left: false);
  return t.isEmpty ? 'untitled' : t;
}

/// The LMS download links carry the original file name inside their base64 'k' parameter
/// (...,Lec-1-Intro-28092026-012454pm.pptx,...). Returns '' when it cannot be read.
String filenameFromLink(String? href) {
  final m = RegExp(r'[?&]k=([^&]+)').firstMatch(href ?? '');
  if (m == null) return '';
  final decoded = _decodeKey(_unquote(m.group(1)!));
  if (decoded == null) return '';
  final ext = RegExp(r'\.[A-Za-z0-9]{2,5}$');
  for (var part in decoded.split(',')) {
    part = part.trim();
    if (ext.hasMatch(part) && !part.contains('/')) return safeName(part, 120);
  }
  return '';
}

/// The LMS 'Lecture Notes' table for one course: one row per week with its files and video links.
List<Json> parseLectures(String pageHtml, String course) {
  final out = <Json>[];
  for (final row in _rows(_doc(pageHtml))) {
    final tds = _kids(row, const {'td'});
    final cells = [for (final c in tds) cleanText(c.text)];
    if (cells.length < 6 || cells[1].isEmpty) continue;
    final week = cells[0], title = cells[1];
    final files = <Json>[];
    var i = 0;
    for (final a in tds[2].querySelectorAll('a[href]')) {
      i++;
      final href = a.attributes['href'] ?? '';
      if (href.isEmpty || href.startsWith('#')) continue;
      final label = cleanText(a.text);
      final name = filenameFromLink(href);
      files.add({'label': label.isEmpty ? 'File $i' : label, 'href': href, 'filename': name.isEmpty ? '${safeName(title)} ($i)' : name});
    }
    final videos = <String>[
      for (final td in tds.sublist(3, 5)) for (final a in td.querySelectorAll('a[href]')) if ((a.attributes['href'] ?? '').isNotEmpty) a.attributes['href']!,
    ];
    if (files.isEmpty && videos.isEmpty) continue;
    out.add({
      'id': sha1Hex('$course|$week|$title|${files.length}').substring(0, 12),
      'course': course, 'week': week, 'title': title, 'files': files, 'videos': videos, 'remarks': cells[5],
    });
  }
  return out;
}

// ---------------------------------------------------------------------------- timetable
const dayOrder = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
final _ttRange = RegExp(r'(\d{1,2}:\d{2})\s*([AP]M)\s*-\s*(\d{1,2}:\d{2})\s*([AP]M)', caseSensitive: false);
final _semester = RegExp(r'^(Spring|Fall|Summer)-\d{4}$');

/// '01:30' + 'PM' -> '13:30'.
String to24h(String hhmm, String ampm) {
  final p = hhmm.split(':');
  return '${_p2(_hour12(int.parse(p[0]), ampm))}:${p[1]}';
}

/// '13:30' -> 810.
int minutes(String hhmm) {
  final p = hhmm.split(':');
  return int.parse(p[0]) * 60 + int.parse(p[1]);
}

Iterable<Text> _textNodes(Node n) sync* {
  for (final c in n.nodes) {
    if (c is Text) {
      yield c;
    } else {
      yield* _textNodes(c);
    }
  }
}

/// The CMS 'Time Table' page: one row per day; every class is a td.event whose inner div's title attribute holds
/// the course, teacher, class, room and the time range, one per line. Returns {"semester", "sessions": [...]} with
/// sessions sorted by day then start, times as 24-hour 'HH:MM'.
Json parseTimetable(String pageHtml) {
  final d = _doc(pageHtml);
  if (d == null) return {'semester': '', 'sessions': <Json>[]};
  var semester = '';
  for (final t in _textNodes(d)) {
    final s = cleanText(t.data);
    if (_semester.hasMatch(s)) {
      semester = s;
      break;
    }
  }
  final sessions = <Json>[];
  for (final row in _rows(d, (t) => t.attributes['id'] == 'timeTable')) {
    final cells = _kids(row, const {'td', 'th'});
    if (cells.isEmpty) continue;
    final first = cleanText(cells[0].text);
    final day = _title(first.length > 3 ? first.substring(0, 3) : first);
    if (!dayOrder.contains(day)) continue;
    for (final td in _kids(row, const {'td'}).where((c) => (c.attributes['class'] ?? '').contains('event'))) {
      final box = [for (final c in td.children) if (c.localName == 'div' && c.attributes.containsKey('title')) c];
      final title = box.isEmpty ? '' : box.first.attributes['title'] ?? '';
      final lines = [for (final ln in title.split('\n')) if (ln.trim().isNotEmpty) ln.trim()];
      final m = _ttRange.firstMatch(title);
      if (m == null) continue;
      String sub(String cls) {
        for (final div in td.querySelectorAll('div')) {
          if (!(div.attributes['class'] ?? '').contains(cls)) continue;
          final spans = div.querySelectorAll('span');
          if (spans.isNotEmpty) return cleanText(spans.first.text);
        }
        return '';
      }

      final teacher = lines.length > 1 ? lines[1] : '';
      sessions.add({
        'day': day,
        'start': to24h(m.group(1)!, m.group(2)!),
        'end': to24h(m.group(3)!, m.group(4)!),
        'course': lines.isNotEmpty ? lines[0] : sub('title'),
        'abbr': sub('title'),
        'teacher': _isUpper(teacher) ? _title(teacher) : teacher,
        'initials': sub('facultyMember'),
        'class': lines.length > 2 ? lines[2] : sub('class'),
        'room': sub('room').isNotEmpty ? sub('room') : (lines.length > 3 ? lines[3] : ''),
      });
    }
  }
  final sorted = _stableSorted(sessions, (a, b) {
    final c = dayOrder.indexOf(a['day']).compareTo(dayOrder.indexOf(b['day']));
    return c != 0 ? c : (a['start'] as String).compareTo(b['start'] as String);
  });
  // the portal splits one class into back-to-back slots now and then; join them
  final merged = <Json>[];
  for (final x in sorted) {
    final last = merged.isEmpty ? null : merged.last;
    if (last != null && last['day'] == x['day'] && last['course'] == x['course'] && last['room'] == x['room'] && last['class'] == x['class'] && last['end'] == x['start']) {
      last['end'] = x['end'];
    } else {
      merged.add({...x});
    }
  }
  return {'semester': semester, 'sessions': merged};
}

/// The classes of one weekday ('Mon'...'Sun'), in order.
List<Json> sessionsOn(List<Json> sessions, String day) => [for (final x in sessions) if (x['day'] == day) x];

// ---------------------------------------------------------------------------- miscellaneous files
/// The LMS 'Miscellaneous' table for one course, in the lecture-record shape (one record per file, week 0,
/// title = the type, kind 'misc') so the same screens and downloader can treat them like lecture notes.
List<Json> parseMisc(String pageHtml, String course) {
  final out = <Json>[];
  for (final row in _rows(_doc(pageHtml))) {
    final cells = _kids(row, const {'td'});
    if (cells.length < 3 || !_isDigits(cleanText(cells[0].text))) continue;
    final kind = cleanText(cells[1].text).isEmpty ? 'File' : cleanText(cells[1].text);
    final remarks = cells.length > 3 ? cleanText(cells[3].text) : '';
    final files = <Json>[];
    for (final a in cells[2].querySelectorAll('a[href]')) {
      final href = a.attributes['href'] ?? '';
      if (!href.contains('Download.php')) continue;
      final name = filenameFromLink(href);
      files.add({'label': name.isEmpty ? cleanText(a.text) : name, 'href': href, 'filename': name});
    }
    if (files.isEmpty) continue;
    final f0 = files.first;
    final seed = '$course|misc|$kind|${(f0['filename'] as String).isNotEmpty ? f0['filename'] : f0['href']}';
    out.add({
      'id': sha1Hex(seed).substring(0, 16), 'kind': 'misc', 'course': course, 'week': 0, 'title': kind,
      'files': files, 'videos': <String>[], 'remarks': remarks,
    });
  }
  return out;
}

// ---------------------------------------------------------------------------- results
/// The letter scale as the portal prints it (grade points per credit hour).
const gradeScale = <String, double>{
  'A': 4.0, 'A-': 3.67, 'B+': 3.33, 'B': 3.0, 'B-': 2.67, 'C+': 2.33, 'C': 2.0, 'C-': 1.67, 'D+': 1.33, 'D': 1.0, 'F': 0.0,
};

/// float(text) after cleaning, null when it is not a plain decimal number (results.py `_num`).
double? _fnum(String? text) {
  final t = cleanText(text);
  if (!RegExp(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$').hasMatch(t)) return null;
  return double.tryParse(t.endsWith('.') ? '${t}0' : t.replaceFirst('.e', '.0e').replaceFirst('.E', '.0E'));
}

/// What `table.findtext("caption")` gives: the text before the caption's first child element.
String _leadText(Element e) {
  final b = StringBuffer();
  for (final n in e.nodes) {
    if (n is! Text) break;
    b.write(n.data);
  }
  return b.toString();
}

/// {"student": {...}, "semesters": [{"name", "courses": [...], "gpa", "cgpa", "complete"}]} from the Provisional
/// Result page. Semesters come in the portal's order (oldest first). gpa/cgpa are the portal's own printed figures
/// (null while the semester is running); each course has credits, grade, points, product.
Json parseResults(String pageHtml) {
  final doc = _doc(pageHtml);
  final student = <String, String>{};
  final semesters = <Json>[];
  if (doc == null) return {'student': student, 'semesters': semesters};
  bool hasCaption(Element t) => t.children.any((c) => c.localName == 'caption');
  final tables = doc.querySelectorAll('table');
  for (final table in tables.where((t) => !hasCaption(t))) {
    for (final row in table.querySelectorAll('tr')) {
      final cells = [for (final c in _kids(row, const {'td', 'th'})) cleanText(c.text)];
      for (var i = 0; i < cells.length - 1; i += 2) {
        final key = _stripChars(cells[i].toLowerCase(), ':', left: false);
        if (const {'program', 'intake semester', 'name', 'enrollment', 'status'}.contains(key)) {
          student[key.replaceAll(' ', '_')] = cells[i + 1];
        }
      }
    }
  }
  for (final table in tables.where(hasCaption)) {
    final name = cleanText(_leadText(table.children.firstWhere((c) => c.localName == 'caption')));
    final courses = <Json>[];
    double? gpa, cgpa;
    for (final row in table.querySelectorAll('tr')) {
      final tds = _kids(row, const {'td'});
      if (tds.length == 1 && tds[0].text.contains('GPA')) {
        final m = RegExp(r'GPA:\s*([\d.]+|N/A)\s*,\s*CGPA:\s*([\d.]+|N/A)').firstMatch(cleanText(tds[0].text));
        if (m != null) {
          gpa = _fnum(m.group(1));
          cgpa = _fnum(m.group(2));
        }
        continue;
      }
      if (tds.length < 8) continue;
      final cells = [for (final c in tds) cleanText(c.text)];
      final credits = _fnum(cells[4]);
      if (credits == null) continue;
      final grade = cells[5].isNotEmpty && cells[5] != 'N/A' ? cells[5] : '';
      var points = grade.isNotEmpty ? _fnum(cells[6]) : null;
      if (grade.isNotEmpty && points == null) points = gradeScale[grade];
      courses.add({
        'code': cells[1], 'title': cells[2], 'credits': credits, 'grade': grade, 'points': points,
        'product': grade.isNotEmpty ? _fnum(cells[7]) : null,
      });
    }
    if (courses.isEmpty) continue;
    semesters.add({'name': name, 'courses': courses, 'gpa': gpa, 'cgpa': cgpa, 'complete': courses.every((c) => (c['grade'] as String).isNotEmpty)});
  }
  return {'student': student, 'semesters': semesters};
}

bool _counted(Json c) => (c['grade'] ?? '').toString().isNotEmpty && c['points'] != null;

/// Credit-weighted average of the graded courses, null when nothing is graded.
double? gpaOf(List<Json> courses) {
  final graded = courses.where(_counted).toList();
  final credits = graded.fold<double>(0, (n, c) => n + (c['credits'] as num));
  if (credits == 0) return null;
  final points = graded.fold<double>(0, (n, c) => n + (c['credits'] as num) * (c['points'] as num));
  return _round(points / credits, 2);
}

/// Cumulative figures over every graded course: credits attempted, credits earned (grade above F), points, cgpa.
Json totals(List<Json> semesters) {
  double credits = 0, earned = 0, points = 0;
  for (final s in semesters) {
    for (final c in (s['courses'] as List).cast<Json>()) {
      if (_counted(c)) {
        credits += c['credits'] as num;
        points += (c['credits'] as num) * (c['points'] as num);
        if (c['grade'] != 'F') earned += c['credits'] as num;
      }
    }
  }
  return {'credits': credits, 'earned': earned, 'points': points, 'cgpa': credits != 0 ? _round(points / credits, 2) : null};
}

/// The semester still waiting for grades (the last incomplete one), or null.
Json? currentSemester(List<Json> semesters) {
  for (final s in semesters.reversed) {
    if (s['complete'] != true) return s;
  }
  return null;
}

int gradedCount(Json semester) => [for (final c in (semester['courses'] as List? ?? const [])) if (((c as Map)['grade'] ?? '').toString().isNotEmpty) c].length;

// ---------------------------------------------------------------------------- deadlines
final _splitRe = RegExp(r'(?<=[ap]m)(?=[0-9])', caseSensitive: false);
final _dateRe = RegExp(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})');
final _timeRe = RegExp(r'(\d{1,2}):(\d{2})\s*([ap]m)', caseSensitive: false);

/// Bahria LMS concatenates an extended deadline with the original one, e.g.
/// '28 September 2026 - 12:00 am22 September 2026-12:00 am'. Returns (active, isExtended, original).
(String, bool, String) parseDeadline(String? rawDeadline) {
  final raw = (rawDeadline ?? '').trim();
  if (raw.isEmpty) return ('N/A', false, '');
  final parts = <String>[];
  var from = 0;
  for (final m in _splitRe.allMatches(raw)) {
    parts.add(raw.substring(from, m.start));
    from = m.start;
  }
  parts.add(raw.substring(from));
  if (parts.length >= 2) return (parts[0].trim(), true, parts[1].trim());
  return (raw, false, '');
}

/// Parses '17 October 2026 - 11:30 pm' or '17 October 2026-11:30 pm' into a DateTime (23:59 without a time).
DateTime? parseDeadlineDatetime(String? raw) {
  if (raw == null || raw.isEmpty) return null;
  final md = _dateRe.firstMatch(raw);
  if (md == null) return null;
  final mo = _monthOf(md.group(2)!);
  if (mo == 0) return null;
  var hour = 23, minute = 59;
  final mt = _timeRe.firstMatch(raw);
  if (mt != null) {
    var h = int.parse(mt.group(1)!);
    minute = int.parse(mt.group(2)!);
    final mer = mt.group(3)!.toLowerCase();
    if (mer == 'pm' && h < 12) {
      h += 12;
    } else if (mer == 'am' && h == 12) {
      h = 0;
    }
    hour = h;
  }
  return _mk(int.parse(md.group(3)!), mo, int.parse(md.group(1)!), hour, minute);
}

DateTime? deadlineOf(Json item) => parseDeadlineDatetime((item['due_date'] ?? '').toString());

int? daysUntil(DateTime? dt, [DateTime? now]) => dt == null ? null : _daysBetween(dt, now ?? DateTime.now());

/// Pending means not submitted and the portal has not marked the deadline as exceeded.
bool isOpenPending(Json item) => item['is_submitted'] != true && !(item['status'] ?? '').toString().toLowerCase().contains('exceeded');

/// {'key', 'label', 'days'} where key is one of submitted | missed | today | soon | week | later | unknown.
Json classify(Json item, [DateTime? now]) {
  now ??= DateTime.now();
  final dt = deadlineOf(item);
  final days = daysUntil(dt, now);
  var timeTxt = '';
  if (dt != null) {
    final h = dt.hour % 12 == 0 ? 12 : dt.hour % 12;
    timeTxt = '$h:${_p2(dt.minute)} ${dt.hour < 12 ? 'am' : 'pm'}';
  }
  if (item['is_submitted'] == true) return {'key': 'submitted', 'label': 'Submitted', 'days': days};
  if ((item['status'] ?? '').toString().toLowerCase().contains('exceeded') || (dt != null && dt.isBefore(now))) {
    return {'key': 'missed', 'label': 'Overdue', 'days': days};
  }
  if (dt == null || days == null) return {'key': 'unknown', 'label': 'No deadline', 'days': null};
  if (days == 0) return {'key': 'today', 'label': 'Due today at $timeTxt', 'days': 0};
  if (days == 1) return {'key': 'soon', 'label': 'Due tomorrow at $timeTxt', 'days': 1};
  if (days <= 3) return {'key': 'soon', 'label': 'Due in $days days', 'days': days};
  if (days <= 7) return {'key': 'week', 'label': 'Due in $days days', 'days': days};
  return {'key': 'later', 'label': 'Due in $days days', 'days': days};
}

/// Sorts open work first by nearest deadline, then everything else by latest deadline. Compare the records
/// (group first, then stamp); [compareSortKeys] does that.
(int, double) sortKey(Json item) {
  final dt = deadlineOf(item);
  final stamp = dt == null ? double.infinity : dt.millisecondsSinceEpoch / 1000.0;
  if (isOpenPending(item)) return (0, stamp);
  return (1, dt != null ? -stamp : double.infinity);
}

int compareSortKeys((int, double) a, (int, double) b) => a.$1 != b.$1 ? a.$1.compareTo(b.$1) : a.$2.compareTo(b.$2);

// ---------------------------------------------------------------------------- assignments (lms_scraper.py)
/// The LMS download link carries a base64 key 'id,date,kind,0,filename,page'. Returns {date, kind, filename} or {}
/// when the link is not of that shape.
Map<String, String> decodeDownloadKey(String? href) {
  final h = href ?? '';
  final at = h.indexOf('k=');
  if (at < 0) return {};
  final decoded = _decodeKey(_unquote(h.substring(at + 2)));
  if (decoded == null) return {};
  final parts = decoded.split(',');
  return parts.length >= 5 ? {'date': parts[1], 'kind': parts[2], 'filename': parts[4]} : {};
}

/// The files linked from an assignment row: the brief (and a solution once posted) in the third column, the
/// student's own submission in the fourth, the returned submission in the sixth. Links expire daily, so they are
/// re-read at download time; the file name comes from the link's key. [tds] are the row's td elements.
Map<String, Map<String, String>> assignmentFiles(List<Element> tds) {
  final out = <String, Map<String, String>>{};
  if (tds.length < 6) return out;
  void add(String kind, Element a) {
    final href = a.attributes['href'] ?? '';
    if (!href.contains('Download')) return;
    out[kind] = {'href': href, 'label': cleanText(a.text), 'filename': decodeDownloadKey(href)['filename'] ?? ''};
  }

  for (final a in tds[2].querySelectorAll('a[href]')) {
    add(a.text.toLowerCase().contains('solution') ? 'solution' : 'brief', a);
  }
  for (final a in tds[3].querySelectorAll('a[href]')) {
    add('submission', a);
  }
  for (final a in tds[5].querySelectorAll('a[href]')) {
    add('returned', a);
  }
  return out;
}

/// The LMS assignments table for one course (one record per row with eight cells).
List<Json> parseCourseTable(String pageHtml, String courseName) {
  final items = <Json>[];
  for (final row in _rows(_doc(pageHtml))) {
    final tds = _kids(row, const {'td'});
    final cells = [for (final c in tds) cleanText(c.text)];
    if (cells.length < 8) continue;
    final assignNo = cells[0], title = cells[1], addedSub = cells[3], marks = cells[4], action = cells[6], rawDeadline = cells[7];
    if (title.isEmpty) continue;
    final (activeDl, isExtended, originalDl) = parseDeadline(rawDeadline);
    final sub = addedSub.toLowerCase();
    final isSubmitted = sub.contains('submission') && !sub.contains('no submission');
    final isExceeded = action.toLowerCase().contains('exceeded') || activeDl.toLowerCase().contains('exceeded');
    items.add({
      'id': '$courseName#$assignNo#$title'.replaceAll(' ', '_'),
      'course': courseName,
      'assign_no': assignNo,
      'title': title,
      'due_date': activeDl,
      'raw_deadline': rawDeadline,
      'is_extended': isExtended,
      'original_due_date': originalDl,
      'submission_status': addedSub,
      'action': action,
      'marks': marks,
      'status': isSubmitted ? 'Submitted' : (isExceeded ? 'Missed (Exceeded)' : 'Pending'),
      'is_submitted': isSubmitted,
      'files': assignmentFiles(tds),
    });
  }
  return items;
}

// ---------------------------------------------------------------------------- submitting work
const submitExtensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip'];
const submitMaxBytes = 15 * 1024 * 1024; // the portal's own limit
final _submitNameBad = RegExp(r'[^A-Za-z0-9 ._()\-]');

/// os.path.splitext on a base name: leading dots never start an extension.
(String, String) _splitExt(String name) {
  var lead = 0;
  while (lead < name.length && name[lead] == '.') {
    lead++;
  }
  final dot = name.lastIndexOf('.');
  return dot >= lead ? (name.substring(0, dot), name.substring(dot)) : (name, '');
}

/// The file name sent to the portal: the portal asks for no special symbols (#, $ ...) in it.
String submissionUploadName(String path) {
  final base = path.split(RegExp(r'[\\/]')).last;
  final (stem0, ext) = _splitExt(base);
  final stem = _stripChars(stem0.replaceAll(_submitNameBad, '').replaceAll(_ws, ' '), ' .');
  return (stem.isEmpty ? 'submission' : stem) + ext.toLowerCase();
}

/// '' when a file of this name and size can be sent, else the reason it cannot.
String checkSubmissionFileBytes(String name, int size) {
  if (!submitExtensions.contains(_splitExt(name).$2.toLowerCase())) return 'The portal accepts only ${submitExtensions.join(', ')} files.';
  if (size == 0) return 'That file is empty.';
  if (size > submitMaxBytes) return "That file is ${(size / 1048576).toStringAsFixed(1)} MB; the portal's limit is 15 MB.";
  return '';
}

/// (canUpload, canReplaceOrDelete) from the Action cell of an assignment row, as the portal words it: 'Submit'
/// offers an upload, 'Delete' offers to remove the submission, 'Deadline Exceeded' offers neither.
(bool, bool) submissionActions(String? actionText) {
  final t = (actionText ?? '').toLowerCase();
  if (t.contains('exceeded')) return (false, false);
  return (t.contains('submit'), t.contains('delete'));
}

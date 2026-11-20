/// The arithmetic the desktop app and the website calculator also use. One scale, tested (test/logic_test.dart).
const gradePoints = <String, double>{
  'A': 4.0, 'A-': 3.67, 'B+': 3.33, 'B': 3.0, 'B-': 2.67, 'C+': 2.33, 'C': 2.0, 'C-': 1.67, 'D+': 1.33, 'D': 1.0, 'F': 0.0,
};

double _round2(double v) => (v * 100).round() / 100;

class GradedCourse {
  GradedCourse({this.credits = 3, this.grade = ''});
  double credits;
  String grade;
  double? get points => gradePoints[grade];
}

double? gpaOf(List<GradedCourse> rows) {
  final c = rows.where((r) => r.credits > 0 && r.points != null).toList();
  final credits = c.fold<double>(0, (n, r) => n + r.credits);
  if (credits == 0) return null;
  return _round2(c.fold<double>(0, (n, r) => n + r.credits * r.points!) / credits);
}

double creditsOf(List<GradedCourse> rows) => rows.where((r) => r.credits > 0 && r.points != null).fold<double>(0, (n, r) => n + r.credits);
double pointsOf(List<GradedCourse> rows) => rows.where((r) => r.credits > 0 && r.points != null).fold<double>(0, (n, r) => n + r.credits * r.points!);

double? cgpaAfter(List<GradedCourse> rows, double? prevCgpa, double prevCredits) {
  final credits = creditsOf(rows);
  if (credits == 0) return prevCredits > 0 && prevCgpa != null ? _round2(prevCgpa) : null;
  if (prevCredits <= 0 || prevCgpa == null) return gpaOf(rows);
  return _round2((prevCgpa * prevCredits + pointsOf(rows)) / (prevCredits + credits));
}

/// The semester GPA that ends on [target] CGPA. `reachable` is false above 4.00; `best` is the CGPA with straight As.
({double needed, bool reachable, double best})? neededGpa(double target, double? prevCgpa, double prevCredits, double semesterCredits) {
  if (semesterCredits <= 0) return null;
  final pc = prevCredits > 0 ? prevCredits : 0.0;
  final pg = pc > 0 ? (prevCgpa ?? 0) : 0.0;
  final needed = (target * (pc + semesterCredits) - pg * pc) / semesterCredits;
  return (needed: _round2(needed), reachable: needed <= 4 + 1e-9, best: _round2((pg * pc + 4 * semesterCredits) / (pc + semesterCredits)));
}

/// How much may be missed over the whole semester, from the credit hours: 16 weeks, a one-credit lab meets three hours a
/// week; the minimum leaves (100 - minimum)% of those hours.
class Allowance {
  Allowance(this.planned, this.max, this.used, this.classLen);
  final double planned, max, used, classLen;
  double get left => (max - used).clamp(0, double.infinity).toDouble();
  int get classes => (max / classLen + 1e-9).floor();
}

Allowance? semesterAllowance(double credit, int minimum, double absent, List<double> sessionHours) {
  if (credit <= 0) return null;
  final planned = (credit == 1 ? 3.0 : credit) * 16;
  final known = sessionHours.where((h) => h > 0).toList()..sort();
  final classLen = known.isNotEmpty ? known[known.length ~/ 2] : (credit == 1 ? 3.0 : credit == 2 ? 2.0 : 1.5);
  return Allowance(planned, planned * (100 - minimum) / 100, absent, classLen);
}

String hoursText(double h) => '${h == h.roundToDouble() ? h.round() : h.toStringAsFixed(1)} h';

/// "just now", "12 min ago", "5 h ago", "3 days ago".
String agoLabel(Duration d) {
  if (d.inMinutes < 1) return 'just now';
  if (d.inMinutes < 60) return '${d.inMinutes} min ago';
  if (d.inHours < 48) return '${d.inHours} h ago';
  return '${d.inDays} days ago';
}

import 'package:flutter_test/flutter_test.dart';

import 'package:assignment_monitor_mobile/logic.dart';

void main() {
  final sem = [GradedCourse(credits: 3, grade: 'A'), GradedCourse(credits: 3, grade: 'B+'), GradedCourse(credits: 2, grade: 'B'), GradedCourse(credits: 1, grade: 'A-')];

  test('the worked example: GPA 3.52 and CGPA 3.50 over 60 earlier credits', () {
    expect(gpaOf(sem), 3.52);
    expect(cgpaAfter(sem, 3.5, 60), 3.5);
  });

  test('ungraded rows and zero-credit rows are ignored', () {
    expect(gpaOf([GradedCourse(credits: 3, grade: ''), GradedCourse(credits: 0, grade: 'A')]), isNull);
    expect(gpaOf([GradedCourse(credits: 3, grade: 'A'), GradedCourse(credits: 0, grade: 'F')]), 4.0);
  });

  test('a 3.60 target over 84 credits needs 4.05 and is out of reach', () {
    final g = neededGpa(3.6, 241.66 / 69, 69, 15)!;
    expect(g.needed, 4.05);
    expect(g.reachable, isFalse);
  });

  test('the whole-semester allowance: 12 h for a lab and 3 credits, 8 h for 2 credits', () {
    expect(semesterAllowance(1, 75, 0, [])!.max, 12);
    expect(semesterAllowance(1, 75, 0, [])!.classes, 4);
    expect(semesterAllowance(2, 75, 0, [])!.max, 8);
    expect(semesterAllowance(2, 75, 0, [])!.classes, 4);
    expect(semesterAllowance(3, 75, 0, [])!.max, 12);
    expect(semesterAllowance(3, 75, 15, [])!.left, 0);
    expect(semesterAllowance(0, 75, 0, []), isNull);
  });
}

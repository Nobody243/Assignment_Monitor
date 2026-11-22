import 'package:assignment_monitor_mobile/tester.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('only the tester account gets the extra tools', () {
    expect(isTester('Nobody243'), isTrue);
    expect(isTester(' nobody243 '), isTrue);
    expect(isTester('someone-else'), isFalse);
    expect(isTester(null), isFalse);
  });
}

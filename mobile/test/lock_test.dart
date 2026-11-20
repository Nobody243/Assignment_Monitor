import 'package:assignment_monitor_mobile/lock.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/reminders.dart';
import 'package:assignment_monitor_mobile/screens/lock_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

class FakeLocker implements Locker {
  FakeLocker({this.isAvailable = true, this.answers = const [true]});
  bool isAvailable;
  List<bool> answers;
  int asked = 0;
  @override Future<bool> available() async => isAvailable;
  @override Future<bool> verify(String reason) async => answers[(asked++).clamp(0, answers.length - 1)];
}

AppModel model(FakeLocker l) => AppModel(Prefs(), store: MemoryStore(), locker: l, splashMin: Duration.zero);

void main() {
  setUp(() { SharedPreferences.setMockInitialValues({}); Reminders.forceSupported = false; });

  group('when the app locks itself', () {
    const policy = LockPolicy();
    final t0 = DateTime(2026, 11, 20, 12);
    test('after more than 30 seconds away, when the lock is on', () {
      expect(policy.shouldLock(enabled: true, leftAt: t0, now: t0.add(const Duration(seconds: 31))), isTrue);
      expect(policy.shouldLock(enabled: true, leftAt: t0, now: t0.add(const Duration(minutes: 10))), isTrue);
    });
    test('not for a short trip, not when off, not when it never left', () {
      expect(policy.shouldLock(enabled: true, leftAt: t0, now: t0.add(const Duration(seconds: 10))), isFalse);
      expect(policy.shouldLock(enabled: false, leftAt: t0, now: t0.add(const Duration(hours: 1))), isFalse);
      expect(policy.shouldLock(enabled: true, leftAt: null, now: t0), isFalse);
    });
  });

  group('the lock on the model', () {
    test('a cold start with the lock on opens locked, and the right answer unlocks it', () async {
      SharedPreferences.setMockInitialValues({'appLock': true});
      final m = model(FakeLocker());
      await m.start();
      expect(m.locked, isTrue);
      expect(await m.unlock(), isTrue);
      expect(m.locked, isFalse);
    });

    test('a wrong or cancelled answer leaves it locked', () async {
      SharedPreferences.setMockInitialValues({'appLock': true});
      final m = model(FakeLocker(answers: [false, false, true]));
      await m.start();
      expect(await m.unlock(), isFalse);
      expect(m.locked, isTrue);
      expect(await m.unlock(), isFalse);
      expect(m.locked, isTrue);
      expect(await m.unlock(), isTrue);
      expect(m.locked, isFalse);
    });

    test('with the lock off nothing is ever locked', () async {
      final m = model(FakeLocker());
      await m.start();
      expect(m.locked, isFalse);
      m.noteLeft(DateTime(2026, 11, 20, 12));
      m.noteBack(DateTime(2026, 11, 20, 14));
      expect(m.locked, isFalse);
    });

    test('coming back after a while locks again; a short trip does not', () async {
      SharedPreferences.setMockInitialValues({'appLock': true});
      final m = model(FakeLocker());
      await m.start();
      await m.unlock();
      final t0 = DateTime(2026, 11, 20, 12);
      m.noteLeft(t0);
      m.noteBack(t0.add(const Duration(seconds: 5)));
      expect(m.locked, isFalse);
      m.noteLeft(t0);
      m.noteBack(t0.add(const Duration(minutes: 3)));
      expect(m.locked, isTrue);
    });

    test('if the phone has lost its screen lock, the app does not lock you out of your own data', () async {
      SharedPreferences.setMockInitialValues({'appLock': true});
      final m = model(FakeLocker(isAvailable: false));
      await m.start();
      expect(m.locked, isFalse);
    });

    test('turning it on needs a phone lock and one successful check', () async {
      var l = FakeLocker(isAvailable: false);
      var m = model(l);
      expect(await m.setAppLock(true), contains('Set up a screen lock'));
      expect(m.prefs.appLock, isFalse);

      l = FakeLocker(answers: [false]);
      m = model(l);
      expect(await m.setAppLock(true), contains('not confirmed'));
      expect(m.prefs.appLock, isFalse);

      l = FakeLocker();
      m = model(l);
      expect(await m.setAppLock(true), isNull);
      expect(m.prefs.appLock, isTrue);
      await Future.delayed(const Duration(milliseconds: 20));   // the save runs just after the change
      expect((await SharedPreferences.getInstance()).getBool('appLock'), isTrue);
    });

    test('turning it off needs no check and unlocks', () async {
      SharedPreferences.setMockInitialValues({'appLock': true});
      final l = FakeLocker();
      final m = model(l);
      await m.start();
      expect(await m.setAppLock(false), isNull);
      expect(m.prefs.appLock, isFalse);
      expect(m.locked, isFalse);
      expect(l.asked, 0);
    });
  });

  testWidgets('the lock screen asks at once, and the button asks again after a refusal', (tester) async {
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(390 * 3, 800 * 3);
    addTearDown(tester.view.reset);
    final l = FakeLocker(answers: [false, true]);
    final m = model(l)..locked = true;
    await tester.pumpWidget(MaterialApp(home: ListenableBuilder(listenable: m, builder: (_, _) => m.locked ? LockScreen(model: m) : const Text('open'))));
    await tester.pump(const Duration(milliseconds: 500));
    expect(l.asked, 1);                                       // asked without a tap
    expect(find.text('That did not unlock it. Try again.'), findsOneWidget);
    await tester.tap(find.text('Unlock'));
    await tester.pumpAndSettle();
    expect(l.asked, 2);
    expect(find.text('open'), findsOneWidget);                // the second answer was yes
  });
}

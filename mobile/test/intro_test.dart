import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/screens/intro.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('the intro has three slides and ends by marking itself as seen', (tester) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(390 * 3, 800 * 3);
    addTearDown(tester.view.reset);
    final model = AppModel(Prefs())..introSeen = false;
    await tester.pumpWidget(MaterialApp(home: IntroScreen(model: model)));
    await tester.pumpAndSettle();

    expect(find.text('Never miss a deadline'), findsOneWidget);
    expect(find.text('Next'), findsOneWidget);
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('Know how many classes you can miss'), findsOneWidget);
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('Your data stays yours'), findsOneWidget);
    expect(find.text('Skip'), findsOneWidget);   // faded out on the last slide, so it cannot be tapped
    expect(find.text('Get started'), findsOneWidget);
    expect(model.introSeen, isFalse);
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();
    expect(model.introSeen, isTrue);
  });

  testWidgets('Skip ends the intro at once', (tester) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(390 * 3, 800 * 3);
    addTearDown(tester.view.reset);
    final model = AppModel(Prefs())..introSeen = false;
    await tester.pumpWidget(MaterialApp(home: IntroScreen(model: model)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Skip'));
    await tester.pumpAndSettle();
    expect(model.introSeen, isTrue);
  });

  testWidgets('the launch mark draws', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: BrandSplash()));
    await tester.pumpAndSettle();
    expect(find.text('Assignment Monitor'), findsOneWidget);
  });
}

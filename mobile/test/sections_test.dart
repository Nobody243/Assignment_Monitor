import 'package:assignment_monitor_mobile/data.dart';
import 'package:assignment_monitor_mobile/main.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/screens/settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Future<(Prefs, AppModel)> setUpApp(WidgetTester tester) async {
    tester.view.devicePixelRatio = 3;
    tester.view.physicalSize = const Size(390 * 3, 800 * 3);
    addTearDown(tester.view.reset);
    final prefs = Prefs();
    final summary = (await tester.runAsync(Summary.load))!;
    return (prefs, AppModel(prefs)..summary = summary..demo = true);
  }

  testWidgets('Timetable, Results and Settings are sections of the app, reached from the menu', (tester) async {
    final (prefs, model) = await setUpApp(tester);
    await tester.pumpWidget(MaterialApp(home: Shell(model: model, prefs: prefs)));
    await tester.pumpAndSettle();
    for (final (row, title) in [('Timetable', 'Timetable'), ('Results & GPA', 'Results & GPA'), ('Settings', 'Settings'), ('Exams', 'Exams')]) {
      await tester.tap(find.byTooltip('Menu'));
      await tester.pumpAndSettle();
      await tester.tap(find.text(row).first);   // the row in the menu
      await tester.pumpAndSettle();
      expect(find.descendant(of: find.byType(AppBar), matching: find.text(title)), findsOneWidget, reason: '$row should become the current section');
      expect(find.byType(BackButton), findsNothing, reason: 'a section has the menu button, not a back arrow');
    }
  });

  testWidgets('Sign out sits at the bottom of Settings and asks first', (tester) async {
    final (prefs, model) = await setUpApp(tester);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: SettingsHub(summary: model.summary!, prefs: prefs, model: model))));
    await tester.pumpAndSettle();
    final leave = find.text('Leave the demo');   // demo mode wording of the sign-out button
    expect(leave, findsOneWidget);
    expect(tester.getTopLeft(leave).dy, greaterThan(tester.getTopLeft(find.text('About and privacy')).dy), reason: 'below the sections');
    await tester.tap(leave);
    await tester.pumpAndSettle();
    expect(find.text('Leave the demo?'), findsOneWidget);   // the confirmation
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(find.text('Leave the demo?'), findsNothing);

    // the Account page no longer carries the sign-out button
    await tester.tap(find.text('Account and data'));
    await tester.pumpAndSettle();
    expect(find.text('Leave the demo'), findsNothing);
    expect(find.text('Sign out'), findsNothing);
  });
}

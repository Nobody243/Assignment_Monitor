import 'package:assignment_monitor_mobile/main.dart';
import 'package:assignment_monitor_mobile/model.dart';
import 'package:assignment_monitor_mobile/data.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// The side menu must always settle fully open or fully shut, however fast it is tapped and dragged.
void main() {
  Future<AppModel> pumpShell(WidgetTester tester) async {
    final prefs = Prefs();
    final summary = (await tester.runAsync(Summary.load))!;   // reading the asset needs real time, not the test clock
    final model = AppModel(prefs)..summary = summary..demo = true;
    tester.view.devicePixelRatio = 3; tester.view.physicalSize = const Size(390 * 3, 800 * 3); addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(home: Shell(model: model, prefs: prefs)));
    await tester.pumpAndSettle();
    return model;
  }

  double appLeft(WidgetTester tester) => tester.getTopLeft(find.byType(Scaffold).first).dx;

  testWidgets('tapping the menu button quickly never leaves it half way', (tester) async {
    await pumpShell(tester);
    expect(appLeft(tester), closeTo(0, 0.5));
    for (final taps in [1, 2, 3, 4, 5, 6, 7]) {
      for (var i = 0; i < taps; i++) {
        await tester.tap(find.byTooltip('Menu'), warnIfMissed: false);
        await tester.pump(Duration(milliseconds: 20 + 25 * i));
      }
      await tester.pumpAndSettle();
      final x = appLeft(tester);
      expect(x < 0.5 || x > 200, isTrue, reason: 'after $taps quick taps the app sits at x=$x');
      // whichever way it ended, one more tap must reverse it
      final before = x > 200;
      await tester.tap(find.byTooltip('Menu'), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(appLeft(tester) > 200, isNot(before), reason: 'after $taps quick taps (open=$before) one more tap did not reverse it');
    }
  });

  testWidgets('a drag from the left edge opens it and a fling shuts it', (tester) async {
    await pumpShell(tester);
    await tester.dragFrom(const Offset(6, 400), const Offset(260, 0));
    await tester.pumpAndSettle();
    expect(appLeft(tester), greaterThan(200));
    await tester.flingFrom(const Offset(340, 400), const Offset(-300, 0), 1200);
    await tester.pumpAndSettle();
    expect(appLeft(tester), closeTo(0, 0.5));
  });
}

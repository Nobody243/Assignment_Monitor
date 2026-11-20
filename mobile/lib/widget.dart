import 'package:home_widget/home_widget.dart';

import 'data.dart';
import 'reminders.dart';

/// The Android home-screen widget: the next deadline, in a small tile. The app writes four short strings; the native widget
/// (android/.../NextDeadlineWidget.kt) draws them. It is refreshed whenever the app plans reminders, which is on every
/// launch, every refresh and every background check.
class HomeScreenWidget {
  static const androidName = 'NextDeadlineWidget';

  /// What the tile shows. Pure, so it is tested without a phone.
  static Map<String, String> data(Summary s, Set<String> done, DateTime now) {
    final open = [for (final w in s.work) if (w.todo && w.open && w.due != null && !done.contains(w.id) && w.due!.isAfter(now)) w]..sort((a, b) => a.due!.compareTo(b.due!));
    if (open.isEmpty) {
      return {'headline': 'All caught up', 'detail': 'Nothing is waiting for a submission', 'left': '', 'count': ''};
    }
    final w = open.first;
    final more = open.length - 1;
    return {
      'headline': w.title,
      'detail': '${w.course} · ${dayLabel(w.due!)}, ${timeLabel(w.due!)}',
      'left': countdown(w.due!, now),
      'count': more <= 0 ? 'only one to do' : '$more more to do',
    };
  }

  static Future<void> update(Summary s, Set<String> done, {DateTime? now}) async {
    if (!Reminders.isAndroid) return;
    try {
      for (final e in data(s, done, now ?? DateTime.now()).entries) { await HomeWidget.saveWidgetData<String>('next_${e.key}', e.value); }
      await HomeWidget.updateWidget(androidName: androidName);
    } catch (_) {
      // a missing widget host (an emulator without one, say) must never disturb the app
    }
  }
}

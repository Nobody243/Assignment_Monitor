import 'dart:convert';

import 'package:flutter/foundation.dart' hide Summary;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import 'data.dart';

/// Deadline reminders scheduled on the phone itself, so they fire with no network and no server.
/// Quiet hours (23:00 to 07:00) are delivered silently. Snooze and Done are notification buttons.
class Reminders {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _ready = false;
  static bool get supported => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  static const _loud = AndroidNotificationDetails('deadlines', 'Deadlines',
      channelDescription: 'Reminders before an assignment is due', importance: Importance.high, priority: Priority.high,
      actions: [AndroidNotificationAction('snooze', 'Snooze 1 h'), AndroidNotificationAction('done', 'Done')]);
  static const _quiet = AndroidNotificationDetails('quiet', 'Quiet hours',
      channelDescription: 'Reminders that fall between 23:00 and 07:00 arrive silently', importance: Importance.low, priority: Priority.low,
      playSound: false, enableVibration: false,
      actions: [AndroidNotificationAction('snooze', 'Snooze 1 h'), AndroidNotificationAction('done', 'Done')]);

  static Future<void> init() async {
    if (!supported || _ready) return;
    tzdata.initializeTimeZones();
    try {
      tz.setLocalLocation(tz.getLocation((await FlutterTimezone.getLocalTimezone()).identifier));
    } catch (e) {
      debugPrint('timezone: $e');
    }
    await _plugin.initialize(
      settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
      onDidReceiveNotificationResponse: _answer,
      onDidReceiveBackgroundNotificationResponse: answerInBackground,
    );
    _ready = true;
  }

  /// Asks for the notification permission (Android 13+). Returns whether reminders can show.
  static Future<bool> allowed() async {
    if (!supported) return false;
    await init();
    final a = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    return await a?.requestNotificationsPermission() ?? false;
  }

  /// Replaces every scheduled reminder with the ones the current summary and settings call for.
  static Future<int> schedule(Summary s, {required List<int> leads, required Set<String> done, required Map<String, DateTime> snoozed}) async {
    if (!supported) return 0;
    await init();
    await _plugin.cancelAll();
    final now = DateTime.now();
    var n = 0;
    for (final w in s.work) {
      if (!w.todo || !w.open || w.due == null || done.contains(w.id)) continue;
      for (final h in leads) {
        final at = w.due!.subtract(Duration(hours: h));
        if (!at.isAfter(now) || n >= 60) continue;
        await _show(w, at, h, _idFor(w.id, h));
        n++;
      }
      final wake = snoozed[w.id];
      if (wake != null && wake.isAfter(now) && wake.isBefore(w.due!)) {
        await _show(w, wake, null, _idFor(w.id, 99));
        n++;
      }
    }
    return n;
  }

  static Future<void> _show(Work w, DateTime at, int? hours, int id) {
    final quiet = at.hour >= 23 || at.hour < 7;
    final left = hours == null ? 'is still open' : hours == 1 ? 'is due in 1 hour' : 'is due in $hours hours';
    return _plugin.zonedSchedule(
      id: id,
      title: '${w.course}: ${w.title}',
      body: 'Assignment ${w.number} $left.'.replaceAll('  ', ' '),
      scheduledDate: tz.TZDateTime.from(at, tz.local),
      notificationDetails: NotificationDetails(android: quiet ? _quiet : _loud),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      payload: w.id,
    );
  }

  static int _idFor(String assignmentId, int slot) => (assignmentId.hashCode.abs() % 20000000) * 100 + slot;

  static Future<void> _answer(NotificationResponse r) => answerInBackground(r);
}

/// Snooze or Done tapped on a notification, possibly while the app is closed: write the choice where the app reads it.
@pragma('vm:entry-point')
Future<void> answerInBackground(NotificationResponse r) async {
  final id = r.payload;
  if (id == null) return;
  final p = await SharedPreferences.getInstance();
  if (r.actionId == 'done') {
    p.setStringList('done', <String>{...(p.getStringList('done') ?? <String>[]), id}.toList());
  } else if (r.actionId == 'snooze') {
    final m = Map<String, dynamic>.from(jsonDecode(p.getString('snoozed') ?? '{}') as Map);
    m[id] = DateTime.now().add(const Duration(hours: 1)).toIso8601String();
    p.setString('snoozed', jsonEncode(m));
  }
}

package com.nobody243.assignment_monitor_mobile

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.SharedPreferences
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetLaunchIntent
import es.antonborri.home_widget.HomeWidgetProvider

/**
 * The home-screen tile: the next deadline. The Flutter side (lib/widget.dart) saves four strings under next_headline,
 * next_detail, next_left and next_count; this only draws them and opens the app when tapped.
 */
class NextDeadlineWidget : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: SharedPreferences,
    ) {
        appWidgetIds.forEach { id ->
            val views = RemoteViews(context.packageName, R.layout.widget_next_deadline).apply {
                setTextViewText(R.id.widget_headline, widgetData.getString("next_headline", "Assignment Monitor"))
                setTextViewText(R.id.widget_detail, widgetData.getString("next_detail", "Open the app to load your deadlines"))
                setTextViewText(R.id.widget_left, widgetData.getString("next_left", ""))
                setTextViewText(R.id.widget_count, widgetData.getString("next_count", ""))
                setOnClickPendingIntent(R.id.widget_root, HomeWidgetLaunchIntent.getActivity(context, MainActivity::class.java))
            }
            appWidgetManager.updateAppWidget(id, views)
        }
    }
}

package kr.arecmik.widget;
import android.content.*;
public final class BootReceiver extends BroadcastReceiver {@Override public void onReceive(Context c,Intent i){SyncJob.schedule(c);CalendarWidget.updateAll(c);ReminderScheduler.reschedule(c);}}

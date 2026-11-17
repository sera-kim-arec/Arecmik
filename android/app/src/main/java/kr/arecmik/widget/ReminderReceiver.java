package kr.arecmik.widget;

import android.content.*;

public final class ReminderReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context c,Intent intent){
        if("kr.arecmik.REMIND".equals(intent.getAction()))ReminderScheduler.fire(c);
        else ReminderScheduler.reschedule(c);
    }
}

package kr.arecmik.widget;

import android.content.Context;

final class AccountConnection {
    static void clear(Context c)throws Exception {synchronized(SyncEngine.LOCK){SecureStore.put(c,"account",null);SecureStore.put(c,"pairing",null);SecureStore.put(c,"webCredential",null);DataStore.clear(c);SyncJob.cancel(c);CalendarWidget.updateAll(c);}}
}

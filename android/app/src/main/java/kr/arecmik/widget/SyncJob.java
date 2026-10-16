package kr.arecmik.widget;

import android.app.job.*;
import android.content.*;

public final class SyncJob extends JobService {
    private static final int PERIODIC=4121,SOON=4122;
    static void schedule(Context c){JobScheduler jobs=c.getSystemService(JobScheduler.class);jobs.schedule(new JobInfo.Builder(PERIODIC,new ComponentName(c,SyncJob.class)).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPeriodic(60*60*1000,15*60*1000).setPersisted(true).build());}
    static void scheduleSoon(Context c){int failures=Math.min(6,DataStore.prefs(c).getInt("syncFailures",0));long delay=Math.min(3600000L,60000L*(1L<<failures));c.getSystemService(JobScheduler.class).schedule(new JobInfo.Builder(SOON,new ComponentName(c,SyncJob.class)).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setMinimumLatency(delay).setBackoffCriteria(60000,JobInfo.BACKOFF_POLICY_EXPONENTIAL).build());}
    static void scheduleNow(Context c,boolean force){android.os.PersistableBundle extras=new android.os.PersistableBundle();extras.putBoolean("force",force);c.getSystemService(JobScheduler.class).schedule(new JobInfo.Builder(SOON,new ComponentName(c,SyncJob.class)).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setExtras(extras).setMinimumLatency(0).setBackoffCriteria(60000,JobInfo.BACKOFF_POLICY_EXPONENTIAL).build());}
    static void cancel(Context c){JobScheduler jobs=c.getSystemService(JobScheduler.class);jobs.cancel(PERIODIC);jobs.cancel(SOON);}
    @Override public boolean onStartJob(JobParameters params){new Thread(()->{SyncEngine.sync(this,params.getExtras().getBoolean("force",false));jobFinished(params,false);},"widget-sync").start();return true;}
    @Override public boolean onStopJob(JobParameters params){return true;}
}

package kr.arecmik.widget;

import android.app.*;
import android.content.*;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import static org.junit.Assert.*;
import static org.robolectric.Shadows.shadowOf;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35,shadows=ReminderSchedulerTest.AccountShadow.class)
public class ReminderSchedulerTest {
    @Implements(value=SecureStore.class,isInAndroidSdk=false)
    public static class AccountShadow {
        @Implementation protected static JSONObject get(Context c,String name)throws Exception{return "account".equals(name)?new JSONObject().put("uid","test-user"):null;}
    }
    Context c;AlarmManager alarms;NotificationManager notifications;
    @Before public void setup(){c=RuntimeEnvironment.getApplication();ReminderScheduler.clear(c);alarms=c.getSystemService(AlarmManager.class);notifications=c.getSystemService(NotificationManager.class);shadowOf((Application)c).grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS);shadowOf(alarms).setCanScheduleExactAlarms(true);}
    JSONObject event(String id,int hours)throws Exception{LocalDateTime d=LocalDateTime.now().plusHours(hours).withSecond(0).withNano(0);return new JSONObject().put("id",id).put("title","다가오는 일정").put("kind","event").put("date",d.toLocalDate().toString()).put("time",d.format(DateTimeFormatter.ofPattern("HH:mm")));}
    void enable(JSONArray tasks)throws Exception{ReminderScheduler.update(c,"test-user",tasks);ReminderScheduler.setEnabled(c,true);}
    long when(JSONObject t){return ReminderPlan.when(t,"15",ZoneId.systemDefault());}
    @Test public void oneAlarmTargetsNearestThenAdvancesWithoutDuplicates()throws Exception{
        JSONObject first=event("first",1),second=event("second",2);enable(new JSONArray().put(first).put(second));assertEquals(1,shadowOf(alarms).getScheduledAlarms().size());assertEquals(when(first),shadowOf(alarms).getScheduledAlarms().get(0).triggerAtTime);
        ReminderScheduler.reschedule(c);ReminderScheduler.fire(c,when(first)+500);assertEquals(1,notifications.getActiveNotifications().length);assertEquals(when(second),shadowOf(alarms).getScheduledAlarms().get(0).triggerAtTime);
        ReminderScheduler.reschedule(c);ReminderScheduler.fire(c);assertEquals(1,notifications.getActiveNotifications().length);
    }
    @Test public void completedDeletedAndMovedEventsCancelReservationsAndVisibleNotifications()throws Exception{
        JSONObject t=event("first",1);enable(new JSONArray().put(t));ReminderScheduler.fire(c,when(t)+500);assertEquals(1,notifications.getActiveNotifications().length);
        ReminderScheduler.completed(c,"first",true);assertEquals(0,notifications.getActiveNotifications().length);assertEquals(0,shadowOf(alarms).getScheduledAlarms().size());
        JSONObject moved=event("first",3);ReminderScheduler.update(c,"test-user",new JSONArray().put(moved));assertEquals(when(moved),shadowOf(alarms).getScheduledAlarms().get(0).triggerAtTime);
        ReminderScheduler.update(c,"test-user",new JSONArray());assertEquals(0,shadowOf(alarms).getScheduledAlarms().size());
    }
    @Test public void permissionDenialAndInexactFallbackStayUsable()throws Exception{
        shadowOf((Application)c).denyPermissions(android.Manifest.permission.POST_NOTIFICATIONS);enable(new JSONArray().put(event("a",1)));assertEquals(0,shadowOf(alarms).getScheduledAlarms().size());
        shadowOf((Application)c).grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS);shadowOf(alarms).setCanScheduleExactAlarms(false);ReminderScheduler.reschedule(c);assertEquals(1,shadowOf(alarms).getScheduledAlarms().size());
    }
    @Test public void rebootAndTimezoneChangesRestoreAlarmAndDisableClearsIt()throws Exception{
        JSONObject t=event("a",1);enable(new JSONArray().put(t));alarms.cancel(ReminderScheduler.alarm(c));new BootReceiver().onReceive(c,new Intent(Intent.ACTION_BOOT_COMPLETED));assertEquals(1,shadowOf(alarms).getScheduledAlarms().size());new ReminderReceiver().onReceive(c,new Intent(Intent.ACTION_TIMEZONE_CHANGED));assertEquals(1,shadowOf(alarms).getScheduledAlarms().size());ReminderScheduler.setEnabled(c,false);assertEquals(0,shadowOf(alarms).getScheduledAlarms().size());
    }
    @Test public void otherAccountCannotReplaceSnapshotAndClearCancelsAlarms()throws Exception{enable(new JSONArray().put(event("a",1)));ReminderScheduler.update(c,"another-user",new JSONArray());assertEquals(1,ReminderScheduler.tasks(c).length());ReminderScheduler.clear(c);assertEquals(0,ReminderScheduler.tasks(c).length());assertEquals(0,shadowOf(alarms).getScheduledAlarms().size());}
    @Test public void clickingReminderCarriesOriginalIdAndAccount()throws Exception{JSONObject t=event("life-event",1).put("space","life");enable(new JSONArray().put(t));ReminderScheduler.fire(c,when(t)+500);Notification n=notifications.getActiveNotifications()[0].getNotification();assertEquals("LIFE",n.extras.getString(Notification.EXTRA_TEXT).substring(0,4));n.contentIntent.send();Intent open=shadowOf((Application)c).getNextStartedActivity();assertEquals("life-event",open.getStringExtra("task"));assertEquals("test-user",open.getStringExtra("uid"));}
    @Test public void olderFetchCannotRestoreACompletedReminder()throws Exception{JSONObject t=event("a",1);long now=System.currentTimeMillis();ReminderScheduler.update(c,"test-user",new JSONArray().put(t),now);ReminderScheduler.setEnabled(c,true);ReminderScheduler.update(c,"test-user",new JSONArray().put(new JSONObject(t.toString()).put("done",true)),now+1000);ReminderScheduler.update(c,"test-user",new JSONArray().put(t),now);assertEquals(0,shadowOf(alarms).getScheduledAlarms().size());}
    @Test public void pendingWidgetCompletionWinsOverWebSnapshot()throws Exception{JSONObject t=event("a",1);enable(new JSONArray().put(t));DataStore.save(c,new JSONObject().put("pending",new JSONObject().put("a",new JSONObject().put("patch",new JSONObject().put("done",true)))));ReminderScheduler.fromWeb(c,"test-user",new JSONArray().put(t),System.currentTimeMillis());assertEquals(0,shadowOf(alarms).getScheduledAlarms().size());DataStore.clear(c);}
}

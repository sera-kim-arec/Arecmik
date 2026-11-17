package kr.arecmik.widget;

import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import org.json.*;
import java.time.*;
import java.time.format.DateTimeFormatter;

/** A single persisted alarm advances through the cached calendar; no paid backend. */
final class ReminderScheduler {
    static final String CHANNEL="schedule-reminders-visible",LEGACY_CHANNEL="schedule-reminders",TAG="arecmik-reminder";
    static android.content.SharedPreferences prefs(Context c){return c.getSharedPreferences("reminders",0);}
    static boolean enabled(Context c){return prefs(c).getBoolean("enabled",false);}
    static void channel(Context c){NotificationChannel ch=new NotificationChannel(CHANNEL,"일정 알림 · 팝업",NotificationManager.IMPORTANCE_HIGH);ch.setDescription("다가오는 WORK · LIFE 일정 · 상단 팝업과 소리");ch.enableVibration(true);ch.setVibrationPattern(new long[]{0,180,100,180});ch.setSound(android.media.RingtoneManager.getDefaultUri(android.media.RingtoneManager.TYPE_NOTIFICATION),new android.media.AudioAttributes.Builder().setUsage(android.media.AudioAttributes.USAGE_NOTIFICATION_EVENT).build());c.getSystemService(NotificationManager.class).createNotificationChannel(ch);}
    static String channelId(Context c){channel(c);NotificationChannel legacy=c.getSystemService(NotificationManager.class).getNotificationChannel(LEGACY_CHANNEL);if(legacy!=null&&(legacy.getImportance()==NotificationManager.IMPORTANCE_NONE||Build.VERSION.SDK_INT<29||legacy.hasUserSetImportance()||legacy.getSound()==null||(Build.VERSION.SDK_INT>=30&&legacy.hasUserSetSound())))return LEGACY_CHANNEL;return CHANNEL;}
    static boolean allowed(Context c){NotificationManager n=c.getSystemService(NotificationManager.class);return (Build.VERSION.SDK_INT<33||c.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED)&&n.areNotificationsEnabled()&&n.getNotificationChannel(channelId(c)).getImportance()!=NotificationManager.IMPORTANCE_NONE;}
    static boolean popupAllowed(Context c){return c.getSystemService(NotificationManager.class).getNotificationChannel(channelId(c)).getImportance()>=NotificationManager.IMPORTANCE_HIGH;}
    static boolean exact(Context c){return Build.VERSION.SDK_INT<31||c.getSystemService(AlarmManager.class).canScheduleExactAlarms();}
    static JSONArray tasks(Context c){try{return new JSONArray(prefs(c).getString("tasks","[]"));}catch(Exception ignored){return new JSONArray();}}
    static JSONObject delivered(Context c){try{return new JSONObject(prefs(c).getString("delivered","{}"));}catch(Exception ignored){return new JSONObject();}}
    static boolean linked(Context c){try{JSONObject account=SecureStore.get(c,"account");return account!=null&&account.optString("uid").equals(prefs(c).getString("uid",""));}catch(Exception ignored){return false;}}
    static PendingIntent alarm(Context c){return PendingIntent.getBroadcast(c,4201,new Intent(c,ReminderReceiver.class).setAction("kr.arecmik.REMIND"),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);}
    static void update(Context c,String uid,JSONArray source)throws Exception{update(c,uid,source,System.currentTimeMillis());}
    static void fromWeb(Context c,String uid,JSONArray source,long receivedAt)throws Exception{
        // Local widget completions awaiting upload take precedence over a server snapshot.
        JSONObject pending=DataStore.pending(DataStore.data(c));
        for(int i=0;i<source.length();i++){JSONObject t=source.optJSONObject(i);if(t==null)continue;JSONObject op=pending.optJSONObject(t.optString("id"));if(op!=null&&op.optJSONObject("patch")!=null&&op.getJSONObject("patch").has("done"))t.put("done",op.getJSONObject("patch").getBoolean("done"));}
        update(c,uid,source,receivedAt);
    }
    static synchronized void update(Context c,String uid,JSONArray source,long receivedAt)throws Exception{
        JSONObject account=SecureStore.get(c,"account");if(account==null||!uid.equals(account.optString("uid")))return;
        if(receivedAt<prefs(c).getLong("updatedAt",0))return;
        JSONArray clean=new JSONArray();
        for(int i=0;i<source.length();i++){
            JSONObject t=source.optJSONObject(i);if(t==null||!t.optString("id").matches("[A-Za-z0-9_-]{1,128}"))continue;
            JSONObject copy=new JSONObject();for(String field:new String[]{"id","date","time","title","kind","space","reminder","done"})if(t.has(field))copy.put(field,t.get(field));clean.put(copy);
        }
        JSONObject seen=delivered(c),keep=new JSONObject();
        for(int i=0;i<clean.length();i++){JSONObject t=clean.getJSONObject(i);String key=ReminderPlan.key(t,ReminderPlan.when(t,prefs(c).getString("lead","15"),ZoneId.systemDefault()));if(seen.has(key))keep.put(key,true);}
        if(!prefs(c).edit().putLong("updatedAt",receivedAt).putString("uid",uid).putString("tasks",clean.toString()).putString("delivered",keep.toString()).commit())throw new IllegalStateException("알림을 기기에 저장하지 못했어요");
        // Remove an already displayed notification if the original was deleted, completed or moved.
        for(android.service.notification.StatusBarNotification n:c.getSystemService(NotificationManager.class).getActiveNotifications())if(n.getTag()!=null&&n.getTag().startsWith(TAG+":")){
            JSONObject task=CalendarData.find(clean,n.getTag().substring(TAG.length()+1));
            long at=task==null?0:ReminderPlan.when(task,prefs(c).getString("lead","15"),ZoneId.systemDefault());
            if(at==0||!ReminderPlan.key(task,at).equals(n.getNotification().extras.getString("reminder-key")))c.getSystemService(NotificationManager.class).cancel(n.getTag(),0);
        }
        reschedule(c);
    }
    static synchronized void setEnabled(Context c,boolean value){prefs(c).edit().putBoolean("enabled",value).commit();if(!value)clearNotifications(c);reschedule(c);}
    static synchronized void reschedule(Context c){
        AlarmManager a=c.getSystemService(AlarmManager.class);a.cancel(alarm(c));
        if(!enabled(c)||!linked(c)||!allowed(c))return;
        long now=System.currentTimeMillis(),next=Long.MAX_VALUE;JSONObject seen=delivered(c);JSONArray all=tasks(c);
        for(int i=0;i<all.length();i++){JSONObject t=all.optJSONObject(i);if(t==null)continue;long at=ReminderPlan.when(t,prefs(c).getString("lead","15"),ZoneId.systemDefault());if(at>now&&at<next&&!seen.has(ReminderPlan.key(t,at)))next=at;}
        if(next==Long.MAX_VALUE)return;
        try{if(exact(c))a.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,next,alarm(c));else a.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,next,alarm(c));}
        catch(SecurityException ignored){a.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,next,alarm(c));}
    }
    static void fire(Context c){fire(c,System.currentTimeMillis());}
    static synchronized void fire(Context c,long now){
        if(!enabled(c)||!linked(c)||!allowed(c)){reschedule(c);return;}
        JSONArray all=tasks(c);JSONObject seen=delivered(c);
        for(int i=0;i<all.length();i++)try{
            JSONObject t=all.getJSONObject(i);long at=ReminderPlan.when(t,prefs(c).getString("lead","15"),ZoneId.systemDefault());String key=ReminderPlan.key(t,at);
            // A short late delivery is useful; old reminders after a long shutdown are not.
            if(at<=0||at>now+1000||now-at>15*60*1000||seen.has(key))continue;
            Intent open=new Intent(c,AppActivity.class).setAction("kr.arecmik.OPEN_REMINDER").setData(Uri.parse("arecmik://reminder/"+t.getString("id"))).putExtra("task",t.getString("id")).putExtra("uid",prefs(c).getString("uid","")).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent click=PendingIntent.getActivity(c,0,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
            String time=t.optString("time").isEmpty()?"종일":t.optString("time");String text=("life".equals(t.optString("space"))?"LIFE":"WORK")+" · "+LocalDate.parse(t.getString("date")).format(DateTimeFormatter.ofPattern("M/d"))+" "+time;
            android.os.Bundle extras=new android.os.Bundle();extras.putString("reminder-key",key);
            Notification n=new Notification.Builder(c,channelId(c)).setSmallIcon(R.drawable.ic_notification_lemon).setLargeIcon(android.graphics.BitmapFactory.decodeResource(c.getResources(),R.drawable.lemon_brand)).setColor(0xffe6c84d).setContentTitle(t.optString("title","일정")).setContentText(text).setStyle(new Notification.BigTextStyle().bigText(t.optString("title","일정")+"\n"+text).setSummaryText("Arecmik · 일정 알림 🍋")).setContentIntent(click).setAutoCancel(true).setOnlyAlertOnce(true).setCategory(Notification.CATEGORY_REMINDER).setVisibility(Notification.VISIBILITY_PRIVATE).addExtras(extras).build();
            c.getSystemService(NotificationManager.class).notify(TAG+":"+t.getString("id"),0,n);seen.put(key,true);
        }catch(Exception ignored){/* One malformed event must not block other reminders. */}
        prefs(c).edit().putString("delivered",seen.toString()).commit();reschedule(c);
    }
    static void clearNotifications(Context c){NotificationManager n=c.getSystemService(NotificationManager.class);for(android.service.notification.StatusBarNotification s:n.getActiveNotifications())if(s.getTag()!=null&&s.getTag().startsWith(TAG+":"))n.cancel(s.getTag(),s.getId());}
    static void test(Context c){if(!allowed(c))return;PendingIntent click=PendingIntent.getActivity(c,4202,new Intent(c,AppActivity.class).setAction("kr.arecmik.REMINDER_TEST"),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);c.getSystemService(NotificationManager.class).notify(TAG+":test",0,new Notification.Builder(c,channelId(c)).setSmallIcon(R.drawable.ic_notification_lemon).setLargeIcon(android.graphics.BitmapFactory.decodeResource(c.getResources(),R.drawable.lemon_brand)).setColor(0xffe6c84d).setContentTitle("Arecmik 알림 테스트 🍋").setContentText("잠깐, 곧 시작할 일정이 있어요!").setStyle(new Notification.BigTextStyle().bigText("웃는 레몬과 함께 알려드려요.\n일정 제목과 시간을 펼쳐서 확인할 수 있어요.")).setContentIntent(click).setAutoCancel(true).setVisibility(Notification.VISIBILITY_PRIVATE).build());}
    static JSONArray notices(Context c)throws Exception{JSONArray notices=new JSONArray();if(!enabled(c)||!allowed(c))return notices;for(android.service.notification.StatusBarNotification n:c.getSystemService(NotificationManager.class).getActiveNotifications()){if(n.getTag()==null||!n.getTag().startsWith(TAG+":"))continue;String key=n.getNotification().extras.getString("reminder-key");if(key!=null)notices.put(new JSONObject().put("id",n.getTag().substring(TAG.length()+1)).put("key",key));}return notices;}
    static synchronized void clear(Context c){c.getSystemService(AlarmManager.class).cancel(alarm(c));clearNotifications(c);prefs(c).edit().clear().commit();}
    static synchronized void completed(Context c,String id,boolean done)throws Exception{JSONArray all=tasks(c);JSONObject t=CalendarData.find(all,id);if(t!=null){t.put("done",done);update(c,prefs(c).getString("uid",""),all);}}
}

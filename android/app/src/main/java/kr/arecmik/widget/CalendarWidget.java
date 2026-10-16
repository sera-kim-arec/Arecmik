package kr.arecmik.widget;

import android.app.*;
import android.appwidget.*;
import android.content.*;
import android.os.Bundle;
import android.net.Uri;
import android.widget.RemoteViews;
import org.json.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;

public final class CalendarWidget extends AppWidgetProvider {
    static final String ACTION="kr.arecmik.widget.ACTION";
    @Override public void onUpdate(Context c,AppWidgetManager manager,int[] ids){for(int id:ids)update(c,id);SyncJob.schedule(c);SyncJob.scheduleNow(c,false);}
    @Override public void onAppWidgetOptionsChanged(Context c,AppWidgetManager m,int id,Bundle options){update(c,id);}
    @Override public void onDeleted(Context c,int[] ids){for(int id:ids)DataStore.prefs(c).edit().remove("day."+id).remove("month."+id).remove("space."+id).apply();}
    @Override public void onDisabled(Context c){SyncJob.cancel(c);}
    @Override public void onReceive(Context c,Intent intent){super.onReceive(c,intent);if(!ACTION.equals(intent.getAction()))return;int id=intent.getIntExtra("widget",AppWidgetManager.INVALID_APPWIDGET_ID);AppWidgetProviderInfo info=AppWidgetManager.getInstance(c).getAppWidgetInfo(id);if(info==null||!new ComponentName(c,CalendarWidget.class).equals(info.provider))return;
        try {String action=intent.getStringExtra("op");if(action==null)return;
            switch(action){
                case "prev":case "next": {YearMonth month=YearMonth.parse(DataStore.month(c,id)).plusMonths(action.equals("prev")?-1:1);DataStore.prefs(c).edit().putString("month."+id,month.toString()).putString("day."+id,month.atDay(1).toString()).commit();break;}
                case "today":DataStore.prefs(c).edit().putString("month."+id,YearMonth.now().toString()).putString("day."+id,LocalDate.now().toString()).commit();break;
                case "work":case "life":DataStore.prefs(c).edit().putString("space."+id,action).commit();break;
                case "day": {String day=LocalDate.parse(intent.getStringExtra("day")).toString();DataStore.prefs(c).edit().putString("day."+id,day).putString("month."+id,day.substring(0,7)).commit();break;}
                case "refresh":SyncJob.scheduleNow(c,true);break;
                case "toggle": {String taskId=intent.getStringExtra("task");JSONObject task=CalendarData.find(DataStore.tasks(DataStore.data(c)),taskId);if(task==null||!DataStore.space(c,id).equals(task.optString("space","work"))||!CalendarData.onDay(task,DataStore.day(c,id)))return;if(DataStore.toggle(c,taskId)){updateAll(c);SyncJob.scheduleNow(c,false);}break;}
                default:return;
            }update(c,id);
        }catch(Exception ignored){android.widget.Toast.makeText(c,"변경하지 못했어요. 연결 상태를 확인해 주세요",android.widget.Toast.LENGTH_SHORT).show();}
    }
    static void updateAll(Context c){AppWidgetManager m=AppWidgetManager.getInstance(c);for(int id:m.getAppWidgetIds(new ComponentName(c,CalendarWidget.class)))update(c,id);}
    static Intent action(Context c,int id,String op){return new Intent(c,CalendarWidget.class).setAction(ACTION).putExtra("widget",id).putExtra("op",op);}
    private static PendingIntent button(Context c,int id,String op,String day){Intent i=action(c,id,op);if(day!=null)i.putExtra("day",day);i.setData(Uri.parse("arecmik-widget://action/"+id+"/"+op+"/"+(day==null?"":day)));return PendingIntent.getBroadcast(c,0,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);}
    static void update(Context c,int id){try {
        JSONObject data=DataStore.data(c);JSONArray tasks=DataStore.tasks(data);String space=DataStore.space(c,id),selected=DataStore.day(c,id);YearMonth month=YearMonth.parse(DataStore.month(c,id));
        WidgetTheme theme=WidgetTheme.current(c);RemoteViews v=new RemoteViews(c.getPackageName(),R.layout.widget_calendar);applyTheme(c,v,theme);v.setTextViewText(R.id.month_year,month.getYear()+" · 나의 달력");v.setTextViewText(R.id.month_title,month.getMonthValue()+"월");v.setContentDescription(R.id.month_title,month.getYear()+"년 "+month.getMonthValue()+"월 · 누르면 이번 달로 이동");
        v.setOnClickPendingIntent(R.id.month_prev,button(c,id,"prev",null));v.setOnClickPendingIntent(R.id.month_next,button(c,id,"next",null));v.setOnClickPendingIntent(R.id.month_title,button(c,id,"today",null));
        v.setOnClickPendingIntent(R.id.space_work,button(c,id,"work",null));v.setOnClickPendingIntent(R.id.space_life,button(c,id,"life",null));v.setTextColor(R.id.space_work,space.equals("work")?theme.active:theme.secondary);v.setTextColor(R.id.space_life,space.equals("life")?theme.active:theme.secondary);v.setInt(R.id.space_work,"setBackgroundResource",space.equals("work")?theme.drawable(c,"space_selected"):R.drawable.day_plain);v.setInt(R.id.space_life,"setBackgroundResource",space.equals("life")?theme.drawable(c,"space_selected"):R.drawable.day_plain);
        v.setOnClickPendingIntent(R.id.widget_refresh,button(c,id,"refresh",null));v.setOnClickPendingIntent(R.id.widget_settings,PendingIntent.getActivity(c,0,new Intent(c,AppActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE));
        List<LocalDate> days=CalendarData.monthDays(month);int weeks=((int)java.time.temporal.ChronoUnit.DAYS.between(days.get(0),month.atDay(1))+month.lengthOfMonth()+6)/7;for(int week=0;week<6;week++)v.setViewVisibility(c.getResources().getIdentifier("week_"+week,"id",c.getPackageName()),week<weeks?android.view.View.VISIBLE:android.view.View.GONE);for(int i=0;i<42;i++) {
            LocalDate date=days.get(i);String key=date.toString();List<JSONObject> entries=CalendarData.forDay(tasks,key,space);String label=String.valueOf(date.getDayOfMonth());
            int view=c.getResources().getIdentifier("day_"+i,"id",c.getPackageName());v.setTextViewText(view,label);v.setViewVisibility(c.getResources().getIdentifier("mark_"+i,"id",c.getPackageName()),entries.isEmpty()?android.view.View.GONE:android.view.View.VISIBLE);v.setContentDescription(view,key+" · "+entries.size()+"개"+(entries.isEmpty()?"":" · "+entries.get(0).optString("title")));
            v.setTextColor(view,key.equals(selected)?theme.selectedText:date.getMonthValue()!=month.getMonthValue()?theme.outside:date.getDayOfWeek()==DayOfWeek.SUNDAY?theme.sunday:date.getDayOfWeek()==DayOfWeek.SATURDAY?theme.saturday:theme.primary);v.setImageViewResource(c.getResources().getIdentifier("mark_"+i,"id",c.getPackageName()),theme.drawable(c,"event_dot"));v.setInt(view,"setBackgroundResource",key.equals(selected)?theme.drawable(c,"day_selected"):date.equals(LocalDate.now())?theme.drawable(c,"day_today"):R.drawable.day_plain);v.setOnClickPendingIntent(view,button(c,id,"day",key));
        }
        List<JSONObject> selectedTasks=CalendarData.forDay(tasks,selected,space);LocalDate chosen=LocalDate.parse(selected);v.setTextViewText(R.id.selected_day,chosen.format(DateTimeFormatter.ofPattern("M월 d일 E요일",Locale.KOREAN)));v.setTextViewText(R.id.selected_count,"일정 "+selectedTasks.size());
        Intent list=new Intent(c,DayListService.class).putExtra("widget",id).setData(Uri.parse("arecmik-widget://list/"+id+"/"+selected+"/"+space));v.setRemoteAdapter(R.id.day_list,list);v.setEmptyView(R.id.day_list,R.id.day_empty);
        Intent template=action(c,id,"toggle").setData(Uri.parse("arecmik-widget://toggle/"+id));v.setPendingIntentTemplate(R.id.day_list,PendingIntent.getBroadcast(c,id,template,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_MUTABLE));
        boolean linked=SecureStore.get(c,"account")!=null;int pending=DataStore.pending(data).length();String status;
        if(!linked)status="레몬을 눌러 계정을 연결해 주세요";else if(DataStore.prefs(c).getBoolean("syncing",false))status="동기화 중…";else if(!data.optString("error").isEmpty())status=data.optString("error");else if(pending>0)status="완료 변경 "+pending+"개 전송 대기";else if(data.optLong("lastSync")>0)status="동기화 "+Instant.ofEpochMilli(data.optLong("lastSync")).atZone(ZoneId.systemDefault()).format(DateTimeFormatter.ofPattern("M/d HH:mm"));else status="오른쪽 ↻를 눌러 가져오세요";
        v.setTextViewText(R.id.sync_status,status);v.setTextViewText(R.id.day_empty,linked?"아직 일정이 없는 날이에요":"레몬을 눌러 계정을 연결해 주세요");AppWidgetManager m=AppWidgetManager.getInstance(c);m.updateAppWidget(id,v);m.notifyAppWidgetViewDataChanged(id,R.id.day_list);
    }catch(Exception ignored){/* A removed widget or unreadable keystore must not crash the launcher. */}}
    private static void applyTheme(Context c,RemoteViews v,WidgetTheme theme){
        v.setInt(R.id.widget_root,"setBackgroundResource",theme.drawable(c,"widget_bg"));
        v.setInt(R.id.space_tabs,"setBackgroundResource",theme.drawable(c,"widget_space_bg"));
        v.setInt(R.id.agenda_panel,"setBackgroundResource",theme.drawable(c,"widget_agenda_bg"));
        v.setInt(R.id.selected_count,"setBackgroundResource",theme.drawable(c,"widget_count_bg"));
        v.setTextColor(R.id.month_title,theme.primary);v.setTextColor(R.id.month_year,theme.muted);
        v.setTextColor(R.id.selected_day,theme.primary);v.setTextColor(R.id.selected_count,theme.active);
        v.setTextColor(R.id.day_empty,theme.secondary);v.setTextColor(R.id.sync_status,theme.muted);
        v.setImageViewResource(R.id.month_prev,theme.drawable(c,"ic_month_prev"));v.setImageViewResource(R.id.month_next,theme.drawable(c,"ic_month_next"));v.setImageViewResource(R.id.widget_refresh,theme.drawable(c,"ic_widget_refresh"));
        for(int i=0;i<7;i++)v.setTextColor(c.getResources().getIdentifier("weekday_"+i,"id",c.getPackageName()),i==0?theme.sunday:i==6?theme.saturday:theme.muted);
    }

}

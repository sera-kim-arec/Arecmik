package kr.arecmik.widget;

import android.content.*;
import android.widget.*;
import org.json.*;
import java.util.*;

public final class DayListService extends RemoteViewsService {
    @Override public RemoteViewsFactory onGetViewFactory(Intent intent){return new Factory(getApplicationContext(),intent.getIntExtra("widget",-1));}
    private static final class Factory implements RemoteViewsFactory {
        final Context c;final int widget;List<JSONObject> tasks=Collections.emptyList();JSONObject pending=new JSONObject();
        Factory(Context c,int widget){this.c=c;this.widget=widget;}
        public void onCreate(){onDataSetChanged();}public void onDestroy(){}public int getCount(){return tasks.size();}public int getViewTypeCount(){return 1;}public long getItemId(int p){return tasks.get(p).optString("id").hashCode();}public boolean hasStableIds(){return false;}public RemoteViews getLoadingView(){return null;}
        public void onDataSetChanged(){JSONObject data=DataStore.data(c);tasks=CalendarData.forDay(DataStore.tasks(data),DataStore.day(c,widget),DataStore.space(c,widget));pending=DataStore.pending(data);}
        public RemoteViews getViewAt(int position){if(position<0||position>=tasks.size())return null;JSONObject t=tasks.get(position);WidgetTheme theme=WidgetTheme.current(c);RemoteViews v=new RemoteViews(c.getPackageName(),R.layout.widget_item);v.setInt(R.id.widget_item_root,"setBackgroundResource",theme.drawable(c,"widget_item_bg"));v.setImageViewResource(R.id.item_check,theme.drawable(c,t.optBoolean("done")?"ic_task_done":"ic_task_open"));v.setContentDescription(R.id.item_check,t.optBoolean("done")?"완료 취소":"완료로 표시");v.setTextViewText(R.id.item_title,t.optString("title","제목 없음"));v.setTextColor(R.id.item_title,t.optBoolean("done")?theme.done:theme.primary);
            v.setInt(R.id.item_title,"setPaintFlags",android.graphics.Paint.ANTI_ALIAS_FLAG|(t.optBoolean("done")?android.graphics.Paint.STRIKE_THRU_TEXT_FLAG:0));
            String time=t.optString("time"),kind=t.optString("kind");String meta=time.isEmpty()?(kind.equals("event")?"종일 일정":"할 일"):time+" 일정";String end=t.optString("end");if(!end.isEmpty()&&end.compareTo(t.optString("date"))>0)meta+=" · "+t.optString("date").substring(5)+" – "+end.substring(5);if(!t.optString("rep").isEmpty())meta+=" · ↻";if(pending.has(t.optString("id")))meta+=" · 전송 대기";v.setTextViewText(R.id.item_meta,meta);v.setTextColor(R.id.item_meta,theme.secondary);Intent fill=new Intent().putExtra("task",t.optString("id"));v.setOnClickFillInIntent(R.id.item_check,fill);return v;
        }
    }
}

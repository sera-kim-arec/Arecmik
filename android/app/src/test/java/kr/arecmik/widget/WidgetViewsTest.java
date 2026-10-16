package kr.arecmik.widget;

import android.content.*;
import android.appwidget.AppWidgetManager;
import android.widget.*;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import java.time.*;
import static org.junit.Assert.*;
import static org.robolectric.Shadows.shadowOf;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=35)
public class WidgetViewsTest {
    Context c;AppWidgetManager manager;int id;
    @Before public void setup()throws Exception {
        c=RuntimeEnvironment.getApplication();manager=AppWidgetManager.getInstance(c);DataStore.prefs(c).edit().clear().commit();
        JSONArray tasks=new JSONArray().put(new JSONObject().put("id","t1").put("title","여행 준비").put("space","work").put("date","2026-10-20").put("end","2026-10-22").put("kind","event").put("done",false))
                .put(new JSONObject().put("id","t2").put("title","산책").put("space","life").put("date","2026-10-20").put("done",false));
        DataStore.save(c,new JSONObject().put("tasks",tasks));id=shadowOf(manager).createWidget(CalendarWidget.class,R.layout.widget_calendar);
        android.appwidget.AppWidgetProviderInfo info=new android.appwidget.AppWidgetProviderInfo();info.provider=new ComponentName(c,CalendarWidget.class);shadowOf(manager).putWidgetInfo(id,info);
        DataStore.prefs(c).edit().putString("month."+id,"2026-10").putString("day."+id,"2026-10-20").commit();CalendarWidget.update(c,id);
    }
    @Test public void remoteViewsInflateAndShowMonthAndMultiDayTitle(){android.view.View view=shadowOf(manager).getViewFor(id);assertEquals("2026년 10월",((TextView)view.findViewById(R.id.month_title)).getText().toString());assertEquals("10월 20일 · 1개",((TextView)view.findViewById(R.id.selected_day)).getText().toString());int index=(int)java.time.temporal.ChronoUnit.DAYS.between(CalendarData.monthDays(YearMonth.of(2026,10)).get(0),LocalDate.of(2026,10,20));assertTrue(((TextView)view.findViewById(c.getResources().getIdentifier("day_"+index,"id",c.getPackageName()))).getText().toString().contains("여행 준비"));}
    @Test public void selectingDateAndSpaceUpdatesWidgetWithoutNetwork(){CalendarWidget provider=new CalendarWidget();provider.onReceive(c,CalendarWidget.action(c,id,"day").putExtra("day","2026-10-21"));assertEquals("2026-10-21",DataStore.day(c,id));provider.onReceive(c,CalendarWidget.action(c,id,"life"));assertEquals("life",DataStore.space(c,id));assertEquals("10월 21일 · 0개",((TextView)shadowOf(manager).getViewFor(id).findViewById(R.id.selected_day)).getText().toString());}
    @Test public void completionIsSavedLocallyAndQueuedWithoutChangingOtherFields()throws Exception{new CalendarWidget().onReceive(c,CalendarWidget.action(c,id,"toggle").putExtra("task","t1"));JSONObject data=DataStore.data(c),task=CalendarData.find(DataStore.tasks(data),"t1");assertTrue(task.getBoolean("done"));assertEquals("2026-10-22",task.getString("end"));assertEquals(1,DataStore.pending(data).length());new CalendarWidget().onReceive(c,CalendarWidget.action(c,id,"toggle").putExtra("task","t2"));assertFalse(CalendarData.find(DataStore.tasks(DataStore.data(c)),"t2").getBoolean("done"));}
    @Test public void dayListBuildsCheckboxAndDateRange()throws Exception{DayListService service=Robolectric.buildService(DayListService.class).create().get();android.widget.RemoteViewsService.RemoteViewsFactory factory=service.onGetViewFactory(new Intent().putExtra("widget",id));factory.onCreate();assertEquals(1,factory.getCount());android.view.View row=factory.getViewAt(0).apply(c,new FrameLayout(c));assertEquals("☐",((TextView)row.findViewById(R.id.item_check)).getText().toString());assertTrue(((TextView)row.findViewById(R.id.item_meta)).getText().toString().contains("10-20 – 10-22"));}
    @Test @org.robolectric.annotation.GraphicsMode(org.robolectric.annotation.GraphicsMode.Mode.NATIVE) public void minimumWidgetSizeLeavesRoomForCalendarAndChecklist(){android.view.View view=shadowOf(manager).getViewFor(id);float density=c.getResources().getDisplayMetrics().density;int width=Math.round(250*density),height=Math.round(420*density);view.measure(android.view.View.MeasureSpec.makeMeasureSpec(width,android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(height,android.view.View.MeasureSpec.EXACTLY));view.layout(0,0,width,height);TextView day=view.findViewById(R.id.day_23);assertTrue("calendar cell height="+day.getHeight()+", line="+day.getLineHeight()+", padding="+(day.getPaddingTop()+day.getPaddingBottom())+", density="+density,day.getHeight()>=day.getLineHeight()*2+day.getPaddingTop()+day.getPaddingBottom());android.view.View listArea=(android.view.View)view.findViewById(R.id.day_list).getParent();assertTrue("list area height="+listArea.getHeight(),listArea.getHeight()>=60*density);}
}

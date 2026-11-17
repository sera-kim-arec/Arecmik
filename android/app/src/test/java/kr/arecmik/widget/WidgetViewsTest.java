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
    @Test public void remoteViewsInflateAndMarkDaysWithMultiDayEvents(){android.view.View view=shadowOf(manager).getViewFor(id);assertEquals("10월",((TextView)view.findViewById(R.id.month_title)).getText().toString());assertEquals("10월 20일 화요일",((TextView)view.findViewById(R.id.selected_day)).getText().toString());int index=(int)java.time.temporal.ChronoUnit.DAYS.between(CalendarData.monthDays(YearMonth.of(2026,10)).get(0),LocalDate.of(2026,10,20));assertEquals(android.view.View.VISIBLE,view.findViewById(c.getResources().getIdentifier("mark_"+index,"id",c.getPackageName())).getVisibility());assertEquals("일정 1",((TextView)view.findViewById(R.id.selected_count)).getText().toString());}
    @Test public void selectingDateAndSpaceUpdatesWidgetWithoutNetwork(){CalendarWidget provider=new CalendarWidget();provider.onReceive(c,CalendarWidget.action(c,id,"day").putExtra("day","2026-10-21"));assertEquals("2026-10-21",DataStore.day(c,id));provider.onReceive(c,CalendarWidget.action(c,id,"life"));assertEquals("life",DataStore.space(c,id));assertEquals("10월 21일 수요일",((TextView)shadowOf(manager).getViewFor(id).findViewById(R.id.selected_day)).getText().toString());}
    @Test public void sixthWeekOnlyAppearsWhenTheMonthNeedsIt(){
        assertEquals(android.view.View.GONE,shadowOf(manager).getViewFor(id).findViewById(R.id.week_5).getVisibility());
        DataStore.prefs(c).edit().putString("month."+id,"2026-08").commit();CalendarWidget.update(c,id);
        assertEquals(android.view.View.VISIBLE,shadowOf(manager).getViewFor(id).findViewById(R.id.week_5).getVisibility());
    }
    @Test public void settingsSwitchAllThemesAndPreserveCalendarData(){
        String before=DataStore.data(c).toString();assertEquals(WidgetTheme.GLASS,WidgetTheme.current(c));
        var activity=Robolectric.buildActivity(MainActivity.class).create().start().resume();
        String[] labels={"레몬 크림 · 포근하고 깔끔하게","흑백 · 최대한 미니멀하게","반투명 · 배경화면이 보이게"};WidgetTheme[] themes={WidgetTheme.LEMON,WidgetTheme.MONO,WidgetTheme.GLASS};
        for(int i=0;i<labels.length;i++){
            java.util.ArrayList<android.view.View> matches=new java.util.ArrayList<>();activity.get().getWindow().getDecorView().findViewsWithText(matches,labels[i],android.view.View.FIND_VIEWS_WITH_TEXT);assertEquals(1,matches.size());matches.get(0).performClick();
            assertEquals(themes[i],WidgetTheme.current(c));assertEquals(themes[i].primary,((TextView)shadowOf(manager).getViewFor(id).findViewById(R.id.month_title)).getCurrentTextColor());assertEquals(before,DataStore.data(c).toString());assertEquals("2026-10-20",DataStore.day(c,id));
        }
        activity.pause().stop().destroy();
    }
    @Test public void completionIsSavedLocallyAndQueuedWithoutChangingOtherFields()throws Exception{new CalendarWidget().onReceive(c,CalendarWidget.action(c,id,"toggle").putExtra("task","t1"));JSONObject data=DataStore.data(c),task=CalendarData.find(DataStore.tasks(data),"t1");assertTrue(task.getBoolean("done"));assertEquals("2026-10-22",task.getString("end"));assertEquals(1,DataStore.pending(data).length());new CalendarWidget().onReceive(c,CalendarWidget.action(c,id,"toggle").putExtra("task","t2"));assertFalse(CalendarData.find(DataStore.tasks(DataStore.data(c)),"t2").getBoolean("done"));}
    @Test public void dayListBuildsCheckboxAndDateRange()throws Exception{DayListService service=Robolectric.buildService(DayListService.class).create().get();android.widget.RemoteViewsService.RemoteViewsFactory factory=service.onGetViewFactory(new Intent().putExtra("widget",id));factory.onCreate();assertEquals(1,factory.getCount());android.view.View row=factory.getViewAt(0).apply(c,new FrameLayout(c));assertNotNull(((ImageView)row.findViewById(R.id.item_check)).getDrawable());assertEquals("완료로 표시",row.findViewById(R.id.item_check).getContentDescription());assertTrue(((TextView)row.findViewById(R.id.item_meta)).getText().toString().contains("10-20 – 10-22"));}
    @Test @org.robolectric.annotation.GraphicsMode(org.robolectric.annotation.GraphicsMode.Mode.NATIVE) public void minimumWidgetSizeLeavesRoomForCalendarAndChecklist(){android.view.View view=shadowOf(manager).getViewFor(id);float density=c.getResources().getDisplayMetrics().density;int width=Math.round(280*density),height=Math.round(480*density);view.measure(android.view.View.MeasureSpec.makeMeasureSpec(width,android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(height,android.view.View.MeasureSpec.EXACTLY));view.layout(0,0,width,height);TextView day=view.findViewById(R.id.day_23);assertTrue("calendar cell height="+day.getHeight()+", line="+day.getLineHeight()+", padding="+(day.getPaddingTop()+day.getPaddingBottom())+", density="+density,day.getHeight()>=day.getLineHeight()+day.getPaddingTop()+day.getPaddingBottom());assertTrue(day.getTextSize()/c.getResources().getDisplayMetrics().scaledDensity>=17);android.view.View listArea=(android.view.View)view.findViewById(R.id.day_list).getParent();assertTrue("list area height="+listArea.getHeight(),listArea.getHeight()>=60*density);}
    @Test @org.robolectric.annotation.GraphicsMode(org.robolectric.annotation.GraphicsMode.Mode.NATIVE) public void enlargedTextFitsCalendarAndAgenda()throws Exception{
        RuntimeEnvironment.setFontScale(1.3f);int largeId=shadowOf(manager).createWidget(CalendarWidget.class,R.layout.widget_calendar);DataStore.prefs(c).edit().putString("month."+largeId,"2026-10").putString("day."+largeId,"2026-10-20").commit();CalendarWidget.update(c,largeId);
        android.view.View view=shadowOf(manager).getViewFor(largeId);float density=c.getResources().getDisplayMetrics().density;
        int width=Math.round(320*density),height=Math.round(540*density);view.measure(android.view.View.MeasureSpec.makeMeasureSpec(width,android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(height,android.view.View.MeasureSpec.EXACTLY));view.layout(0,0,width,height);
        TextView day=view.findViewById(R.id.day_23);assertEquals(1,day.getMaxLines());assertTrue(day.getHeight()>=day.getLineHeight()+day.getPaddingTop()+day.getPaddingBottom());assertEquals(0,day.getLayout().getEllipsisCount(0));
        DayListService service=Robolectric.buildService(DayListService.class).create().get();android.widget.RemoteViewsService.RemoteViewsFactory factory=service.onGetViewFactory(new Intent().putExtra("widget",id));factory.onCreate();android.view.View row=factory.getViewAt(0).apply(c,new FrameLayout(c));assertEquals(Math.round(android.util.TypedValue.applyDimension(android.util.TypedValue.COMPLEX_UNIT_SP,16,c.getResources().getDisplayMetrics())),((TextView)row.findViewById(R.id.item_title)).getTextSize(),0.1f);
        FrameLayout area=(FrameLayout)view.findViewById(R.id.day_list).getParent();view.findViewById(R.id.day_list).setVisibility(android.view.View.GONE);view.findViewById(R.id.day_empty).setVisibility(android.view.View.GONE);area.addView(row,new FrameLayout.LayoutParams(-1,-2));view.measure(android.view.View.MeasureSpec.makeMeasureSpec(width,android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(height,android.view.View.MeasureSpec.EXACTLY));view.layout(0,0,width,height);
        for(WidgetTheme theme:WidgetTheme.values()){
            DataStore.prefs(c).edit().putString("theme",theme.key).commit();int previewId=shadowOf(manager).createWidget(CalendarWidget.class,R.layout.widget_calendar);DataStore.prefs(c).edit().putString("month."+previewId,"2026-10").putString("day."+previewId,"2026-10-20").commit();CalendarWidget.update(c,previewId);
            android.view.View example=shadowOf(manager).getViewFor(previewId);FrameLayout panel=(FrameLayout)example.findViewById(R.id.day_list).getParent();example.findViewById(R.id.day_list).setVisibility(android.view.View.GONE);example.findViewById(R.id.day_empty).setVisibility(android.view.View.GONE);panel.addView(factory.getViewAt(0).apply(c,panel),new FrameLayout.LayoutParams(-1,-2));
            example.measure(android.view.View.MeasureSpec.makeMeasureSpec(width,android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(height,android.view.View.MeasureSpec.EXACTLY));example.layout(0,0,width,height);
            android.graphics.Bitmap preview=android.graphics.Bitmap.createBitmap(width,height,android.graphics.Bitmap.Config.ARGB_8888);android.graphics.Canvas canvas=new android.graphics.Canvas(preview);
            canvas.drawColor(android.graphics.Color.rgb(161,182,167));example.draw(canvas);java.io.File report=new java.io.File("build/reports/widget-preview-"+theme.key+".png");report.getParentFile().mkdirs();try(java.io.FileOutputStream out=new java.io.FileOutputStream(report)){preview.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out);}
        }
        RuntimeEnvironment.setFontScale(1f);
    }
}

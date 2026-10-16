package kr.arecmik.widget;
import org.junit.Test;
import org.json.*;
import java.time.*;
import java.util.*;
import static org.junit.Assert.*;

public class CalendarDataTest {
    private JSONObject task(String date,String end,String space,boolean done)throws Exception{return new JSONObject().put("id",UUID.randomUUID().toString()).put("title","테스트").put("date",date).put("end",end).put("space",space).put("done",done);}
    @Test public void monthContains42ConsecutiveDaysAndSundayStart(){List<LocalDate> days=CalendarData.monthDays(YearMonth.of(2026,10));assertEquals(42,days.size());assertEquals(LocalDate.of(2026,9,27),days.get(0));assertEquals(LocalDate.of(2026,11,7),days.get(41));}
    @Test public void inclusiveRangeAndSpacesDoNotLeak()throws Exception{JSONArray tasks=new JSONArray().put(task("2026-10-20","2026-10-23","work",false)).put(task("2026-10-20","","life",false));assertEquals(1,CalendarData.forDay(tasks,"2026-10-23","work").size());assertEquals(0,CalendarData.forDay(tasks,"2026-10-24","work").size());assertEquals(1,CalendarData.forDay(tasks,"2026-10-20","life").size());}
    @Test public void dateOnlyTasksAndFinishedTasksSortPredictably()throws Exception{JSONArray tasks=new JSONArray().put(task("2026-10-20","","work",true)).put(task("2026-10-20","","work",false).put("time","14:00")).put(task("2026-10-20","","work",false).put("kind","event"));List<JSONObject> sorted=CalendarData.forDay(tasks,"2026-10-20","work");assertEquals("event",sorted.get(0).getString("kind"));assertTrue(sorted.get(2).getBoolean("done"));}
    @Test public void firestoreRoundTripPreservesNestedFields()throws Exception{JSONObject t=task("2026-10-20","","life",false).put("subs",new JSONArray().put(new JSONObject().put("t","준비").put("done",false))).put("doneAt",1792454400000L).put("repN",2);JSONObject round=CalendarData.decodeFields(CalendarData.fields(t));assertEquals(t.getString("id"),round.getString("id"));assertEquals(1792454400000L,round.getLong("doneAt"));assertFalse(round.getJSONArray("subs").getJSONObject(0).getBoolean("done"));}
    @Test public void repetitionsClampMonthsAndSkipWeekends()throws Exception{assertEquals(LocalDate.of(2026,2,28),CalendarData.nextRepeat(new JSONObject().put("date","2026-01-31").put("rep","m")));assertEquals(LocalDate.of(2026,10,19),CalendarData.nextRepeat(new JSONObject().put("date","2026-10-16").put("rep","wd")));assertEquals(LocalDate.of(2026,11,2),CalendarData.nextRepeat(new JSONObject().put("date","2026-10-21").put("rep","c").put("repU","w").put("repN",2).put("repW",new JSONArray().put(1))));}
    @Test public void nextOccurrencePreservesDurationAndResetsSubtasks()throws Exception{JSONObject t=task("2026-10-20","2026-10-22","work",true).put("rep","w").put("note","회고").put("subs",new JSONArray().put(new JSONObject().put("t","준비").put("done",true)));JSONObject next=CalendarData.nextCopy(t,LocalDate.of(2026,10,27));assertEquals("2026-10-29",next.getString("end"));assertEquals("w",next.getString("rep"));assertFalse(next.has("id"));assertFalse(next.getBoolean("done"));assertFalse(next.getJSONArray("subs").getJSONObject(0).getBoolean("done"));assertEquals("",next.getString("note"));}
}

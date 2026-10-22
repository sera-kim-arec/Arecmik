package kr.arecmik.widget;

import org.json.*;
import org.junit.*;
import java.time.*;
import static org.junit.Assert.*;

public class ReminderPlanTest {
    final ZoneId zone=ZoneId.of("Asia/Seoul");
    JSONObject event()throws Exception{return new JSONObject().put("id","event").put("kind","event").put("date","2026-10-22").put("time","14:00");}
    long at(String time){return LocalDateTime.parse("2026-10-22T"+time).atZone(zone).toInstant().toEpochMilli();}
    @Test public void defaultsToFifteenMinutesAndExplicitChoiceOverridesDevice()throws Exception{assertEquals(at("13:45"),ReminderPlan.when(event(),"15",zone));assertEquals(at("13:00"),ReminderPlan.when(event().put("reminder","60"),"15",zone));assertEquals(at("14:00"),ReminderPlan.when(event().put("reminder","0"),"15",zone));}
    @Test public void allDayAndMultiDayEventsNotifyOnceOnStartMorning()throws Exception{assertEquals(at("09:00"),ReminderPlan.when(event().put("time","").put("end","2026-10-25"),"15",zone));assertEquals(at("09:00"),ReminderPlan.when(event().put("reminder","morning"),"15",zone));}
    @Test public void noAlarmForCompletedUndatedOffOrOrdinaryTask()throws Exception{assertEquals(0,ReminderPlan.when(event().put("done",true),"15",zone));assertEquals(0,ReminderPlan.when(event().put("date",""),"15",zone));assertEquals(0,ReminderPlan.when(event().put("reminder","off"),"15",zone));JSONObject task=event().put("kind","todo").put("time","");assertEquals(0,ReminderPlan.when(task,"15",zone));assertEquals(at("09:00"),ReminderPlan.when(task.put("reminder","morning"),"15",zone));}
    @Test public void invalidDatesAndTimesDoNotCrashOrRollOver()throws Exception{assertEquals(0,ReminderPlan.when(event().put("date","2026-02-30"),"15",zone));assertEquals(0,ReminderPlan.when(event().put("time","25:00"),"15",zone));}
    @Test public void midnightLeadCrossesDateAndUsesPhoneTimezone()throws Exception{JSONObject t=event().put("time","00:05");assertEquals(LocalDateTime.parse("2026-10-21T23:50").atZone(zone).toInstant().toEpochMilli(),ReminderPlan.when(t,"15",zone));assertNotEquals(ReminderPlan.when(t,"15",zone),ReminderPlan.when(t,"15",ZoneId.of("UTC")));}
}

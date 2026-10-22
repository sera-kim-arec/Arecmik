package kr.arecmik.widget;

import org.json.JSONObject;
import java.time.*;

/** One reminder for the start of an occurrence, in the phone's local timezone. */
final class ReminderPlan {
    static final String[] VALUES={"default","off","0","15","30","60","morning"};
    static String choice(String value){for(String v:VALUES)if(v.equals(value))return v;return "default";}
    static long when(JSONObject task,String defaultLead,ZoneId zone){
        try{
            if(task.optBoolean("done")||task.optString("date").isEmpty())return 0;
            String raw=task.optString("reminder","default"),lead=choice(raw);if(!raw.equals(lead))return 0;
            if("off".equals(lead))return 0;
            if("default".equals(lead)){
                if(!"event".equals(task.optString("kind"))&&task.optString("time").isEmpty())return 0;
                lead=choice(defaultLead);if("default".equals(lead)||"off".equals(lead))lead="15";
            }
            LocalDate date=LocalDate.parse(task.getString("date"));String time=task.optString("time");
            if(time.isEmpty()||"morning".equals(lead))return date.atTime(9,0).atZone(zone).toInstant().toEpochMilli();
            if(!time.matches("([01]\\d|2[0-3]):[0-5]\\d"))return 0;
            return date.atTime(LocalTime.parse(time)).atZone(zone).minusMinutes(Long.parseLong(lead)).toInstant().toEpochMilli();
        }catch(Exception ignored){return 0;}
    }
    static String key(JSONObject task,long at){return task.optString("id")+"|"+task.optString("date")+"|"+task.optString("time")+"|"+at;}
}

package kr.arecmik.widget;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.*;
import java.time.*;

final class DataStore {
    static SharedPreferences prefs(Context c){return c.getSharedPreferences("calendar",0);}
    static synchronized JSONObject data(Context c){try{return new JSONObject(prefs(c).getString("data","{}"));}catch(Exception e){return new JSONObject();}}
    static synchronized void save(Context c,JSONObject data){if(!prefs(c).edit().putString("data",data.toString()).commit())throw new IllegalStateException("기기 저장 공간을 확인해 주세요");}
    static JSONArray tasks(JSONObject data){return data.optJSONArray("tasks")==null?new JSONArray():data.optJSONArray("tasks");}
    static JSONObject pending(JSONObject data){return data.optJSONObject("pending")==null?new JSONObject():data.optJSONObject("pending");}
    static String day(Context c,int id){return prefs(c).getString("day."+id,LocalDate.now().toString());}
    static String month(Context c,int id){return prefs(c).getString("month."+id,YearMonth.now().toString());}
    static String space(Context c,int id){return prefs(c).getString("space."+id,"work");}
    static synchronized boolean toggle(Context c,String id) throws Exception {
        JSONObject data=data(c);JSONArray tasks=tasks(data);JSONObject task=CalendarData.find(tasks,id);if(task==null)return false;
        boolean done=!task.optBoolean("done");long now=System.currentTimeMillis();
        JSONObject patch=new JSONObject().put("done",done).put("doneDate",done?LocalDate.now().toString():"").put("doneAt",done?now:0);
        JSONObject queue=pending(data);JSONObject previous=queue.optJSONObject(id);String nextId=previous==null?"widget-"+java.util.UUID.randomUUID():previous.optString("nextId","widget-"+java.util.UUID.randomUUID());
        queue.put(id,new JSONObject().put("patch",patch).put("version",java.util.UUID.randomUUID().toString()).put("nextId",nextId));
        for(String k:CalendarData.keys(patch))task.put(k,patch.get(k));data.put("tasks",tasks).put("pending",queue);save(c,data);return true;
    }
    static void clear(Context c){prefs(c).edit().remove("data").commit();}
}

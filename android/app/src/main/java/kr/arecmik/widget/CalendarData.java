package kr.arecmik.widget;

import org.json.*;
import java.time.*;
import java.time.temporal.ChronoUnit;
import java.util.*;

/** Shared date and Firestore mapping logic; no Android dependencies. */
final class CalendarData {
    static List<String> keys(JSONObject o){List<String> keys=new ArrayList<>();o.keys().forEachRemaining(keys::add);return keys;}
    static JSONObject find(JSONArray tasks,String id){for(int i=0;i<tasks.length();i++){JSONObject t=tasks.optJSONObject(i);if(t!=null&&id.equals(t.optString("id")))return t;}return null;}
    static boolean onDay(JSONObject t,String day){String start=t.optString("date"),end=t.optString("end",start);if(end.compareTo(start)<0)end=start;return !start.isEmpty()&&start.compareTo(day)<=0&&end.compareTo(day)>=0;}
    static List<JSONObject> forDay(JSONArray tasks,String day,String space){List<JSONObject> result=new ArrayList<>();for(int i=0;i<tasks.length();i++){JSONObject t=tasks.optJSONObject(i);if(t!=null&&space.equals(t.optString("space","work"))&&onDay(t,day))result.add(t);}result.sort(Comparator.comparing((JSONObject t)->t.optBoolean("done")).thenComparing(t->t.optString("time").isEmpty()?"00:00":t.optString("time")).thenComparing(t->t.optString("title")));return result;}
    static List<LocalDate> monthDays(YearMonth month){LocalDate first=month.atDay(1);first=first.minusDays(first.getDayOfWeek().getValue()%7);List<LocalDate> result=new ArrayList<>();for(int i=0;i<42;i++)result.add(first.plusDays(i));return result;}
    static JSONObject decodeFields(JSONObject fields) throws Exception {JSONObject out=new JSONObject();for(String k:keys(fields))out.put(k,decode(fields.getJSONObject(k)));return out;}
    static Object decode(JSONObject v) throws Exception {
        if(v.has("stringValue"))return v.getString("stringValue");if(v.has("booleanValue"))return v.getBoolean("booleanValue");if(v.has("integerValue"))return v.getLong("integerValue");if(v.has("doubleValue"))return v.getDouble("doubleValue");
        if(v.has("mapValue"))return decodeFields(v.getJSONObject("mapValue").optJSONObject("fields")==null?new JSONObject():v.getJSONObject("mapValue").getJSONObject("fields"));
        if(v.has("arrayValue")){JSONArray a=v.getJSONObject("arrayValue").optJSONArray("values"),out=new JSONArray();if(a!=null)for(int i=0;i<a.length();i++)out.put(decode(a.getJSONObject(i)));return out;}return JSONObject.NULL;
    }
    static JSONObject fields(JSONObject object) throws Exception {JSONObject out=new JSONObject();for(String k:keys(object))out.put(k,encode(object.get(k)));return out;}
    static JSONObject encode(Object v) throws Exception {
        JSONObject out=new JSONObject();if(v==null||v==JSONObject.NULL)return out.put("nullValue",JSONObject.NULL);if(v instanceof Boolean)return out.put("booleanValue",v);if(v instanceof Integer||v instanceof Long)return out.put("integerValue",String.valueOf(v));if(v instanceof Number)return out.put("doubleValue",v);if(v instanceof JSONObject)return out.put("mapValue",new JSONObject().put("fields",fields((JSONObject)v)));if(v instanceof JSONArray){JSONArray values=new JSONArray();for(int i=0;i<((JSONArray)v).length();i++)values.put(encode(((JSONArray)v).get(i)));return out.put("arrayValue",new JSONObject().put("values",values));}return out.put("stringValue",String.valueOf(v));
    }
    static LocalDate nextRepeat(JSONObject t){LocalDate d=LocalDate.parse(t.optString("date"));String r=t.optString("rep");int n=Math.max(1,t.optInt("repN",1));return switch(r){
        case "d" -> d.plusDays(1);case "wd" -> {LocalDate x=d.plusDays(1);while(x.getDayOfWeek().getValue()>5)x=x.plusDays(1);yield x;}
        case "w" -> d.plusWeeks(1);case "w2" -> d.plusWeeks(2);case "m" -> clampedMonth(d,1,t.optInt("repDay",d.getDayOfMonth()));case "y" -> jsYear(d,1);
        case "c" -> switch(t.optString("repU","d")){case "d" -> d.plusDays(n);case "m" -> clampedMonth(d,n,t.optInt("repDay",d.getDayOfMonth()));case "y" -> jsYear(d,n);default -> {TreeSet<Integer> days=new TreeSet<>();JSONArray a=t.optJSONArray("repW");if(a!=null)for(int i=0;i<a.length();i++)days.add(a.optInt(i));int current=d.getDayOfWeek().getValue()%7;if(days.isEmpty())days.add(current);Integer next=days.higher(current);yield d.plusDays(next!=null?next-current:7-current+7L*(n-1)+days.first());}};
        default -> null;
    };}
    private static LocalDate clampedMonth(LocalDate d,int n,int anchor){YearMonth m=YearMonth.from(d).plusMonths(n);return m.atDay(Math.max(1,Math.min(anchor,m.lengthOfMonth())));}
    private static LocalDate jsYear(LocalDate d,int n){return LocalDate.of(d.getYear()+n,d.getMonthValue(),1).plusDays(d.getDayOfMonth()-1);}
    static JSONObject nextCopy(JSONObject original,LocalDate next) throws Exception {JSONObject t=new JSONObject(original.toString());t.remove("id");t.remove("_updateTime");LocalDate start=LocalDate.parse(original.getString("date"));String end=original.optString("end");t.put("date",next.toString()).put("end",!end.isEmpty()&&end.compareTo(start.toString())>0?next.plusDays(ChronoUnit.DAYS.between(start,LocalDate.parse(end))).toString():"");t.put("done",false).put("doneDate","").put("doneAt",0).put("note","").put("created",System.currentTimeMillis());JSONArray subs=t.optJSONArray("subs");if(subs!=null)for(int i=0;i<subs.length();i++)subs.getJSONObject(i).put("done",false);return t;}
}

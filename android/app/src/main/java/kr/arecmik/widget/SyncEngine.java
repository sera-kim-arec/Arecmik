package kr.arecmik.widget;

import android.content.Context;
import android.icu.util.ChineseCalendar;
import org.json.*;
import java.time.*;
import java.util.*;

final class SyncEngine {
    static final Object LOCK=new Object();
    static String base(JSONObject account) throws Exception {return "https://firestore.googleapis.com/v1/projects/"+BuildConfigData.PROJECT+"/databases/(default)/documents/users/"+account.getString("uid")+"/todos";}
    static JSONObject getTask(Context c,String root,String id,String token) throws Exception {
        if(!id.matches("[A-Za-z0-9_-]{1,128}"))throw new SecurityException("Invalid ID");
        claimReads(c,1);JSONObject doc=Network.request("GET",root+"/"+id,null,token);return CalendarData.decodeFields(doc.optJSONObject("fields")==null?new JSONObject():doc.getJSONObject("fields")).put("id",id).put("_updateTime",doc.getString("updateTime"));
    }
    static void sync(Context context,boolean force) {
        Context c=context.getApplicationContext();synchronized(LOCK){try {
            JSONObject account=SecureStore.get(c,"account");if(account==null){CalendarWidget.updateAll(c);return;}
            JSONObject before=DataStore.data(c);JSONObject queue=DataStore.pending(before);long last=before.optLong("lastSync");
            if(!force&&queue.length()==0&&System.currentTimeMillis()-last<45*60*1000){CalendarWidget.updateAll(c);return;}
            DataStore.prefs(c).edit().putBoolean("syncing",true).apply();CalendarWidget.updateAll(c);
            long reminderReadAt=System.currentTimeMillis();String token=Network.token(c,account),root=base(account);
            for(String id:CalendarData.keys(queue)) {
                JSONObject op=queue.getJSONObject(id),patch=op.getJSONObject("patch");
                try {
                    JSONObject server=getTask(c,root,id,token);JSONArray writes=new JSONArray();JSONObject applied=new JSONObject(patch.toString());
                    if(patch.optBoolean("done")&&!server.optBoolean("done")&&!server.optString("rep").isEmpty()&&!server.optString("date").isEmpty()) {
                        LocalDate next="ly".equals(server.optString("rep"))?nextLunar(LocalDate.parse(server.getString("date"))):CalendarData.nextRepeat(server);
                        if(next==null)throw new IllegalStateException("이 반복 일정은 앱에서 완료해 주세요");
                        String nextName=docName(account,op.getString("nextId"));
                        JSONObject nextTask=CalendarData.nextCopy(server,next);
                        writes.put(new JSONObject().put("update",new JSONObject().put("name",nextName).put("fields",CalendarData.fields(nextTask))).put("currentDocument",new JSONObject().put("exists",false)));
                        applied.put("rep","").put("repeatUndo",CalendarData.repeatUndo(server,op.getString("nextId"),nextTask));
                    }else if(!patch.optBoolean("done")&&server.optBoolean("done")&&server.optJSONObject("repeatUndo")!=null){
                        JSONObject undo=server.getJSONObject("repeatUndo"),next=null;try{next=getTask(c,root,undo.getString("nextId"),token);}catch(Network.Failure failure){if(failure.status!=404)throw failure;}
                        if(next!=null){if(!CalendarData.unmodifiedNext(next,undo.getJSONObject("next")))throw new IllegalStateException("다음 반복을 수정해서 취소하지 않았어요. 앱에서 다음 일정을 확인해 주세요");writes.put(new JSONObject().put("delete",docName(account,undo.getString("nextId"))).put("currentDocument",new JSONObject().put("updateTime",next.getString("_updateTime"))));}
                        applied.put("rep",undo.getString("rep")).put("repDay",undo.getInt("repDay")).put("repeatUndo",JSONObject.NULL);
                    }
                    // Both writes commit together. A failed retry never creates a second repetition.
                    JSONArray masks=new JSONArray(CalendarData.keys(applied));writes.put(new JSONObject().put("update",new JSONObject().put("name",docName(account,id)).put("fields",CalendarData.fields(applied))).put("updateMask",new JSONObject().put("fieldPaths",masks)).put("currentDocument",new JSONObject().put("updateTime",server.getString("_updateTime"))));
                    Network.request("POST","https://firestore.googleapis.com/v1/projects/"+BuildConfigData.PROJECT+"/databases/(default)/documents:commit",new JSONObject().put("writes",writes),token);
                    synchronized(DataStore.class){JSONObject current=DataStore.data(c),pending=DataStore.pending(current);JSONObject latest=pending.optJSONObject(id);if(latest!=null&&op.getString("version").equals(latest.optString("version")))pending.remove(id);current.put("pending",pending);DataStore.save(c,current);}
                }catch(Network.Failure failure){if(failure.status!=404)throw failure;synchronized(DataStore.class){JSONObject current=DataStore.data(c),pending=DataStore.pending(current);pending.remove(id);current.put("pending",pending);DataStore.save(c,current);}}
            }
            // Fetch all dates once, so month navigation and day selection use no extra reads.
            JSONArray tasks=new JSONArray();String page="";int pages=0;
            do {
                claimReads(c,300);
                JSONObject response=Network.request("GET",root+"?pageSize=300"+(page.isEmpty()?"":"&pageToken="+java.net.URLEncoder.encode(page,"UTF-8")),null,token);
                JSONArray docs=response.optJSONArray("documents");if(docs!=null)for(int i=0;i<docs.length();i++){JSONObject doc=docs.getJSONObject(i);String name=doc.getString("name");JSONObject task=CalendarData.decodeFields(doc.optJSONObject("fields")==null?new JSONObject():doc.getJSONObject("fields"));task.put("id",name.substring(name.lastIndexOf('/')+1));tasks.put(task);}
                page=response.optString("nextPageToken");if(++pages>50)throw new IllegalStateException("일정이 너무 많아요. 앱에서 오래된 기록을 정리해 주세요");
            }while(!page.isEmpty());
            synchronized(DataStore.class){JSONObject current=DataStore.data(c),pending=DataStore.pending(current);for(String id:CalendarData.keys(pending)){JSONObject task=CalendarData.find(tasks,id);if(task!=null){JSONObject p=pending.getJSONObject(id).getJSONObject("patch");for(String k:CalendarData.keys(p))task.put(k,p.get(k));}}current.put("tasks",tasks).put("lastSync",System.currentTimeMillis()).put("error","");DataStore.save(c,current);}
            ReminderScheduler.update(c,account.getString("uid"),DataStore.tasks(DataStore.data(c)),reminderReadAt);
            DataStore.prefs(c).edit().putInt("syncFailures",0).apply();if(DataStore.pending(DataStore.data(c)).length()>0)SyncJob.scheduleSoon(c);
        }catch(Exception e){synchronized(DataStore.class){JSONObject current=DataStore.data(c);try{current.put("error",e instanceof Network.Failure?e.getMessage():e instanceof IllegalStateException?e.getMessage():"인터넷 연결을 기다리고 있어요");DataStore.save(c,current);}catch(Exception ignored){}}DataStore.prefs(c).edit().putInt("syncFailures",Math.min(6,DataStore.prefs(c).getInt("syncFailures",0)+1)).apply();if(!(e instanceof Network.Failure failure&&(failure.status==401||failure.status==403)))SyncJob.scheduleSoon(c);
        }finally{DataStore.prefs(c).edit().putBoolean("syncing",false).apply();CalendarWidget.updateAll(c);}}
    }
    static String docName(JSONObject account,String id)throws Exception{return "projects/"+BuildConfigData.PROJECT+"/databases/(default)/documents/users/"+account.getString("uid")+"/todos/"+id;}
    private static void claimReads(Context c,int count){String day=LocalDate.now().toString();int used=day.equals(DataStore.prefs(c).getString("readsDay",""))?DataStore.prefs(c).getInt("reads",0):0;if(used+count>20000)throw new IllegalStateException("오늘의 위젯 동기화 한도에 도달했어요. 내일 다시 가져옵니다");DataStore.prefs(c).edit().putString("readsDay",day).putInt("reads",used+count).commit();}
    static LocalDate nextLunar(LocalDate date){ChineseCalendar original=chinese(date);int month=original.get(ChineseCalendar.MONTH),day=original.get(ChineseCalendar.DAY_OF_MONTH);for(int wanted:new int[]{day,day==30?29:day})for(int i=300;i<=430;i++){LocalDate next=date.plusDays(i);ChineseCalendar c=chinese(next);if(c.get(ChineseCalendar.MONTH)==month&&c.get(ChineseCalendar.DAY_OF_MONTH)==wanted&&c.get(ChineseCalendar.IS_LEAP_MONTH)==0)return next;}return date.plusDays(365);}
    private static ChineseCalendar chinese(LocalDate date){ChineseCalendar c=new ChineseCalendar(android.icu.util.TimeZone.getTimeZone("Asia/Seoul"));c.setTimeInMillis(date.atTime(12,0).atZone(ZoneId.of("Asia/Seoul")).toInstant().toEpochMilli());return c;}
}

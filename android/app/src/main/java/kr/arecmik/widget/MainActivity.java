package kr.arecmik.widget;

import android.app.*;
import android.appwidget.*;
import android.content.*;
import android.net.Uri;
import android.os.Bundle;
import android.view.*;
import android.widget.*;
import org.json.*;

public final class MainActivity extends Activity {
    private TextView status,reminderStatus;
    @Override public void onCreate(Bundle saved){super.onCreate(saved);draw();Uri uri=getIntent().getData();if(uri!=null&&"arecmik-widget".equals(uri.getScheme()))connect(uri);}
    @Override protected void onResume(){super.onResume();if(status!=null)showStatus();if(reminderStatus!=null)showReminders();ReminderScheduler.reschedule(this);}
    private int dp(int x){return Math.round(x*getResources().getDisplayMetrics().density);}
    private void draw(){ScrollView scroll=new ScrollView(this);LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(24),dp(30),dp(24),dp(30));scroll.addView(content);scroll.setBackgroundColor(0xfff4f3f0);setContentView(scroll);scroll.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(0,insets.getSystemWindowInsetTop(),0,insets.getSystemWindowInsetBottom());return insets;});
        ImageView lemon=new ImageView(this);lemon.setImageResource(R.mipmap.ic_launcher);lemon.setContentDescription("Arecmik 레몬");content.addView(lemon,new LinearLayout.LayoutParams(dp(64),dp(64)));
        TextView title=new TextView(this);title.setText("Arecmik\n위젯 · 계정 설정");title.setTextSize(30);title.setTextColor(0xff343a34);content.addView(title);TextView intro=new TextView(this);intro.setText("달력에서 날짜를 고르고, 아래 목록에서 일정과 할 일을 완료하세요.\nWORK / LIFE를 따로 볼 수 있어요.");intro.setTextSize(15);intro.setPadding(0,dp(20),0,dp(20));content.addView(intro);status=new TextView(this);status.setTextSize(14);content.addView(status);
        reminderPicker(content,scroll);themePicker(content);
        button(content,"1. 브라우저에서 계정 연결",()->{try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(Pairing.start(this,true))));}catch(Exception e){message("브라우저를 열지 못했어요. 기본 브라우저를 확인해 주세요.");}});
        button(content,"2. 홈 화면에 위젯 추가",()->{AppWidgetManager manager=getSystemService(AppWidgetManager.class);if(manager.isRequestPinAppWidgetSupported())manager.requestPinAppWidget(new ComponentName(this,CalendarWidget.class),null,null);else message("홈 화면의 빈 곳을 길게 누르고 ‘위젯’에서 ‘Arecmik’을 추가해 주세요.");});
        button(content,"지금 동기화",()->{status.setText("동기화 중…");new Thread(()->{SyncEngine.sync(this,true);runOnUiThread(this::showStatus);}).start();});
        button(content,"APK 설치 · 업데이트",()->startActivity(new Intent(this,UpdateActivity.class)));
        button(content,"일정 · 기록 화면 열기",()->{startActivity(new Intent(this,AppActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP));finish();});
        button(content,"이 휴대폰 연결 해제",()->new AlertDialog.Builder(this).setMessage("이 휴대폰에 보관한 연결 정보와 달력을 지울까요? 전송 대기 중인 완료 변경도 지워져요. 기존 앱의 원본 기록은 유지돼요.").setNegativeButton("닫기",null).setPositiveButton("연결 해제",(dialog,which)->new Thread(()->{try{AccountConnection.clear(this);}catch(Exception ignored){}runOnUiThread(this::showStatus);}).start()).show());
        TextView help=new TextView(this);help.setText("위젯을 4×5 정도로 크게 배치하면 월 달력과 목록을 함께 보기 편해요.\n\n체크 변경은 기기에 먼저 저장하고, 인터넷이 연결되면 원본에 반영해요. 달력은 약 1시간마다 동기화하며 Android의 절전 상태에 따라 지연될 수 있어요. 바로 가져오려면 위젯의 ↻를 누르세요.\n\n별도 유료 서버 없이 기존 Firebase에 연결합니다. 홈 화면 위젯에는 일정 제목이 표시됩니다.\n\nv1.3.1 · Android 8 이상");help.setTextSize(13);help.setPadding(0,dp(24),0,0);content.addView(help);showStatus();}
    private void themePicker(LinearLayout root){
        TextView title=new TextView(this);title.setText("위젯 디자인");title.setTextSize(19);title.setPadding(0,dp(24),0,dp(6));root.addView(title);
        TextView hint=new TextView(this);hint.setText("모든 홈 화면 위젯에 바로 적용돼요.");hint.setTextSize(13);root.addView(hint);
        RadioGroup group=new RadioGroup(this);String[] labels={"반투명 · 배경화면이 보이게","레몬 크림 · 포근하고 깔끔하게","흑백 · 최대한 미니멀하게"};WidgetTheme[] themes={WidgetTheme.GLASS,WidgetTheme.LEMON,WidgetTheme.MONO};
        for(int i=0;i<themes.length;i++){RadioButton radio=new RadioButton(this);radio.setId(View.generateViewId());radio.setText(labels[i]);radio.setTextSize(15);radio.setPadding(0,dp(6),0,dp(6));radio.setTag(themes[i]);group.addView(radio);if(themes[i]==WidgetTheme.current(this))radio.setChecked(true);}
        group.setOnCheckedChangeListener((g,id)->{WidgetTheme theme=(WidgetTheme)g.findViewById(id).getTag();if(DataStore.prefs(this).edit().putString("theme",theme.key).commit())CalendarWidget.updateAll(this);else Toast.makeText(this,"디자인을 저장하지 못했어요. 다시 선택해 주세요.",Toast.LENGTH_SHORT).show();});root.addView(group);
    }
    private void reminderPicker(LinearLayout root,ScrollView scroll){
        TextView title=new TextView(this);title.setText("일정 알림 🍋");title.setTextSize(20);title.setPadding(0,dp(24),0,dp(8));root.addView(title);
        reminderStatus=new TextView(this);reminderStatus.setTextSize(14);root.addView(reminderStatus);
        Switch enabled=new Switch(this);enabled.setText("이 휴대폰에서 일정 알림 받기");enabled.setTextSize(15);enabled.setMinHeight(dp(52));enabled.setChecked(ReminderScheduler.enabled(this));root.addView(enabled);
        enabled.setOnCheckedChangeListener((b,value)->{ReminderScheduler.setEnabled(this,value);if(value&&android.os.Build.VERSION.SDK_INT>=33&&checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{android.Manifest.permission.POST_NOTIFICATIONS},61);showReminders();if(value)SyncJob.scheduleNow(this,true);});
        TextView label=new TextView(this);label.setText("시간 있는 일정의 기본 알림");label.setPadding(0,dp(10),0,dp(6));root.addView(label);
        Spinner lead=new Spinner(this);String[] values={"15","30","60","0","morning"};String[] labels={"15분 전","30분 전","1시간 전","시작할 때","당일 오전 9시"};lead.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));String current=ReminderScheduler.prefs(this).getString("lead","15");for(int i=0;i<values.length;i++)if(values[i].equals(current))lead.setSelection(i);root.addView(lead,new LinearLayout.LayoutParams(-1,dp(48)));
        lead.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onNothingSelected(android.widget.AdapterView<?> parent){}public void onItemSelected(android.widget.AdapterView<?> parent,View view,int pos,long id){ReminderScheduler.prefs(MainActivity.this).edit().putString("lead",values[pos]).commit();ReminderScheduler.reschedule(MainActivity.this);showReminders();}});
        button(root,"알림 팝업 · 소리 설정",()->startActivity(new Intent(android.provider.Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS).putExtra(android.provider.Settings.EXTRA_APP_PACKAGE,getPackageName()).putExtra(android.provider.Settings.EXTRA_CHANNEL_ID,ReminderScheduler.channelId(this))));
        button(root,"테스트 알림 보내기",()->{if(ReminderScheduler.allowed(this))ReminderScheduler.test(this);else Toast.makeText(this,"먼저 Android 알림 권한을 허용해 주세요.",Toast.LENGTH_SHORT).show();});
        if(android.os.Build.VERSION.SDK_INT>=31)button(root,"정확한 시간의 알림 허용",()->{if(!ReminderScheduler.exact(this))startActivity(new Intent(android.provider.Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,Uri.parse("package:"+getPackageName())));else Toast.makeText(this,"이미 허용되어 있어요.",Toast.LENGTH_SHORT).show();});
        TextView help=new TextView(this);help.setText("시간 없는 일정은 당일 오전 9시, 여러 날 일정은 시작일에 한 번 알려줘요. 일정 상세에서 개별 알림을 바꾸거나 끌 수 있어요.\n\n휴대폰에 가져온 일정은 앱을 닫아도 알려줘요. PC에서 바꾼 일정은 휴대폰에 동기화되어야 반영돼요. 자동 동기화는 약 1시간마다이며, 휴대폰 앱을 열면 바로 반영돼요.");help.setTextSize(13);help.setPadding(0,dp(12),0,dp(12));root.addView(help);
        ReminderScheduler.channel(this);showReminders();if(getIntent().getBooleanExtra("reminders",false))title.post(()->scroll.smoothScrollTo(0,title.getTop()));
    }
    private void showReminders(){if(reminderStatus==null)return;reminderStatus.setText(!ReminderScheduler.enabled(this)?"알림이 꺼져 있어요.":!ReminderScheduler.allowed(this)?"Android 알림 권한이 꺼져 있어요. 아래 설정에서 허용해 주세요.":!ReminderScheduler.popupAllowed(this)?"알림 사용 중 · 아래 팝업 설정에서 ‘화면에 팝업 표시’를 켜 주세요.":ReminderScheduler.exact(this)?"알림 사용 중 · 상단 팝업 · 정확한 알림 허용됨.":"알림 사용 중 · 정확한 알림을 허용하면 절전 중 지연을 줄일 수 있어요.");}
    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] results){super.onRequestPermissionsResult(code,permissions,results);if(code==61){showReminders();ReminderScheduler.reschedule(this);}}
    private void button(LinearLayout root,String text,Runnable action){Button b=new Button(this);b.setText(text);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.topMargin=dp(12);root.addView(b,p);b.setOnClickListener(v->action.run());}
    private void showStatus(){try{JSONObject account=SecureStore.get(this,"account"),data=DataStore.data(this);status.setText(account==null?"아직 연결하지 않았어요.":"연결됨 · "+account.optString("name","내 계정")+"\n일정·할 일 "+DataStore.tasks(data).length()+"개 · 전송 대기 "+DataStore.pending(data).length()+"개"+(data.optString("error").isEmpty()?"":"\n"+data.optString("error")));}catch(Exception e){status.setText("연결 정보를 읽지 못했어요. 다시 연결해 주세요.");}}
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);if(intent.getData()!=null)connect(intent.getData());}
    private void connect(Uri uri){status.setText("계정을 확인하고 달력을 가져오는 중…");new Thread(()->{try {
        JSONObject account=Pairing.finish(this,uri);synchronized(SyncEngine.LOCK){JSONObject old=SecureStore.get(this,"account");if(old!=null&&!old.optString("uid").equals(account.optString("uid"))&&DataStore.pending(DataStore.data(this)).length()>0)throw new IllegalStateException("전송 대기 중인 변경이 있어요. 먼저 동기화하거나 연결을 해제해 주세요.");Network.refresh(this,account);if(old==null||!old.optString("uid").equals(account.optString("uid"))){ReminderScheduler.clear(this);DataStore.clear(this);}String googleId=account.optString("googleIdToken"),googleAccess=account.optString("googleAccessToken");account.remove("googleIdToken");account.remove("googleAccessToken");SecureStore.put(this,"account",account);if(!googleId.isEmpty()||!googleAccess.isEmpty())SecureStore.put(this,"webCredential",new JSONObject().put("uid",account.getString("uid")).put("idToken",googleId).put("accessToken",googleAccess).put("expires",System.currentTimeMillis()+10*60*1000));}SyncJob.schedule(this);SyncEngine.sync(this,true);runOnUiThread(()->{showStatus();startActivity(new Intent(this,AppActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP));finish();});
    }catch(Exception e){runOnUiThread(()->{showStatus();message(e instanceof Network.Failure||e instanceof IllegalStateException?e.getMessage():"계정을 연결하지 못했어요. 브라우저에서 다시 연결해 주세요.");});}}).start();}
    private void message(String text){if(isFinishing()||isDestroyed())return;new AlertDialog.Builder(this).setMessage(text).setPositiveButton("확인",null).show();}
}

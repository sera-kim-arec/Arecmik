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
    private TextView status;
    @Override public void onCreate(Bundle saved){super.onCreate(saved);draw();Uri uri=getIntent().getData();if(uri!=null&&"arecmik-widget".equals(uri.getScheme()))connect(uri);}
    @Override protected void onResume(){super.onResume();if(status!=null)showStatus();}
    private int dp(int x){return Math.round(x*getResources().getDisplayMetrics().density);}
    private void draw(){ScrollView scroll=new ScrollView(this);LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(24),dp(30),dp(24),dp(30));scroll.addView(content);scroll.setBackgroundColor(0xfff4f3f0);setContentView(scroll);scroll.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(0,insets.getSystemWindowInsetTop(),0,insets.getSystemWindowInsetBottom());return insets;});
        TextView title=new TextView(this);title.setText("Arecmik\n월 달력 위젯");title.setTextSize(30);title.setTextColor(0xff343a34);content.addView(title);TextView intro=new TextView(this);intro.setText("달력에서 날짜를 고르고, 아래 목록에서 일정과 할 일을 완료하세요.\nWORK / LIFE를 따로 볼 수 있어요.");intro.setTextSize(15);intro.setPadding(0,dp(20),0,dp(20));content.addView(intro);status=new TextView(this);status.setTextSize(14);content.addView(status);
        button(content,"1. 브라우저에서 계정 연결",()->{try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(Pairing.start(this))));}catch(Exception e){message("브라우저를 열지 못했어요. 기본 브라우저를 확인해 주세요.");}});
        button(content,"2. 홈 화면에 위젯 추가",()->{AppWidgetManager manager=getSystemService(AppWidgetManager.class);if(manager.isRequestPinAppWidgetSupported())manager.requestPinAppWidget(new ComponentName(this,CalendarWidget.class),null,null);else message("홈 화면의 빈 곳을 길게 누르고 ‘위젯’에서 ‘Arecmik 월 달력’을 추가해 주세요.");});
        button(content,"지금 동기화",()->{status.setText("동기화 중…");new Thread(()->{SyncEngine.sync(this,true);runOnUiThread(this::showStatus);}).start();});
        button(content,"기존 Arecmik 앱 열기",()->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(Pairing.SITE))));
        button(content,"이 휴대폰 연결 해제",()->new AlertDialog.Builder(this).setMessage("이 휴대폰에 보관한 연결 정보와 달력을 지울까요? 전송 대기 중인 완료 변경도 지워져요. 기존 앱의 원본 기록은 유지돼요.").setNegativeButton("닫기",null).setPositiveButton("연결 해제",(dialog,which)->new Thread(()->{synchronized(SyncEngine.LOCK){try{SecureStore.put(this,"account",null);SecureStore.put(this,"pairing",null);DataStore.clear(this);SyncJob.cancel(this);CalendarWidget.updateAll(this);}catch(Exception ignored){}}runOnUiThread(this::showStatus);}).start()).show());
        TextView help=new TextView(this);help.setText("위젯을 4×5 정도로 크게 배치하면 월 달력과 목록을 함께 보기 편해요.\n\n체크 변경은 기기에 먼저 저장하고, 인터넷이 연결되면 원본에 반영해요. 달력은 약 1시간마다 동기화하며 Android의 절전 상태에 따라 지연될 수 있어요. 바로 가져오려면 위젯의 ↻를 누르세요.\n\n별도 유료 서버 없이 기존 Firebase에 연결합니다. 홈 화면 위젯에는 일정 제목이 표시됩니다.\n\nv1.0.0 · Android 8 이상");help.setTextSize(13);help.setPadding(0,dp(24),0,0);content.addView(help);showStatus();}
    private void button(LinearLayout root,String text,Runnable action){Button b=new Button(this);b.setText(text);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.topMargin=dp(12);root.addView(b,p);b.setOnClickListener(v->action.run());}
    private void showStatus(){try{JSONObject account=SecureStore.get(this,"account"),data=DataStore.data(this);status.setText(account==null?"아직 연결하지 않았어요.":"연결됨 · "+account.optString("name","내 계정")+"\n일정·할 일 "+DataStore.tasks(data).length()+"개 · 전송 대기 "+DataStore.pending(data).length()+"개"+(data.optString("error").isEmpty()?"":"\n"+data.optString("error")));}catch(Exception e){status.setText("연결 정보를 읽지 못했어요. 다시 연결해 주세요.");}}
    private void connect(Uri uri){status.setText("계정을 확인하고 달력을 가져오는 중…");new Thread(()->{try {
        JSONObject account=Pairing.finish(this,uri);synchronized(SyncEngine.LOCK){JSONObject old=SecureStore.get(this,"account");if(old!=null&&!old.optString("uid").equals(account.optString("uid"))&&DataStore.pending(DataStore.data(this)).length()>0)throw new IllegalStateException("전송 대기 중인 변경이 있어요. 먼저 동기화하거나 연결을 해제해 주세요.");Network.refresh(this,account);if(old==null||!old.optString("uid").equals(account.optString("uid")))DataStore.clear(this);SecureStore.put(this,"account",account);}SyncJob.schedule(this);SyncEngine.sync(this,true);runOnUiThread(()->{showStatus();message("계정을 연결했어요. 홈 화면에 위젯을 추가해 주세요.");});
    }catch(Exception e){runOnUiThread(()->{showStatus();message(e instanceof Network.Failure||e instanceof IllegalStateException?e.getMessage():"계정을 연결하지 못했어요. 브라우저에서 다시 연결해 주세요.");});}}).start();}
    private void message(String text){if(isFinishing()||isDestroyed())return;new AlertDialog.Builder(this).setMessage(text).setPositiveButton("확인",null).show();}
}

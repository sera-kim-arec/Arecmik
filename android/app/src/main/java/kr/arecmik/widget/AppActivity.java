package kr.arecmik.widget;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** Existing web app in its own app window; Google OAuth always uses the browser. */
public final class AppActivity extends Activity {
    static final Uri ORIGIN=Uri.parse("https://sera-kim-arec.github.io");
    WebView web;WebMessagePort port;boolean ready;TextView error;ProgressBar loading;int pageGeneration;
    private ValueCallback<Uri[]> fileCallback;
    private JSONObject reminderToOpen;
    private final java.util.concurrent.ExecutorService reminderQueue=java.util.concurrent.Executors.newSingleThreadExecutor();
    private static final int PHOTOS=41,BACKUP=42;
    static boolean trusted(String value){
        if(value==null)return false;Uri u=Uri.parse(value);String path=u.getPath();
        return "https".equals(u.getScheme())&&"sera-kim-arec.github.io".equals(u.getHost())&&u.getUserInfo()==null&&u.getPort()==-1&&("/Arecmik/".equals(path)||"/Arecmik/index.html".equals(path));
    }
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    @Override public void onCreate(Bundle saved){super.onCreate(saved);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(0xfff4f3f0);
        loading=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);root.addView(loading,new LinearLayout.LayoutParams(-1,dp(3)));
        error=new TextView(this);error.setTextSize(15);error.setPadding(dp(16),dp(16),dp(16),dp(16));error.setVisibility(View.GONE);error.setOnClickListener(v->web.loadUrl(Pairing.SITE));root.addView(error);
        web=new WebView(this);root.addView(web,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(0,insets.getSystemWindowInsetTop(),0,insets.getSystemWindowInsetBottom());return insets;});
        WebSettings options=web.getSettings();options.setJavaScriptEnabled(true);options.setDomStorageEnabled(true);options.setAllowFileAccess(false);options.setAllowContentAccess(false);options.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);options.setSupportMultipleWindows(true);options.setUserAgentString(options.getUserAgentString()+" ArecmikAndroid/1");
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){if(!request.isForMainFrame())return !"https".equals(request.getUrl().getScheme());if(trusted(request.getUrl().toString()))return false;external(request.getUrl());return true;}
            @Override public void onPageStarted(WebView view,String url,android.graphics.Bitmap icon){closePort();error.setVisibility(View.GONE);}
            @Override public void onPageFinished(WebView view,String url){if(trusted(url))offerChannel(pageGeneration,0);}
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError problem){if(request.isForMainFrame())loadError();}
            @Override public void onReceivedHttpError(WebView view,WebResourceRequest request,WebResourceResponse response){if(request.isForMainFrame()&&response.getStatusCode()>=400)loadError();}
        });
        web.setWebChromeClient(new WebChromeClient(){
            @Override public void onProgressChanged(WebView view,int progress){loading.setProgress(progress);loading.setVisibility(progress==100?View.GONE:View.VISIBLE);}
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params){if(!trusted(view.getUrl()))return false;if(fileCallback!=null)fileCallback.onReceiveValue(null);fileCallback=callback;boolean json=false;for(String accept:params.getAcceptTypes())if("application/json".equals(accept)||".json".equals(accept))json=true;Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(json?"application/json":"image/*").putExtra(Intent.EXTRA_ALLOW_MULTIPLE,!json&&params.getMode()==FileChooserParams.MODE_OPEN_MULTIPLE);try{startActivityForResult(pick,PHOTOS);}catch(ActivityNotFoundException e){fileCallback.onReceiveValue(null);fileCallback=null;}return true;}
            @Override public boolean onJsAlert(WebView v,String url,String text,JsResult result){if(!trusted(url))return false;new AlertDialog.Builder(AppActivity.this).setMessage(text).setPositiveButton("확인",(d,w)->result.confirm()).setOnCancelListener(d->result.cancel()).show();return true;}
            @Override public boolean onJsConfirm(WebView v,String url,String text,JsResult result){if(!trusted(url))return false;new AlertDialog.Builder(AppActivity.this).setMessage(text).setPositiveButton("확인",(d,w)->result.confirm()).setNegativeButton("취소",(d,w)->result.cancel()).setOnCancelListener(d->result.cancel()).show();return true;}
            @Override public boolean onCreateWindow(WebView view,boolean dialog,boolean gesture,android.os.Message result){if(!gesture)return false;WebView popup=new WebView(AppActivity.this);popup.setWebViewClient(new WebViewClient(){@Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest request){external(request.getUrl());v.destroy();return true;}});((WebView.WebViewTransport)result.obj).setWebView(popup);result.sendToTarget();return true;}
        });
        web.setDownloadListener((url,agent,disposition,mime,length)->external(Uri.parse(url)));
        // A new WebView reloads the online page while Firebase keeps its own local persistence.
        if(saved==null)new File(getCacheDir(),"backup.pending").delete();
        readReminder(getIntent());web.loadUrl(Pairing.SITE);
    }
    private void external(Uri uri){String scheme=uri.getScheme();if(!"https".equals(scheme)&&!"http".equals(scheme)&&!"mailto".equals(scheme)&&!"tel".equals(scheme)&&!"geo".equals(scheme))return;try{startActivity(new Intent(Intent.ACTION_VIEW,uri));}catch(ActivityNotFoundException e){Toast.makeText(this,"이 링크를 열 앱이 없어요.",Toast.LENGTH_SHORT).show();}}
    private void loadError(){error.setText("화면을 불러오지 못했어요. 인터넷 연결을 확인한 뒤 여기를 눌러 다시 열어 주세요. 위젯에 저장된 달력은 계속 볼 수 있어요.");error.setVisibility(View.VISIBLE);}
    void receive(String raw){if(!trusted(web.getUrl())||raw==null)return;try{JSONObject message=new JSONObject(raw);switch(message.optString("type")){
        case "ready":ready=true;deliverAccount();break;
        case "login":startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(Pairing.start(this,true))));break;
        case "settings":startActivity(new Intent(this,MainActivity.class));break;
        case "reminders-settings":startActivity(new Intent(this,MainActivity.class).putExtra("reminders",true));break;
        case "reminders-notices":{JSONObject account=SecureStore.get(this,"account");if(account!=null)send(new JSONObject().put("type","reminder-notices").put("uid",account.getString("uid")).put("enabled",ReminderScheduler.enabled(this)&&ReminderScheduler.allowed(this)).put("lead",ReminderScheduler.prefs(this).getString("lead","15")).put("notices",ReminderScheduler.notices(this)));break;}
        case "reminders-dismiss":{String id=message.optString("id");if(id.matches("[A-Za-z0-9_-]{1,128}"))getSystemService(NotificationManager.class).cancel(ReminderScheduler.TAG+":"+id,0);break;}
        case "reminders-sync":{JSONArray tasks=message.optJSONArray("tasks");String uid=message.optString("uid");long receivedAt=System.currentTimeMillis();if(tasks!=null)reminderQueue.execute(()->{try{ReminderScheduler.fromWeb(this,uid,tasks,receivedAt);}catch(Exception ignored){}});break;}
        case "update":startActivity(new Intent(this,UpdateActivity.class));break;
        case "back-unhandled":moveTaskToBack(true);break;
        case "auth-ok": {JSONObject credential=SecureStore.get(this,"webCredential");if(credential!=null&&credential.optString("uid").equals(message.optString("uid")))SecureStore.put(this,"webCredential",null);break;}
        case "logout":new Thread(()->{try{AccountConnection.clear(this);runOnUiThread(()->{try{send(new JSONObject().put("type","signed-out"));}catch(JSONException ignored){}});}catch(Exception e){runOnUiThread(()->Toast.makeText(this,"연결을 해제하지 못했어요. 다시 시도해 주세요.",Toast.LENGTH_LONG).show());}}).start();break;
        case "backup":saveBackup(message);break;
        default:break;
    }}catch(Exception e){Toast.makeText(this,"작업을 마치지 못했어요. 다시 시도해 주세요.",Toast.LENGTH_LONG).show();}}
    private void saveBackup(JSONObject message)throws Exception {if(!message.optString("name").matches("Arecmik-백업-\\d{4}-\\d{2}-\\d{2}\\.json"))return;File pending=new File(getCacheDir(),"backup.pending");if(pending.exists()){Toast.makeText(this,"이미 백업 저장을 진행 중이에요.",Toast.LENGTH_SHORT).show();return;}JSONObject content=new JSONObject(message.getString("content"));if(!content.optBoolean("complete")||!"Arecmik".equals(content.optString("app")))return;try(FileOutputStream out=new FileOutputStream(pending)){out.write(message.getString("content").getBytes(StandardCharsets.UTF_8));}try{startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/json").putExtra(Intent.EXTRA_TITLE,message.getString("name")),BACKUP);}catch(Exception e){pending.delete();throw e;}}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==PHOTOS&&fileCallback!=null){Uri[] values=null;if(result==RESULT_OK&&data!=null){if(data.getClipData()!=null){values=new Uri[data.getClipData().getItemCount()];for(int i=0;i<values.length;i++)values[i]=data.getClipData().getItemAt(i).getUri();}else if(data.getData()!=null)values=new Uri[]{data.getData()};}fileCallback.onReceiveValue(values);fileCallback=null;}
        if(request==BACKUP){File pending=new File(getCacheDir(),"backup.pending");boolean ok=false;try{if(result==RESULT_OK&&data!=null&&data.getData()!=null){try(InputStream in=new FileInputStream(pending);OutputStream out=getContentResolver().openOutputStream(data.getData())){if(out==null)throw new IOException();byte[] bytes=new byte[16384];int count;while((count=in.read(bytes))!=-1)out.write(bytes,0,count);ok=true;}}}catch(Exception ignored){}finally{pending.delete();}try{send(new JSONObject().put("type","backup-result").put("ok",ok));}catch(JSONException ignored){}}
    }
    void deliverAccount(){if(!ready||!trusted(web.getUrl()))return;try{JSONObject account=SecureStore.get(this,"account");send(new JSONObject().put("type","account").put("uid",account==null?"":account.optString("uid")).put("capabilities",new JSONArray().put("update").put("reminders").put("reminder-popups")));if(reminderToOpen!=null&&account!=null&&account.optString("uid").equals(reminderToOpen.optString("uid"))){send(reminderToOpen);reminderToOpen=null;}JSONObject credential=SecureStore.get(this,"webCredential");if(credential!=null){if(credential.optLong("expires")<=System.currentTimeMillis()){SecureStore.put(this,"webCredential",null);return;}if(account!=null&&account.optString("uid").equals(credential.optString("uid")))send(new JSONObject(credential.toString()).put("type","credential"));}}catch(Exception ignored){}}
    private void readReminder(Intent intent){try{JSONObject account=SecureStore.get(this,"account");String id=intent.getStringExtra("task"),uid=intent.getStringExtra("uid");if("kr.arecmik.OPEN_REMINDER".equals(intent.getAction())&&account!=null&&account.optString("uid").equals(uid)&&id!=null&&id.matches("[A-Za-z0-9_-]{1,128}"))reminderToOpen=new JSONObject().put("type","open-task").put("uid",uid).put("id",id);}catch(Exception ignored){}}
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);readReminder(intent);deliverAccount();}
    void send(JSONObject message){if(port!=null&&trusted(web.getUrl()))try{port.postMessage(new WebMessage(message.toString()));}catch(IllegalStateException ignored){}}
    private void offerChannel(int generation,int attempt){if(generation!=pageGeneration||ready||attempt>=20||!trusted(web.getUrl())||isDestroyed())return;if(port!=null)port.close();WebMessagePort[] channel=web.createWebMessageChannel();port=channel[0];port.setWebMessageCallback(new WebMessagePort.WebMessageCallback(){@Override public void onMessage(WebMessagePort p,WebMessage message){if(p==port)receive(message.getData());}});web.postWebMessage(new WebMessage("arecmik-native-v1",new WebMessagePort[]{channel[1]}),ORIGIN);web.postDelayed(()->offerChannel(generation,attempt+1),1000);}
    private void closePort(){pageGeneration++;ready=false;if(port!=null){port.close();port=null;}}
    @Override protected void onResume(){super.onResume();if(web!=null){web.onResume();deliverAccount();}}
    @Override protected void onPause(){if(web!=null)web.onPause();super.onPause();}
    @Override public void onBackPressed(){if(ready)try{send(new JSONObject().put("type","back"));}catch(JSONException ignored){}else if(web.canGoBack())web.goBack();else moveTaskToBack(true);}
    @Override protected void onDestroy(){closePort();if(fileCallback!=null)fileCallback.onReceiveValue(null);web.destroy();reminderQueue.shutdown();super.onDestroy();}
}

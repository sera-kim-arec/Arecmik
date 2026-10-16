package kr.arecmik.widget;

import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.net.ssl.HttpsURLConnection;

/** Downloads only the owner's HTTPS release and hands a verified update to Android. */
public final class UpdateActivity extends Activity {
    private static final AtomicBoolean RUNNING=new AtomicBoolean();
    private static final int INSTALL_PERMISSION=51;
    private TextView status;private Button install;private File candidate;
    @Override public void onCreate(Bundle saved){super.onCreate(saved);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);int pad=Math.round(24*getResources().getDisplayMetrics().density);root.setPadding(pad,pad,pad,pad);root.setBackgroundColor(0xfff4f3f0);
        TextView title=new TextView(this);title.setText("Arecmik 업데이트");title.setTextSize(25);root.addView(title);
        status=new TextView(this);status.setTextSize(16);status.setPadding(0,pad,0,pad);status.setText("새 버전을 확인하고 있어요…");root.addView(status);
        install=new Button(this);install.setText("설치 계속하기");install.setVisibility(View.GONE);install.setOnClickListener(v->install());root.addView(install);
        Button close=new Button(this);close.setText("닫기");close.setOnClickListener(v->finish());root.addView(close);setContentView(root);
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(pad,pad+insets.getSystemWindowInsetTop(),pad,pad+insets.getSystemWindowInsetBottom());return insets;});
        if(!RUNNING.compareAndSet(false,true)){status.setText("이미 업데이트를 확인하고 있어요. 잠시 후 다시 열어 주세요.");return;}
        new Thread(()->{try{check();}catch(Exception e){show("업데이트를 받지 못했어요. 인터넷 연결을 확인하고 다시 눌러 주세요. 기존 앱은 계속 사용할 수 있어요.");}finally{RUNNING.set(false);}}).start();
    }
    static JSONObject release(String raw)throws Exception {
        JSONObject value=new JSONObject(raw);String name=value.optString("versionName"),digest=value.optString("sha256");long code=value.optLong("versionCode",-1);
        if(code<1||code>Integer.MAX_VALUE||!name.matches("\\d+\\.\\d+\\.\\d+")||!digest.matches("[a-f0-9]{64}")||!value.optString("url").equals(Pairing.SITE+"downloads/Arecmik-"+name+".apk"))throw new IOException("Invalid release");
        return value;
    }
    private static HttpsURLConnection connection(String url)throws Exception {
        URL address=new URL(url);if(!"https".equals(address.getProtocol())||!"sera-kim-arec.github.io".equals(address.getHost())||address.getPort()!=-1)throw new IOException();
        HttpsURLConnection c=(HttpsURLConnection)address.openConnection();c.setInstanceFollowRedirects(false);c.setUseCaches(false);c.setConnectTimeout(10000);c.setReadTimeout(30000);c.setRequestProperty("Cache-Control","no-cache");if(c.getResponseCode()!=200){c.disconnect();throw new IOException();}return c;
    }
    private static long version(PackageInfo info){return Build.VERSION.SDK_INT>=28?info.getLongVersionCode():info.versionCode;}
    private static Set<String> signers(PackageInfo info)throws Exception {
        Signature[] signatures=Build.VERSION.SDK_INT>=28?(info.signingInfo==null?null:info.signingInfo.getApkContentsSigners()):info.signatures;
        if(signatures==null||signatures.length==0)throw new IOException("Unsigned package");Set<String> result=new HashSet<>();for(Signature signature:signatures)result.add(Base64.getEncoder().encodeToString(MessageDigest.getInstance("SHA-256").digest(signature.toByteArray())));return result;
    }
    static boolean validPackage(PackageInfo current,PackageInfo update,long expected)throws Exception {return update!=null&&current.packageName.equals(update.packageName)&&version(update)==expected&&version(update)>version(current)&&signers(current).equals(signers(update));}
    private void check()throws Exception {
        JSONObject release;HttpsURLConnection meta=connection(Pairing.SITE+"android-release.json?t="+System.currentTimeMillis());
        try(InputStream in=meta.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] bytes=new byte[2048];int n,total=0;while((n=in.read(bytes))!=-1){total+=n;if(total>8192)throw new IOException();out.write(bytes,0,n);}release=release(out.toString("UTF-8"));}finally{meta.disconnect();}
        int flags=Build.VERSION.SDK_INT>=28?PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES;PackageInfo current=getPackageManager().getPackageInfo(getPackageName(),flags);long code=release.getLong("versionCode");
        if(code<=version(current)){show("이미 최신 버전이에요. · v"+current.versionName);return;}
        show("v"+release.getString("versionName")+" 설치 파일을 받고 있어요…");File directory=new File(getCacheDir(),"updates");if(!directory.exists()&&!directory.mkdirs())throw new IOException();
        File temp=File.createTempFile("download-",".apk",directory);HttpsURLConnection download=null;
        try{download=connection(release.getString("url"));MessageDigest digest=MessageDigest.getInstance("SHA-256");
            try(InputStream in=download.getInputStream();OutputStream out=new FileOutputStream(temp)){byte[] bytes=new byte[16384];int n;long total=0;while((n=in.read(bytes))!=-1){total+=n;if(total>64*1024*1024)throw new IOException();digest.update(bytes,0,n);out.write(bytes,0,n);}}
            StringBuilder hex=new StringBuilder();for(byte b:digest.digest())hex.append(String.format(Locale.ROOT,"%02x",b&255));if(!release.getString("sha256").equals(hex.toString()))throw new IOException("Checksum mismatch");
            PackageInfo update=getPackageManager().getPackageArchiveInfo(temp.getAbsolutePath(),flags);if(!validPackage(current,update,code))throw new IOException("Package mismatch");
            File ready=new File(directory,"Arecmik-"+code+".apk");if(ready.exists()&&!ready.delete())throw new IOException();if(!temp.renameTo(ready))throw new IOException();candidate=ready;
            runOnUiThread(()->{if(!isFinishing()&&!isDestroyed()){status.setText("파일 확인을 마쳤어요. Android 설치 화면에서 ‘설치’를 눌러 주세요.");install.setVisibility(View.VISIBLE);install();}});
        }finally{temp.delete();if(download!=null)download.disconnect();}
    }
    private void show(String text){runOnUiThread(()->{if(!isFinishing()&&!isDestroyed())status.setText(text);});}
    private void install(){if(candidate==null||!candidate.isFile())return;
        if(!getPackageManager().canRequestPackageInstalls()){status.setText("처음 한 번만 ‘이 출처의 앱 설치’를 허용해 주세요. 돌아오면 설치를 계속합니다.");try{startActivityForResult(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+getPackageName())),INSTALL_PERMISSION);}catch(ActivityNotFoundException e){status.setText("휴대폰 설정에서 Arecmik의 ‘알 수 없는 앱 설치’를 허용한 뒤 다시 눌러 주세요.");}return;}
        Uri uri=new Uri.Builder().scheme("content").authority(getPackageName()+".apk").appendPath("updates").appendPath(candidate.getName()).build();
        Intent intent=new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);intent.setClipData(ClipData.newRawUri("Arecmik APK",uri));try{startActivity(intent);}catch(ActivityNotFoundException e){status.setText("설치 화면을 열지 못했어요. 휴대폰의 앱 설치 설정을 확인해 주세요.");}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==INSTALL_PERMISSION&&getPackageManager().canRequestPackageInstalls())install();}
}

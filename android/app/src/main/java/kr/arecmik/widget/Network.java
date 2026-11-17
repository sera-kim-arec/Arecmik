package kr.arecmik.widget;

import android.content.Context;
import org.json.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.io.*;

final class Network {
    static final class Failure extends IOException {
        final int status;
        Failure(int status){super(status==401||status==403?"계정을 다시 연결해 주세요":status==429?"동기화 한도에 도달했어요. 잠시 후 다시 시도해 주세요":"연결을 기다리는 중이에요");this.status=status;}
    }
    static JSONObject request(String method,String url,JSONObject json,String token) throws Exception {return requestBody(method,url,json==null?null:json.toString(),"application/json; charset=UTF-8",token);}
    static JSONObject requestBody(String method,String url,String body,String contentType,String token) throws Exception {
        URI uri=URI.create(url);if(!"https".equals(uri.getScheme())||!("firestore.googleapis.com".equals(uri.getHost())||"securetoken.googleapis.com".equals(uri.getHost())))throw new SecurityException("Unexpected API host");
        javax.net.ssl.HttpsURLConnection conn=(javax.net.ssl.HttpsURLConnection)uri.toURL().openConnection();conn.setInstanceFollowRedirects(false);conn.setRequestMethod(method);conn.setConnectTimeout(10000);conn.setReadTimeout(15000);conn.setRequestProperty("Accept","application/json");
        if(token!=null)conn.setRequestProperty("Authorization","Bearer "+token);
        try {if(body!=null){conn.setDoOutput(true);conn.setRequestProperty("Content-Type",contentType);try(OutputStream out=conn.getOutputStream()){out.write(body.getBytes(StandardCharsets.UTF_8));}}
            int status=conn.getResponseCode();if(status<200||status>=300)throw new Failure(status);
            try(InputStream in=conn.getInputStream()){ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1){out.write(b,0,n);if(out.size()>16*1024*1024)throw new IOException("일정이 너무 많아 동기화를 멈췄어요");}String text=out.toString("UTF-8");return text.isEmpty()?new JSONObject():new JSONObject(text);}
        }finally{conn.disconnect();}
    }
    static String refresh(Context c,JSONObject account) throws Exception {
        JSONObject response=requestBody("POST","https://securetoken.googleapis.com/v1/token?key="+BuildConfigData.API_KEY,
                "grant_type=refresh_token&refresh_token="+URLEncoder.encode(account.getString("refreshToken"),"UTF-8"),"application/x-www-form-urlencoded",null);
        if(!account.getString("uid").equals(response.getString("user_id")))throw new SecurityException("Account mismatch");
        account.put("refreshToken",response.getString("refresh_token")).put("idToken",response.getString("id_token")).put("expires",System.currentTimeMillis()+response.getLong("expires_in")*1000);
        return response.getString("id_token");
    }
    static String token(Context c,JSONObject account) throws Exception {
        if(account.optLong("expires")>System.currentTimeMillis()+120000&&!account.optString("idToken").isEmpty())return account.getString("idToken");
        String token=refresh(c,account);SecureStore.put(c,"account",account);return token;
    }
}

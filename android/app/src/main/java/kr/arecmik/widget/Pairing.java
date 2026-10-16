package kr.arecmik.widget;

import android.content.Context;
import android.net.Uri;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.*;
import javax.crypto.*;
import javax.crypto.spec.*;

final class Pairing {
    static final String SITE="https://sera-kim-arec.github.io/Arecmik/";
    static String start(Context c) throws Exception {
        KeyPairGenerator gen=KeyPairGenerator.getInstance("EC");gen.initialize(new ECGenParameterSpec("secp256r1"));KeyPair pair=gen.generateKeyPair();
        byte[] nonce=new byte[24];new SecureRandom().nextBytes(nonce);long expires=System.currentTimeMillis()+10*60*1000;
        JSONObject request=new JSONObject().put("v",1).put("nonce",SecureStore.b64(nonce)).put("expires",expires).put("publicKey",SecureStore.b64(pair.getPublic().getEncoded()));
        SecureStore.put(c,"pairing",new JSONObject(request.toString()).put("privateKey",SecureStore.b64(pair.getPrivate().getEncoded())));
        return SITE+"widget-connect.html#pair="+SecureStore.b64(request.toString().getBytes(StandardCharsets.UTF_8));
    }
    static JSONObject finish(Context c,Uri uri) throws Exception {
        if(!"arecmik-widget".equals(uri.getScheme())||!"connect".equals(uri.getHost()))throw new Exception("올바른 연결 주소가 아니에요");
        String fragment=uri.getFragment();if(fragment==null||!fragment.startsWith("data=")||fragment.length()>24000)throw new Exception("연결 정보를 확인할 수 없어요");
        JSONObject pending=SecureStore.get(c,"pairing");if(pending==null||pending.optLong("expires")<System.currentTimeMillis())throw new Exception("연결 시간이 지났어요. 다시 연결해 주세요");
        JSONObject e=new JSONObject(new String(SecureStore.unb64(fragment.substring(5)),StandardCharsets.UTF_8));
        if(e.optInt("v")!=1||!pending.getString("nonce").equals(e.optString("nonce")))throw new Exception("이 휴대폰에서 시작한 연결이 아니에요");
        byte[] clear=PairCrypto.decrypt(SecureStore.unb64(pending.getString("privateKey")),SecureStore.unb64(e.getString("publicKey")),SecureStore.unb64(e.getString("iv")),SecureStore.unb64(e.getString("data")),pending.getString("nonce"));
        JSONObject account=new JSONObject(new String(clear,StandardCharsets.UTF_8));
        if(!BuildConfigData.PROJECT.equals(account.optString("projectId"))||!account.optString("uid").matches("[A-Za-z0-9_-]{1,128}")||account.optString("refreshToken").length()<40)throw new Exception("계정 연결 정보를 확인해 주세요");
        // Consume the one-time key before any network operation; captured callbacks cannot be replayed.
        SecureStore.put(c,"pairing",null);return account;
    }
}

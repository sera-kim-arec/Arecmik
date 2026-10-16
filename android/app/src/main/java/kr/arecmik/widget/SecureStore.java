package kr.arecmik.widget;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Account credentials and pending pairing keys never leave private encrypted storage. */
final class SecureStore {
    private static SecretKey key() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        String alias="arecmik.widget.private.v1";
        if(!store.containsAlias(alias)) {
            KeyGenerator gen=KeyGenerator.getInstance("AES","AndroidKeyStore");
            gen.init(new KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
            gen.generateKey();
        }
        return (SecretKey)store.getKey(alias,null);
    }
    static synchronized JSONObject get(Context c,String name) throws Exception {
        String raw=c.getSharedPreferences("private",0).getString(name,null);if(raw==null)return null;
        JSONObject envelope=new JSONObject(raw);Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,unb64(envelope.getString("iv"))));
        cipher.updateAAD(name.getBytes(StandardCharsets.UTF_8));
        return new JSONObject(new String(cipher.doFinal(unb64(envelope.getString("data"))),StandardCharsets.UTF_8));
    }
    static synchronized void put(Context c,String name,JSONObject data) throws Exception {
        if(data==null){c.getSharedPreferences("private",0).edit().remove(name).commit();return;}
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());cipher.updateAAD(name.getBytes(StandardCharsets.UTF_8));
        JSONObject envelope=new JSONObject().put("iv",b64(cipher.getIV())).put("data",b64(cipher.doFinal(data.toString().getBytes(StandardCharsets.UTF_8))));
        if(!c.getSharedPreferences("private",0).edit().putString(name,envelope.toString()).commit())throw new Exception("기기에 연결 정보를 저장하지 못했어요");
    }
    static String b64(byte[] b){return Base64.encodeToString(b,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);}
    static byte[] unb64(String s){return Base64.decode(s,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);}
}

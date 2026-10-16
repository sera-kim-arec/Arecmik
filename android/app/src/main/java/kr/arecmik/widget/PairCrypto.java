package kr.arecmik.widget;
import java.security.*;
import java.security.spec.*;
import java.nio.charset.StandardCharsets;
import javax.crypto.*;
import javax.crypto.spec.*;

/** The same ECDH + SHA-256 + AES-GCM protocol as widget-pairing.js. */
final class PairCrypto {
    static byte[] decrypt(byte[] privateDer,byte[] publicDer,byte[] iv,byte[] data,String nonce)throws Exception {
        KeyFactory factory=KeyFactory.getInstance("EC");PrivateKey privateKey=factory.generatePrivate(new PKCS8EncodedKeySpec(privateDer));PublicKey publicKey=factory.generatePublic(new X509EncodedKeySpec(publicDer));
        if(!(((java.security.interfaces.ECPublicKey)publicKey).getParams().getCurve().getField().getFieldSize()==256))throw new SecurityException("Unexpected curve");
        KeyAgreement agreement=KeyAgreement.getInstance("ECDH");agreement.init(privateKey);agreement.doPhase(publicKey,true);byte[] aad=("arecmik-widget:v1:"+nonce).getBytes(StandardCharsets.UTF_8);
        MessageDigest sha=MessageDigest.getInstance("SHA-256");sha.update(agreement.generateSecret());byte[] key=sha.digest(aad);
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,iv));cipher.updateAAD(aad);return cipher.doFinal(data);
    }
}

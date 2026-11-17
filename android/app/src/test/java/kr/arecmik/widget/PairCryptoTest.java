package kr.arecmik.widget;
import org.junit.Test;
import java.security.*;
import java.security.spec.ECGenParameterSpec;
import java.nio.charset.StandardCharsets;
import javax.crypto.*;
import javax.crypto.spec.*;
import static org.junit.Assert.*;

public class PairCryptoTest {
    @Test public void onlyRecipientCanDecryptAndTamperingFails()throws Exception{
        KeyPairGenerator gen=KeyPairGenerator.getInstance("EC");gen.initialize(new ECGenParameterSpec("secp256r1"));KeyPair recipient=gen.generateKeyPair(),sender=gen.generateKeyPair();String nonce="test-session";
        KeyAgreement agreement=KeyAgreement.getInstance("ECDH");agreement.init(sender.getPrivate());agreement.doPhase(recipient.getPublic(),true);byte[] aad=("arecmik-widget:v1:"+nonce).getBytes(StandardCharsets.UTF_8);MessageDigest sha=MessageDigest.getInstance("SHA-256");sha.update(agreement.generateSecret());byte[] key=sha.digest(aad),iv=new byte[12];new SecureRandom().nextBytes(iv);Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,iv));cipher.updateAAD(aad);byte[] data=cipher.doFinal("test account".getBytes(StandardCharsets.UTF_8));
        assertEquals("test account",new String(PairCrypto.decrypt(recipient.getPrivate().getEncoded(),sender.getPublic().getEncoded(),iv,data,nonce),StandardCharsets.UTF_8));
        try{PairCrypto.decrypt(recipient.getPrivate().getEncoded(),sender.getPublic().getEncoded(),iv,data,"wrong-session");fail("Wrong session must fail");}catch(AEADBadTagException expected){}
        data[0]^=1;try{PairCrypto.decrypt(recipient.getPrivate().getEncoded(),sender.getPublic().getEncoded(),iv,data,nonce);fail("Tampering must fail");}catch(AEADBadTagException expected){}
    }
}

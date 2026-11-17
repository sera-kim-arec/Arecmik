package kr.arecmik.widget;

import android.content.pm.*;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;
import static org.robolectric.Shadows.shadowOf;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35)
public class UpdateSafetyTest {
    private JSONObject metadata()throws Exception{return new JSONObject().put("versionCode",4).put("versionName","1.2.0").put("sha256","ab".repeat(32)).put("url",Pairing.SITE+"downloads/Arecmik-1.2.0.apk");}
    @Test public void onlyOwnVersionedHttpsReleaseAndSha256AreAccepted()throws Exception{
        assertEquals(4,UpdateActivity.release(metadata().toString()).getInt("versionCode"));
        for(JSONObject bad:new JSONObject[]{metadata().put("url","https://evil.test/Arecmik-1.2.0.apk"),metadata().put("url",Pairing.SITE+"../Other/app.apk"),metadata().put("sha256","bad"),metadata().put("versionCode",-1),metadata().put("versionName","../../evil")})assertThrows(Exception.class,()->UpdateActivity.release(bad.toString()));
    }
    private PackageInfo apk(int code,String signer){PackageInfo p=new PackageInfo();p.packageName="kr.arecmik.widget";p.setLongVersionCode(code);p.signingInfo=new SigningInfo();shadowOf(p.signingInfo).setSignatures(new Signature[]{new Signature(signer.getBytes(java.nio.charset.StandardCharsets.UTF_8))});return p;}
    @Test public void updateMustMatchInstalledSignaturePackageAndExpectedHigherVersion()throws Exception{
        PackageInfo current=apk(3,"owner"),next=apk(4,"owner");assertTrue(UpdateActivity.validPackage(current,next,4));
        assertFalse(UpdateActivity.validPackage(current,apk(4,"other"),4));assertFalse(UpdateActivity.validPackage(current,apk(2,"owner"),2));assertFalse(UpdateActivity.validPackage(current,next,5));assertFalse(UpdateActivity.validPackage(current,null,4));next.packageName="another.app";assertFalse(UpdateActivity.validPackage(current,next,4));
    }
}

package kr.arecmik.widget;

import android.content.Intent;
import android.webkit.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;
import static org.robolectric.Shadows.shadowOf;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35)
public class AppActivityTest {
    @Test public void onlyExactAppPagesCanReceiveNativeCredentials(){
        assertTrue(AppActivity.trusted(Pairing.SITE));assertTrue(AppActivity.trusted(Pairing.SITE+"index.html?v=1"));
        for(String url:new String[]{"http://sera-kim-arec.github.io/Arecmik/","https://sera-kim-arec.github.io.evil.test/Arecmik/","https://sera-kim-arec.github.io:8443/Arecmik/","https://evil@sera-kim-arec.github.io/Arecmik/",Pairing.SITE+"widget-connect.html","file:///Arecmik/","https://sera-kim-arec.github.io/Other/"})assertFalse(url,AppActivity.trusted(url));
    }
    @Test public void launcherLoadsOriginalAppWithRestrictedWebView(){
        var controller=Robolectric.buildActivity(AppActivity.class).create().start().resume();AppActivity app=controller.get();
        assertEquals(Pairing.SITE,shadowOf(app.web).getLastLoadedUrl());assertTrue(app.web.getSettings().getJavaScriptEnabled());assertTrue(app.web.getSettings().getDomStorageEnabled());assertFalse(app.web.getSettings().getAllowFileAccess());assertFalse(app.web.getSettings().getAllowContentAccess());assertEquals(WebSettings.MIXED_CONTENT_NEVER_ALLOW,app.web.getSettings().getMixedContentMode());assertTrue(app.web.getSettings().getUserAgentString().contains("ArecmikAndroid/1"));
        controller.pause().stop().destroy();
    }
    @Test public void settingsCommandOpensNativeWidgetSettings(){
        var controller=Robolectric.buildActivity(AppActivity.class).create().start().resume();AppActivity app=controller.get();app.receive("{\"type\":\"settings\"}");Intent settings=shadowOf(app).getNextStartedActivity();assertNotNull(settings);assertEquals(MainActivity.class.getName(),settings.getComponent().getClassName());controller.pause().stop().destroy();
    }
}

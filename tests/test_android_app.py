"""Exercise the actual Android browser adapter with a simulated native MessagePort."""
import json
import re
import unittest
from playwright.sync_api import expect
import test_archive as ui


class AndroidAppTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        self.context.add_init_script("Object.defineProperty(navigator,'userAgent',{value:navigator.userAgent+' ArecmikAndroid/1'});")
        self.context.route('**/firebase-auth.js', lambda route: route.fulfill(
            status=200, content_type='application/javascript',
            headers={'Access-Control-Allow-Origin': '*'}, body="""
            let listener;const auth={currentUser:{uid:'ui-test'},authStateReady:async()=>{}};
            export const getAuth=()=>auth;
            export class GoogleAuthProvider { static credential(idToken,accessToken){return {idToken,accessToken};} }
            export const signInWithPopup=async()=>{throw new Error('OAuth must use native browser handoff');};
            export const onAuthStateChanged=(a,cb)=>{listener=cb;setTimeout(()=>cb(auth.currentUser),0);};
            export const signOut=async()=>{auth.currentUser=null;listener(null);};
            export const signInWithCredential=async(a,credential)=>{window.__usedCredential=credential;auth.currentUser={uid:window.__credentialUid||'paired-user'};listener(auth.currentUser);return {user:auth.currentUser};};
            """))
        self.page.reload()
        expect(self.page.locator('#app')).to_be_visible()

    def connect_port(self):
        self.page.evaluate("""() => {
          window.__nativeMessages=[];
          const channel=new MessageChannel();window.__nativePort=channel.port1;
          channel.port1.onmessage=event=>window.__nativeMessages.push(JSON.parse(event.data));channel.port1.start();
          window.dispatchEvent(new MessageEvent('message',{data:'arecmik-native-v1',ports:[channel.port2]}));
        }""")
        self.page.wait_for_function("window.__nativeMessages.some(x=>x.type==='ready')")

    def send(self, message):
        self.page.evaluate("message=>window.__nativePort.postMessage(JSON.stringify(message))", message)

    def test_native_login_and_widget_settings_use_app_commands(self):
        self.connect_port()
        self.send({'type': 'account', 'uid': ''})
        expect(self.page.locator('#login')).to_be_visible()
        self.page.locator('#gl').click()
        self.page.wait_for_function("window.__nativeMessages.some(x=>x.type==='login')")

    def test_browser_google_credential_signs_into_app_and_acknowledges_matching_uid(self):
        self.connect_port()
        self.send({'type': 'account', 'uid': 'paired-user'})
        self.send({'type': 'credential', 'uid': 'paired-user', 'idToken': 'fake-google-id', 'accessToken': 'fake-google-access'})
        self.page.wait_for_function("window.ME?.uid==='paired-user' && window.__nativeMessages.some(x=>x.type==='auth-ok'&&x.uid==='paired-user')")
        expect(self.page.locator('#app')).to_be_visible()
        self.assertNotIn('fake-google', self.page.evaluate('JSON.stringify(localStorage)'))
        self.page.evaluate("document.querySelector('[data-widget-install]').click()")
        self.page.wait_for_function("window.__nativeMessages.some(x=>x.type==='settings')")

    def test_mismatched_credential_is_rejected_and_native_logout_signs_out(self):
        self.connect_port()
        self.send({'type': 'credential', 'uid': 'other-user', 'idToken': 'fake-google-id'})
        expect(self.page.locator('#login')).to_be_visible()
        self.assertFalse(self.page.evaluate("window.__nativeMessages.some(x=>x.type==='auth-ok')"))
        self.send({'type': 'credential', 'uid': 'paired-user', 'idToken': 'fake-google-id'})
        expect(self.page.locator('#app')).to_be_visible()
        self.send({'type': 'signed-out'})
        expect(self.page.locator('#login')).to_be_visible()

    def test_iframe_cannot_supply_native_channel(self):
        self.page.evaluate("""() => {
          const iframe=document.createElement('iframe');document.body.append(iframe);
          const channel=new MessageChannel();window.__forged=[];
          channel.port1.onmessage=e=>window.__forged.push(e.data);channel.port1.start();
          window.dispatchEvent(new MessageEvent('message',{source:iframe.contentWindow,data:'arecmik-native-v1',ports:[channel.port2]}));
        }""")
        self.connect_port()
        self.assertEqual(self.page.evaluate('window.__forged'), [])

    def test_android_back_closes_open_sheet_before_leaving_app(self):
        self.connect_port()
        self.page.locator('[data-search]').click()
        expect(self.page.locator('#srch')).to_have_class(re.compile(r'\bon\b'))
        self.send({'type': 'back'})
        expect(self.page.locator('#srch')).not_to_have_class(re.compile(r'\bon\b'))
        self.assertFalse(self.page.evaluate("window.__nativeMessages.some(x=>x.type==='back-unhandled')"))
        self.send({'type': 'back'})
        self.page.wait_for_function("window.__nativeMessages.some(x=>x.type==='back-unhandled')")

    def test_complete_backup_uses_native_save_picker_message(self):
        self.connect_port()
        self.page.evaluate("document.querySelector('[data-backup]').click()")
        self.page.wait_for_function("window.__nativeMessages.some(x=>x.type==='backup')")
        backup = self.page.evaluate("window.__nativeMessages.find(x=>x.type==='backup')")
        self.assertRegex(backup['name'], r'^Arecmik-백업-\d{4}-\d{2}-\d{2}\.json$')
        self.assertTrue(json.loads(backup['content'])['complete'])
        self.assertEqual(len(json.loads(backup['content'])['exps']), len(ui.SEED['exps']))


if __name__ == '__main__':
    unittest.main()

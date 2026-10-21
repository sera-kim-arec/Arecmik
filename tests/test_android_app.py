"""Exercise the actual Android browser adapter with a simulated native MessagePort."""
import json
import re
import hashlib
from pathlib import Path
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
        self.send({'type': 'account', 'uid': 'paired-user', 'capabilities': ['update']})
        self.send({'type': 'credential', 'uid': 'paired-user', 'idToken': 'fake-google-id', 'accessToken': 'fake-google-access'})
        self.page.wait_for_function("window.ME?.uid==='paired-user' && window.__nativeMessages.some(x=>x.type==='auth-ok'&&x.uid==='paired-user')")
        expect(self.page.locator('#app')).to_be_visible()
        self.assertNotIn('fake-google', self.page.evaluate('JSON.stringify(localStorage)'))
        self.page.evaluate("document.querySelector('[data-widget-install]').click()")
        self.page.wait_for_function("window.__nativeMessages.some(x=>x.type==='settings')")
        self.page.evaluate("document.querySelector('[data-apk-download]').click()")
        self.page.wait_for_function("window.__nativeMessages.some(x=>x.type==='update')")

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

    def test_back_from_related_document_restores_project_then_project_list(self):
        self.connect_port()
        self.page.evaluate("""async()=>{const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await m.updateDoc(m.doc(m.collection({},'notes'),'work-n'),{pid:'work-p'})}""")
        self.page.locator("nav [data-tab='proj']").click();self.page.locator('[data-open="work-p"]').click()
        ui.reveal(self.page,'.project-records [data-archive-open="doc"]')
        self.page.locator('.project-records [data-archive-open="doc"]').click()
        expect(self.page.locator('[data-db]')).to_be_visible()
        self.send({'type':'back'});expect(self.page.locator('.pname')).to_have_value('업무 프로젝트')
        self.send({'type':'back'});expect(self.page.locator('[data-open="work-p"]')).to_be_visible()
        self.assertFalse(self.page.evaluate("window.__nativeMessages.some(x=>x.type==='back-unhandled')"))

    def test_back_restores_search_query_and_reference_draft(self):
        self.connect_port();self.page.locator('[data-search]').click();self.page.locator('#sqi').fill('업무 회의록')
        self.page.locator('#sqr [data-sgo="doc"]').click();expect(self.page.locator('[data-db]')).to_be_visible()
        self.send({'type':'back'});expect(self.page.locator('#srch')).to_have_class(re.compile(r'\bon\b'))
        expect(self.page.locator('#sqi')).to_have_value('업무 회의록');self.send({'type':'back'})
        ui.record_source(self.page, 'ref');self.page.locator('[data-newref]').click();self.page.locator('#r-t').fill('뒤로가도 유지할 자료')
        self.send({'type':'back'});expect(self.page.locator('#scrim')).not_to_have_class('scrim on')
        self.page.locator('[data-newref]').click();expect(self.page.locator('#r-t')).to_have_value('뒤로가도 유지할 자료')

    def test_old_native_app_without_updater_downloads_the_new_apk(self):
        self.connect_port()
        self.send({'type': 'account', 'uid': 'ui-test'})
        self.page.locator('[data-menu]').click()
        with self.page.expect_download() as result:
            self.page.locator('[data-apk-download]').click()
        expected = (ui.ROOT/'downloads/SHA256SUMS.txt').read_text().split()[0]
        self.assertEqual(hashlib.sha256(Path(result.value.path()).read_bytes()).hexdigest(), expected)


if __name__ == '__main__':
    unittest.main()

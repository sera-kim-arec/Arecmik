"""The browser hands credentials only to the requesting device's encryption key."""
import base64
import hashlib
import json
from pathlib import Path
import unittest
from playwright.sync_api import expect
import test_archive as ui


class WidgetPairingTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        self.context.route('**/firebase-auth.js', lambda route: route.fulfill(
            status=200, content_type='application/javascript',
            headers={'Access-Control-Allow-Origin': '*'}, body="""
            export const getAuth=()=>({});export const GoogleAuthProvider=class {};
            export const signInWithPopup=async()=>{};
            export const onAuthStateChanged=(a,cb)=>setTimeout(()=>cb({uid:'ui-test',displayName:'테스트 계정',refreshToken:'fake-test-refresh-token-that-is-not-a-real-credential',getIdToken:async()=>'test-id-token'}),0);
            """))
        self.pair = self.page.evaluate("""async () => {
          const {b64}=await import('./widget-pairing.js');
          const keys=await crypto.subtle.generateKey({name:'ECDH',namedCurve:'P-256'},true,['deriveBits']);
          const request={v:1,nonce:b64(crypto.getRandomValues(new Uint8Array(24))),expires:Date.now()+600000,publicKey:b64(await crypto.subtle.exportKey('spki',keys.publicKey))};
          return {request,fragment:'#pair='+b64(new TextEncoder().encode(JSON.stringify(request))),privateKey:await crypto.subtle.exportKey('jwk',keys.privateKey)};
        }""")

    def test_explicit_approval_encrypts_and_binds_account_to_device_session(self):
        self.page.goto(self.origin+'/widget-connect.html'+self.pair['fragment'])
        expect(self.page.locator('#connect-status')).to_contain_text('테스트 계정')
        expect(self.page.locator('#return-widget')).not_to_be_visible()
        self.assertNotIn('pair=', self.page.url)
        self.page.locator('#widget-authorize').click()
        expect(self.page.locator('#return-widget')).to_be_visible()
        uri = self.page.locator('#return-widget').get_attribute('href')
        self.assertNotIn('refreshToken', uri)
        self.assertNotIn('ui-test', uri)
        decoded = self.page.evaluate("""async ({uri,privateKey}) => {
          const {unb64}=await import('./widget-pairing.js');
          const e=JSON.parse(new TextDecoder().decode(unb64(uri.split('#data=')[1])));
          const privateCryptoKey=await crypto.subtle.importKey('jwk',privateKey,{name:'ECDH',namedCurve:'P-256'},false,['deriveBits']);
          const publicKey=await crypto.subtle.importKey('spki',unb64(e.publicKey),{name:'ECDH',namedCurve:'P-256'},false,[]);
          const bits=new Uint8Array(await crypto.subtle.deriveBits({name:'ECDH',public:publicKey},privateCryptoKey,256));
          const aad=new TextEncoder().encode('arecmik-widget:v1:'+e.nonce),material=new Uint8Array(bits.length+aad.length);material.set(bits);material.set(aad,bits.length);
          const key=await crypto.subtle.importKey('raw',await crypto.subtle.digest('SHA-256',material),'AES-GCM',false,['decrypt']);
          return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:unb64(e.iv),additionalData:aad},key,unb64(e.data))));
        }""", {'uri': uri, 'privateKey': self.pair['privateKey']})
        self.assertEqual(decoded['uid'], 'ui-test')
        self.assertEqual(decoded['projectId'], 'arecmik-25699')
        self.assertEqual(decoded['refreshToken'], 'fake-test-refresh-token-that-is-not-a-real-credential')
        self.assertNotIn('fake-test-refresh-token', self.page.evaluate('JSON.stringify(localStorage)'))

    def test_missing_or_expired_request_never_enables_credential_transfer(self):
        for fragment in ['', '#pair=bad', self.expired_fragment()]:
            with self.subTest(fragment=fragment[:20]):
                self.page.goto(self.origin+'/widget-connect.html'+fragment)
                expect(self.page.locator('#widget-authorize')).not_to_be_visible()
                expect(self.page.locator('#return-widget')).not_to_be_visible()
                expect(self.page.locator('#connect-status')).not_to_contain_text('확인하고 있어요')

    def expired_fragment(self):
        request = dict(self.pair['request'], expires=1)
        return '#pair='+base64.urlsafe_b64encode(json.dumps(request).encode()).decode().rstrip('=')

    def test_install_page_has_apk_link_and_mobile_instructions(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.goto(self.origin+'/widget.html')
        expect(self.page.locator('a[download]')).to_have_attribute('href', 'downloads/Arecmik-widget-1.0.0.apk')
        expect(self.page.locator('main')).to_contain_text('홈 화면에 위젯 추가')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
        with self.page.expect_download() as result:
            self.page.locator('a[download]').click()
        download = result.value
        self.assertEqual(download.suggested_filename, 'Arecmik-widget-1.0.0.apk')
        expected = (ui.ROOT/'downloads/SHA256SUMS.txt').read_text().split()[0]
        self.assertEqual(hashlib.sha256(Path(download.path()).read_bytes()).hexdigest(), expected)


if __name__ == '__main__':
    unittest.main()

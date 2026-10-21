"""Schedule memo photos must survive saving/reopening; Firebase is mocked."""
import base64
import unittest

from playwright.sync_api import expect
import test_archive as ui


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1XcAAAAASUVORK5CYII=')


class MemoImageTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown
    search = ui.ArchiveTests.search

    def open_event(self):
        self.search('보고서 제출')
        self.page.locator('#sqr [data-sgo="todo"]').click()
        expect(self.page.locator('#e-n')).to_be_visible()

    def paste_photo(self):
        self.page.locator('#e-n').focus()
        self.page.locator('#e-n').evaluate("""(ed, bytes) => {
          const cd=new DataTransfer();
          cd.items.add(new File([new Uint8Array(bytes)],'photo.png',{type:'image/png'}));
          ed.dispatchEvent(new ClipboardEvent('paste',{clipboardData:cd,bubbles:true,cancelable:true}));
        }""", list(PNG))

    def assert_photo_loaded(self, selector='#e-n img[data-img]'):
        expect(self.page.locator(selector)).to_have_count(1)
        self.page.wait_for_function("s=>{const im=document.querySelector(s);return im?.complete&&im.naturalWidth>0}", arg=selector, timeout=3000)

    def test_pasted_photo_survives_save_reopen_and_reload(self):
        self.open_event()
        self.paste_photo()
        self.assert_photo_loaded()
        self.page.locator('[data-esave]').click()
        expect(self.page.locator('#scrim')).not_to_have_class('scrim on')
        saved=self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').noteH")
        self.assertIn('data-img=', saved)
        self.assertNotIn('src=', saved)
        self.open_event()
        self.assert_photo_loaded()
        self.page.reload()
        self.open_event()
        self.assert_photo_loaded()
        expect(self.page.locator('#e-n')).to_contain_text('검토 의견')

    def pick_photos(self, payloads=None):
        with self.page.expect_file_chooser() as chosen:
            self.page.locator('[data-memo-photo="e-n"]').click()
        chosen.value.set_files(payloads if payloads is not None else [{'name':'photo.png','mimeType':'image/png','buffer':PNG}])

    def test_mobile_picker_adds_multiple_photos_and_saves_image_only_memo(self):
        self.page.set_viewport_size({'width':360,'height':800})
        self.open_event()
        self.page.locator('#e-kind').select_option('event')
        self.page.locator('#e-n').fill('')
        self.pick_photos([{'name':f'photo-{i}.png','mimeType':'image/png','buffer':PNG} for i in range(2)])
        expect(self.page.locator('#e-n img[data-img]')).to_have_count(2)
        expect(self.page.locator('.image-upload-status')).to_have_count(0)
        self.page.locator('[data-esave]').click()
        self.page.reload()
        self.open_event()
        expect(self.page.locator('#e-n img[data-img]')).to_have_count(2)
        self.page.wait_for_function("[...document.querySelectorAll('#e-n img')].every(im=>im.naturalWidth>0)")
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').kind"),'event')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),360)
        self.assertGreaterEqual(self.page.locator('[data-memo-photo]').bounding_box()['height'],44)

    def test_upload_failure_preserves_text_and_can_retry(self):
        self.open_event()
        self.page.evaluate("window.__failWritesFor='imgs'")
        self.pick_photos()
        expect(self.page.locator('.toast')).to_contain_text('다시 추가해 주세요')
        expect(self.page.locator('#e-n')).to_contain_text('검토 의견')
        expect(self.page.locator('#e-n img')).to_have_count(0)
        expect(self.page.locator('.image-upload-status')).to_have_count(0)
        self.page.evaluate('window.__failWritesFor=null')
        self.pick_photos()
        self.assert_photo_loaded()
        self.page.locator('[data-esave]').click()
        self.page.reload()
        self.open_event()
        self.assert_photo_loaded()

    def test_slow_upload_cannot_be_saved_or_closed_before_attachment_arrives(self):
        self.open_event()
        self.page.evaluate('window.__writeDelayMs=1200')
        self.pick_photos()
        expect(self.page.locator('.image-upload-status')).to_contain_text('사진 올리는 중')
        self.page.locator('[data-esave]').click()
        expect(self.page.locator('.toast')).to_contain_text('완료 후 저장')
        self.page.locator('#sheet [data-sx="0"]').click()
        expect(self.page.locator('.toast')).to_contain_text('완료 후 닫아')
        ui.reveal(self.page,'#sheet [data-conn-record]')
        self.page.locator('#sheet [data-conn-record]').click()
        expect(self.page.locator('#e-n')).to_be_visible()
        expect(self.page.locator('#scrim')).to_have_class('scrim on')
        self.assert_photo_loaded()
        expect(self.page.locator('.image-upload-status')).to_have_count(0)
        self.page.evaluate('window.__writeDelayMs=0')
        self.page.locator('[data-esave]').click()
        expect(self.page.locator('#scrim')).not_to_have_class('scrim on')
        self.open_event()
        self.assert_photo_loaded()

    def test_canceled_picker_and_upload_leave_memo_editable(self):
        self.open_event()
        self.pick_photos([])
        expect(self.page.locator('.image-upload-status')).to_have_count(0)
        expect(self.page.locator('#e-n')).not_to_have_attribute('aria-busy','true')
        self.page.evaluate('window.__writeDelayMs=1500')
        self.pick_photos()
        self.page.locator('.image-upload-status button').click()
        expect(self.page.locator('.image-upload-status')).to_have_count(0)
        self.page.locator('#e-n').fill('사진 없이 저장할 메모')
        self.page.evaluate('window.__writeDelayMs=0')
        self.page.locator('[data-esave]').click()
        self.page.wait_for_timeout(1700)
        self.open_event()
        expect(self.page.locator('#e-n')).to_contain_text('사진 없이 저장할 메모')
        expect(self.page.locator('#e-n img')).to_have_count(0)

    def test_photo_draft_survives_close_and_reload_without_overwriting_saved_memo(self):
        self.open_event()
        self.pick_photos()
        self.assert_photo_loaded()
        self.page.locator('#sheet [data-sx="0"]').click()
        self.assertNotIn('data-img=',self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').noteH"))
        self.page.reload()
        self.open_event()
        expect(self.page.locator('.form-draft-note')).to_be_visible()
        self.assert_photo_loaded()
        self.page.locator('[data-esave]').click()
        self.page.reload()
        self.open_event()
        self.assert_photo_loaded()
        expect(self.page.locator('.form-draft-note')).to_have_count(0)

    def test_slash_photo_entry_still_saves_and_reopens(self):
        self.open_event()
        self.page.locator('#e-n').fill('')
        self.page.locator('#e-n').press('/')
        with self.page.expect_file_chooser() as chosen:
            self.page.locator('.slm button').filter(has_text='사진').click()
        chosen.value.set_files({'name':'photo.png','mimeType':'image/png','buffer':PNG})
        self.assert_photo_loaded()
        self.page.locator('[data-esave]').click()
        self.open_event()
        self.assert_photo_loaded()


if __name__ == '__main__':
    unittest.main()

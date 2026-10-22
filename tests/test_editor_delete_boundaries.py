"""Character deletion near a toggle must never select its structural containers."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors
from test_memo_images import PNG
import base64

class EditorDeleteBoundaryTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    note=editors.BlockEditorTests.note
    patch=editors.BlockEditorTests.patch

    def seed(self,opened=True,before='',after='',body='<div>본문 보존</div>'):
        self.patch('notes','work-n',{'html':before+'<div class="nb-toggle" data-expanded="'+str(opened).lower()+'"><div class="nb-toggle-title">제목 보존</div><div class="nb-toggle-body">'+body+'</div></div>'+after})
        return self.note()

    def assert_no_container_selection(self,ed):
        expect(ed.locator('.nb-toggle.ProseMirror-selectednode,.nb-toggle-body.ProseMirror-selectednode')).to_have_count(0)

    def test_delete_after_previous_text_enters_title_instead_of_deleting_whole_toggle(self):
        p=self.page;ed=self.seed(before='<div>앞 글</div>');ed.locator(':scope > div').first.click();p.keyboard.press('End');p.keyboard.press('Delete');self.assert_no_container_selection(ed)
        expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존');p.keyboard.press('Delete')
        expect(ed.locator('.nb-toggle-title')).to_have_text('목 보존');expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존');expect(ed.locator(':scope > div').first).to_have_text('앞 글')
        p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존')

    def test_backspace_before_following_text_enters_body_without_selecting_toggle(self):
        p=self.page;ed=self.seed(after='<div>뒤 글</div>');ed.locator(':scope > div').last.click();p.keyboard.press('Home');p.keyboard.press('Backspace');self.assert_no_container_selection(ed)
        p.keyboard.press('Backspace');expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보');expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존');expect(ed.locator(':scope > div').last).to_have_text('뒤 글')

    def test_backspace_after_closed_toggle_only_edits_visible_title(self):
        p=self.page;ed=self.seed(opened=False,after='<div>뒤 글</div>');ed.locator(':scope > div').last.click();p.keyboard.press('Home');p.keyboard.press('Backspace');self.assert_no_container_selection(ed)
        p.keyboard.press('Backspace');expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보');expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존');expect(ed.locator('.nb-toggle-body')).to_be_hidden()

    def test_delete_at_open_title_end_enters_body_then_deletes_one_character(self):
        p=self.page;ed=self.seed();ed.locator('.nb-toggle-title').click();p.keyboard.press('End');p.keyboard.press('Delete');self.assert_no_container_selection(ed)
        expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존');p.keyboard.press('Delete');expect(ed.locator('.nb-toggle-body')).to_have_text('문 보존');expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존')

    def test_delete_at_closed_title_end_does_not_select_or_clear_hidden_body(self):
        p=self.page;ed=self.seed(opened=False);ed.locator('.nb-toggle-title').click();p.keyboard.press('End')
        p.keyboard.press('Delete');p.keyboard.press('Delete');self.assert_no_container_selection(ed)
        expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존');expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존');expect(ed.locator('.nb-toggle-body')).to_be_hidden()

    def test_native_delete_forward_intent_uses_same_safe_title_boundary(self):
        p=self.page;ed=self.seed();ed.locator('.nb-toggle-title').click();p.keyboard.press('End')
        stopped=ed.evaluate("ed=>!ed.dispatchEvent(new InputEvent('beforeinput',{inputType:'deleteContentForward',bubbles:true,cancelable:true}))")
        self.assertTrue(stopped);expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존');self.assert_no_container_selection(ed)
        p.keyboard.insert_text('추가 ');expect(ed.locator('.nb-toggle-body')).to_have_text('추가 본문 보존')

    def test_explicit_select_all_delete_and_undo_restores_closed_toggle_and_photo(self):
        p=self.page;self.patch('imgs','qa-photo',{'d':'data:image/png;base64,'+base64.b64encode(PNG).decode()})
        ed=self.seed(opened=False,body='<div>본문 보존</div><div class="img"><img data-img="qa-photo"></div>')
        ed.locator('.nb-toggle-title').click();p.keyboard.press('Control+a');p.keyboard.press('Delete');expect(ed.locator('.nb-toggle,img')).to_have_count(0)
        p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-body')).to_be_hidden();expect(ed.locator('.nb-toggle-body')).to_contain_text('본문 보존');expect(ed.locator('img[data-img="qa-photo"]')).to_have_count(1)
        ed.locator('.nb-toggle-title').click();p.keyboard.press('End');p.keyboard.insert_text(' 보완')
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('보완')")
        saved=p.evaluate("__store.notes.find(n=>n.id==='work-n').html");self.assertIn('data-img="qa-photo"',saved);self.assertNotIn('src=',saved)
        p.reload();ed=self.note();expect(ed.locator('.nb-toggle-body')).to_be_hidden();ed.locator('.nb-toggle-arrow').click();expect(ed.locator('img')).to_be_visible();p.wait_for_function("document.querySelector('[data-db] img')?.naturalWidth>0")

    def test_chromium_ime_composition_and_cancellation_preserve_committed_text(self):
        p=self.page;ed=self.seed();ed.locator('.nb-toggle-title').click();p.keyboard.press('End');cdp=self.context.new_cdp_session(p)
        for text in ['ㄱ','가','각']:cdp.send('Input.imeSetComposition',{'text':text,'selectionStart':len(text),'selectionEnd':len(text)})
        cdp.send('Input.insertText',{'text':'가각'});expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존가각');expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존')
        cdp.send('Input.imeSetComposition',{'text':'ㄴ','selectionStart':1,'selectionEnd':1});cdp.send('Input.imeSetComposition',{'text':'','selectionStart':0,'selectionEnd':0})
        expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존가각');p.keyboard.press('Backspace');expect(ed.locator('.nb-toggle-title')).to_have_text('제목 보존가')

    def test_control_delete_at_toggle_boundary_preserves_body(self):
        p=self.page;ed=self.seed(before='<div>앞 글</div>');ed.locator(':scope > div').first.click();p.keyboard.press('End');p.keyboard.press('Control+Delete');self.assert_no_container_selection(ed)
        p.keyboard.press('Control+Delete');expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존');expect(ed.locator('.nb-toggle-title')).not_to_have_text('')

    def test_control_backspace_after_closed_toggle_preserves_hidden_body(self):
        p=self.page;ed=self.seed(opened=False,after='<div>뒤 글</div>');ed.locator(':scope > div').last.click();p.keyboard.press('Home');p.keyboard.press('Control+Backspace');self.assert_no_container_selection(ed)
        p.keyboard.press('Control+Backspace');expect(ed.locator('.nb-toggle-body')).to_have_text('본문 보존');expect(ed.locator(':scope > div').last).to_have_text('뒤 글');expect(ed.locator('.nb-toggle-body')).to_be_hidden()

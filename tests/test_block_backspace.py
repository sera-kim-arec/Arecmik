"""Empty toggle lines must not jump between the body and the following block."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class BlockBackspaceTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    note=editors.BlockEditorTests.note
    patch=editors.BlockEditorTests.patch

    def seed(self,body='<div><br></div>',after='',opened=True):
        self.patch('notes','work-n',{'html':'<div class="nb-toggle" data-expanded="'+str(opened).lower()+'"><div class="nb-toggle-title">기억할 제목</div><div class="nb-toggle-body">'+body+'</div></div>'+after})
        return self.note()

    def assert_title_caret(self):
        self.assertTrue(self.page.evaluate("!!getSelection().anchorNode?.parentElement?.closest('.nb-toggle-title')"))

    def test_empty_first_body_backspace_returns_to_title_without_creating_outside_line(self):
        p=self.page;ed=self.seed();ed.locator('.nb-toggle-body > div').click();p.keyboard.press('Backspace')
        expect(ed.locator(':scope > div')).to_have_count(1);expect(ed.locator('.nb-toggle-body > div')).to_have_count(1);self.assert_title_caret()
        p.keyboard.insert_text(' 이어 쓰기');expect(ed.locator('.nb-toggle-title')).to_have_text('기억할 제목 이어 쓰기')
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('이어 쓰기')")
        p.reload();ed=self.note();expect(ed.locator(':scope > div')).to_have_count(1)

    def test_empty_first_line_before_other_body_content_is_removed_without_moving_content(self):
        p=self.page;ed=self.seed('<div><br></div><div>남길 내용</div>');ed.locator('.nb-toggle-body > div').first.click();p.keyboard.press('Backspace')
        expect(ed.locator('.nb-toggle-body > div')).to_have_text(['남길 내용']);self.assert_title_caret()
        p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-body > div')).to_have_text(['','남길 내용'])

    def test_empty_following_line_skips_empty_placeholder_and_returns_to_title(self):
        p=self.page;ed=self.seed(after='<div><br></div>');ed.locator(':scope > div').last.click();p.keyboard.press('Backspace')
        expect(ed.locator(':scope > div')).to_have_count(1);self.assert_title_caret()
        p.keyboard.insert_text(' 수정');expect(ed.locator('.nb-toggle-title')).to_have_text('기억할 제목 수정')
        expect(ed.locator('.nb-toggle-body > div')).to_have_count(1)

    def test_following_line_after_closed_toggle_preserves_hidden_content_and_undo(self):
        p=self.page;ed=self.seed('<div>숨겨진 본문</div>',after='<div><br></div>',opened=False);ed.locator(':scope > div').last.click();p.keyboard.press('Backspace')
        self.assert_title_caret();expect(ed.locator('.nb-toggle-body')).to_be_hidden();expect(ed.locator('.nb-toggle-body')).to_have_text('숨겨진 본문')
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div')).to_have_count(2);expect(ed.locator('.nb-toggle-body')).to_have_text('숨겨진 본문')

    def test_android_delete_beforeinput_uses_same_empty_body_behavior(self):
        p=self.page;ed=self.seed();ed.locator('.nb-toggle-body > div').click()
        prevented=ed.evaluate("""ed=>!ed.dispatchEvent(new InputEvent('beforeinput',{inputType:'deleteContentBackward',bubbles:true,cancelable:true}))""")
        self.assertTrue(prevented);self.assert_title_caret();expect(ed.locator(':scope > div')).to_have_count(1)
        p.keyboard.insert_text(' 입력');expect(ed.locator('.nb-toggle-title')).to_have_text('기억할 제목 입력')

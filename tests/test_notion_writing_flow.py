"""Behavior from the user's writing video, using real keys and mocked storage."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class NotionWritingFlowTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    note=editors.BlockEditorTests.note
    patch=editors.BlockEditorTests.patch
    choose=editors.BlockEditorTests.choose

    def seed(self,html):
        self.patch('notes','work-n',{'html':html});return self.note()

    def saved(self,marker):
        self.page.wait_for_function("s=>__store.notes.find(n=>n.id==='work-n').html.includes(s)",arg=marker)
        return self.page.evaluate("__store.notes.find(n=>n.id==='work-n').html")

    def body(self,html,after=''):
        return self.seed('<div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">토글 제목</div><div class="nb-toggle-body">'+html+'</div></div>'+after)

    def test_enter_and_shift_enter_have_distinct_spacing_and_survive_reload(self):
        p=self.page;ed=self.seed('');ed.fill('첫 문단');p.keyboard.press('Enter');p.keyboard.insert_text('다음 문단');p.keyboard.press('Shift+Enter');p.keyboard.insert_text('같은 문단의 둘째 줄')
        expect(ed.locator(':scope > div')).to_have_text(['첫 문단','다음 문단같은 문단의 둘째 줄'])
        expect(ed.locator(':scope > div').last.locator('br:not(.ProseMirror-trailingBreak)')).to_have_count(1)
        spacing=ed.evaluate("""el=>{const a=el.children[0],b=el.children[1],first=document.createRange(),second=document.createRange(),soft=document.createRange();first.selectNodeContents(a);second.setStart(b.firstChild,0);second.setEnd(b.firstChild,b.firstChild.length);soft.setStart(b.lastChild,0);soft.setEnd(b.lastChild,b.lastChild.length);return {block:second.getBoundingClientRect().top-first.getBoundingClientRect().top,line:soft.getBoundingClientRect().top-second.getBoundingClientRect().top}}""")
        self.assertGreater(spacing['block'],spacing['line']+3)
        html=self.saved('같은 문단의 둘째 줄');self.assertNotIn('nb-text-block',html);self.assertNotIn('data-placeholder',html)
        p.reload();ed=self.note();expect(ed.locator(':scope > div')).to_have_count(2);expect(ed.locator(':scope > div').last.locator('br:not(.ProseMirror-trailingBreak)')).to_have_count(1)

    def test_final_empty_body_backspace_leaves_toggle_and_undo_redo_preserve_text(self):
        p=self.page;ed=self.body('<div>남길 내용</div><div><br></div>');ed.locator('.nb-toggle-body > div').last.click();p.keyboard.press('Backspace');p.keyboard.insert_text('토글 밖에 작성')
        expect(ed.locator('.nb-toggle-body > div')).to_have_text(['남길 내용']);expect(ed.locator(':scope > div').last).to_have_text('토글 밖에 작성')
        self.saved('토글 밖에 작성');p.reload();ed=self.note();expect(ed.locator('.nb-toggle-body > div')).to_have_text(['남길 내용']);expect(ed.locator(':scope > div').last).to_have_text('토글 밖에 작성')
        # Give the same structural command its own undo step.
        ed=self.seed('<div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">제목</div><div class="nb-toggle-body"><div>본문</div><div><br></div></div></div>')
        ed.locator('.nb-toggle-body > div').last.click();p.keyboard.press('Backspace');expect(ed.locator(':scope > div')).to_have_count(2)
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div')).to_have_count(1);expect(ed.locator('.nb-toggle-body > div')).to_have_text(['본문',''])
        p.keyboard.press('Control+Shift+z');expect(ed.locator(':scope > div')).to_have_count(2);expect(ed.locator('.nb-toggle-body > div')).to_have_text(['본문'])

    def test_empty_middle_body_line_keeps_following_content_inside(self):
        p=self.page;ed=self.body('<div>첫 줄</div><div><br></div><div>마지막 줄</div>');ed.locator('.nb-toggle-body > div').nth(1).click();p.keyboard.press('Backspace')
        expect(ed.locator(':scope > div')).to_have_count(1);expect(ed.locator('.nb-toggle-body > div')).to_have_text(['첫 줄','마지막 줄'])

    def test_nested_toggle_exit_moves_only_one_level_and_keeps_following_sibling(self):
        p=self.page;ed=self.body('<div>바깥 본문</div><div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">안쪽 제목</div><div class="nb-toggle-body"><div>안쪽 본문</div><div><br></div></div></div><div>뒤에 남길 내용</div>')
        inner=ed.locator('.nb-toggle').nth(1);inner.locator('.nb-toggle-body > div').last.click();p.keyboard.press('Backspace');p.keyboard.insert_text('안쪽에서 나온 문단')
        expect(ed.locator(':scope > div')).to_have_count(1);expect(inner.locator('.nb-toggle-body > div')).to_have_text(['안쪽 본문']);outer=ed.locator('.nb-toggle-body').first
        expect(outer.locator(':scope > div')).to_have_count(4);expect(outer.locator(':scope > div')).to_contain_text(['바깥 본문','안쪽 제목안쪽 본문','안쪽에서 나온 문단','뒤에 남길 내용'])

    def test_native_mobile_backspace_uses_the_same_final_empty_line_exit(self):
        p=self.page;p.set_viewport_size({'width':390,'height':844});ed=self.body('<div>남길 내용</div><div><br></div>');ed.locator('.nb-toggle-body > div').last.click()
        stopped=ed.evaluate("ed=>!ed.dispatchEvent(new InputEvent('beforeinput',{inputType:'deleteContentBackward',bubbles:true,cancelable:true}))")
        self.assertTrue(stopped);p.keyboard.insert_text('휴대폰에서 밖으로');expect(ed.locator('.nb-toggle-body > div')).to_have_text(['남길 내용']);expect(ed.locator(':scope > div').last).to_have_text('휴대폰에서 밖으로')

    def test_native_line_break_stays_in_toggle_title_and_preserves_body(self):
        p=self.page;ed=self.body('<div>기존 본문</div>');ed.locator('.nb-toggle-title').click();p.keyboard.press('End')
        stopped=ed.evaluate("ed=>!ed.dispatchEvent(new InputEvent('beforeinput',{inputType:'insertLineBreak',bubbles:true,cancelable:true}))")
        self.assertTrue(stopped);p.keyboard.insert_text('두 줄 제목');expect(ed.locator('.nb-toggle-title br:not(.ProseMirror-trailingBreak)')).to_have_count(1);expect(ed.locator('.nb-toggle-body > div')).to_have_text(['기존 본문'])
        self.saved('두 줄 제목');p.reload();ed=self.note();expect(ed.locator('.nb-toggle-title br:not(.ProseMirror-trailingBreak)')).to_have_count(1);expect(ed.locator('.nb-toggle-body')).to_have_text('기존 본문')

    def test_quote_menu_soft_line_and_exit_match_the_recording(self):
        p=self.page;ed=self.seed('');ed.fill('');p.keyboard.press('/');self.choose('인용');p.keyboard.insert_text('인용 첫 줄');p.keyboard.press('Shift+Enter');p.keyboard.insert_text('인용 둘째 줄');p.keyboard.press('Enter');p.keyboard.insert_text('인용 밖의 문단')
        expect(ed.locator('.qt')).to_have_text('인용 첫 줄인용 둘째 줄');expect(ed.locator('.qt br')).to_have_count(1);expect(ed.locator(':scope > div').last).to_have_text('인용 밖의 문단')
        self.saved('인용 밖의 문단');p.reload();ed=self.note();expect(ed.locator('.qt br')).to_have_count(1);expect(ed.locator(':scope > div').last).to_have_text('인용 밖의 문단')

    def test_soft_break_only_body_is_preserved_when_enter_splits_it(self):
        p=self.page;ed=self.body('<div><br><br></div><div>다음 내용</div>');line=ed.locator('.nb-toggle-body > div').first;line.evaluate("el=>{el.focus();const r=document.createRange();r.selectNodeContents(el);r.collapse(false);getSelection().removeAllRanges();getSelection().addRange(r)}");p.keyboard.press('Enter')
        expect(ed.locator(':scope > div')).to_have_count(1);expect(ed.locator('.nb-toggle-body > div')).to_have_count(3);expect(ed.locator('.nb-toggle-body > div').first.locator('br:not(.ProseMirror-trailingBreak)')).to_have_count(2);expect(ed.locator('.nb-toggle-body > div').last).to_have_text('다음 내용')

if __name__=='__main__':unittest.main()

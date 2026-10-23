"""User-facing block operations beyond creating a lookalike block."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class BlockWritingTests(unittest.TestCase):
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

    def select(self,ed,first,last):
        ed.evaluate("""(ed,[first,last])=>{ed.focus();const r=document.createRange();r.setStart(ed.children[first],0);r.setEnd(ed.children[last],ed.children[last].childNodes.length);getSelection().removeAllRanges();getSelection().addRange(r)}""",[first,last])
        ed.locator(':scope > div').nth(first).hover()
        expect(self.page.locator('.nb-inline')).to_be_visible()
        self.page.wait_for_function("document.querySelectorAll('.nb-selected-block').length>=2")

    def test_multiple_selected_blocks_convert_duplicate_delete_and_undo_together(self):
        p=self.page;ed=self.seed('<div><strong>첫째</strong></div><div>둘째</div><div>셋째</div>');self.select(ed,0,1)
        p.locator('[data-block-menu]').click();self.choose('글머리 목록')
        expect(ed.locator(':scope > .li')).to_have_text(['첫째','둘째']);expect(ed.locator('strong')).to_have_text('첫째')
        ed.locator(':scope > div').first.hover()
        p.locator('[data-block-menu]').click();self.choose('복제')
        expect(ed.locator(':scope > div')).to_have_text(['첫째','둘째','첫째','둘째','셋째'])
        ed.locator(':scope > div').nth(2).hover()
        p.locator('[data-block-menu]').click();self.choose('삭제')
        expect(ed.locator(':scope > div')).to_have_text(['첫째','둘째','셋째'])
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div')).to_have_text(['첫째','둘째','첫째','둘째','셋째'])

    def test_divider_and_conversion_keep_text_and_photo_in_a_mixed_selection(self):
        p=self.page;ed=self.seed('<div>남겨야 할 본문</div><div class="img"><img data-img="kept-photo" alt="사진"></div><div>마지막 문단</div>');self.select(ed,0,2)
        p.locator('[data-block-menu]').click();self.choose('큰 제목')
        expect(ed.locator('img[data-img="kept-photo"]')).to_have_count(1);expect(ed.locator('.h1')).to_have_text(['남겨야 할 본문','마지막 문단'])
        ed.locator(':scope > div').first.click();p.locator('[data-block-menu]').click();self.choose('구분선')
        expect(ed.locator(':scope > div').first).to_have_text('남겨야 할 본문');expect(ed.locator('.hrl2')).to_have_count(1);expect(ed.locator('img[data-img="kept-photo"]')).to_have_count(1)

    def test_hover_plus_inserts_after_hovered_block_and_leaves_original_caret_text_untouched(self):
        p=self.page;ed=self.seed('<div>원래 쓰던 문단</div><div>여기에 추가</div>');ed.locator(':scope > div').first.click();p.keyboard.press('End')
        ed.locator(':scope > div').last.hover();p.locator('[data-block-add]').click();self.choose('본문');p.keyboard.insert_text('추가한 문단')
        expect(ed.locator(':scope > div')).to_have_text(['원래 쓰던 문단','여기에 추가','추가한 문단'])

    def test_native_copy_paste_keeps_block_structure_formatting_and_cut_undo(self):
        p=self.page;ed=self.seed('<div><strong>첫 문단</strong></div><div class="li" data-depth="1">들여쓴 목록</div><div><br></div>');self.context.grant_permissions(['clipboard-read','clipboard-write'],origin=self.origin)
        self.select(ed,0,1);p.keyboard.press('Control+c');ed.locator(':scope > div').last.click();p.keyboard.press('Control+v')
        expect(ed.locator(':scope > div')).to_have_text(['첫 문단','들여쓴 목록','첫 문단','들여쓴 목록'])
        expect(ed.locator('strong')).to_have_count(2);expect(ed.locator('.li[data-depth="1"]')).to_have_count(2)
        self.select(ed,2,3);p.keyboard.press('Control+x');expect(ed.locator(':scope > div')).to_have_text(['첫 문단','들여쓴 목록',''])
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div')).to_have_text(['첫 문단','들여쓴 목록','첫 문단','들여쓴 목록'])

    def test_pasted_html_numbered_and_nested_lists_keep_their_kind_and_indent(self):
        p=self.page;ed=self.seed('');ed.fill('')
        html='<ol><li>첫 순서<ul><li>안쪽 항목</li></ul></li><li>두 번째 순서</li></ol>'
        ed.evaluate("""(ed,html)=>{const cd=new DataTransfer();cd.setData('text/html',html);cd.setData('text/plain','순서');ed.dispatchEvent(new ClipboardEvent('paste',{clipboardData:cd,bubbles:true,cancelable:true}))}""",html)
        expect(ed.locator('.num')).to_have_text(['첫 순서','두 번째 순서']);expect(ed.locator('.num').last).to_have_attribute('data-n','2');expect(ed.locator('.li[data-depth="1"]')).to_have_text('안쪽 항목')
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('안쪽 항목')");p.reload();ed=self.note();expect(ed.locator('.li[data-depth="1"]')).to_have_text('안쪽 항목')

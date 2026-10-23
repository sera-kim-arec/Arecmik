"""Block controls follow the pointer without reviving on caret or scroll events."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class BlockToolsVisibilityTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    note=editors.BlockEditorTests.note
    patch=editors.BlockEditorTests.patch
    choose=editors.BlockEditorTests.choose

    def seed(self,html='<div>첫 문단</div><div>둘째 문단</div>'):
        self.patch('notes','work-n',{'html':html});return self.note()

    def test_leaving_a_focused_editor_hides_controls_even_after_typing_and_scroll(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').first.click();p.keyboard.press('End');expect(p.locator('.nb-tools')).to_be_visible();before=p.evaluate('JSON.stringify(__store)')
        p.mouse.move(8,100);expect(p.locator('.nb-tools')).to_have_count(0);expect(ed).to_be_focused();self.assertEqual(p.evaluate('JSON.stringify(__store)'),before)
        p.keyboard.insert_text(' 계속 작성');p.evaluate("window.dispatchEvent(new Event('scroll'));document.dispatchEvent(new Event('selectionchange'))");expect(p.locator('.nb-tools')).to_have_count(0);expect(ed.locator(':scope > div').first).to_have_text('첫 문단 계속 작성')
        ed.locator(':scope > div').last.hover();expect(p.locator('.nb-tools')).to_be_visible()

    def test_empty_editor_padding_hides_controls_and_hover_does_not_move_caret(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').first.click();p.keyboard.press('End');ed.locator(':scope > div').last.hover();expect(p.locator('.nb-tools')).to_be_visible();r=ed.bounding_box();p.mouse.move(r['x']+60,r['y']+r['height']-8);expect(p.locator('.nb-tools')).to_have_count(0)
        p.keyboard.insert_text(' 이어 쓰기');expect(ed.locator(':scope > div').first).to_have_text('첫 문단 이어 쓰기');expect(p.locator('.nb-tools')).to_have_count(0)

    def test_nested_gutter_bridge_keeps_the_same_controls_usable(self):
        p=self.page;ed=self.seed('<div>바깥 문단</div><div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">토글 제목</div><div class="nb-toggle-body"><div>안쪽 첫째</div><div>안쪽 둘째</div></div></div>');row=ed.locator('.nb-toggle-body > div').last;row.hover();handle=p.locator('[data-block-menu]');b=handle.bounding_box();r=row.bounding_box();panel=p.locator('.nb-tools').bounding_box()
        p.mouse.move((panel['x']+panel['width']+r['x'])/2,b['y']+b['height']/2,steps=12);p.wait_for_timeout(250);expect(handle).to_be_visible();self.assertAlmostEqual(handle.bounding_box()['y'],b['y'],delta=1)
        p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2,steps=8);handle.click();self.choose('아래에 문단 추가');p.keyboard.insert_text('새 안쪽 문단');expect(ed.locator('.nb-toggle-body > div')).to_have_text(['안쪽 첫째','안쪽 둘째','새 안쪽 문단'])

    def test_open_block_menu_remains_usable_when_controls_hide(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').last.hover();p.locator('[data-block-menu]').click();expect(p.locator('.nb-menu')).to_be_visible();p.mouse.move(8,100);expect(p.locator('.nb-tools')).to_have_count(0);expect(p.locator('.nb-menu')).to_be_visible();self.choose('복제');expect(ed.locator(':scope > div')).to_have_text(['첫 문단','둘째 문단','둘째 문단'])

    def test_selection_formatting_survives_leaving_the_block_controls(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').first.click();p.keyboard.press('Home');p.keyboard.press('Shift+End');expect(p.locator('.nb-inline')).to_be_visible();p.mouse.move(8,100);expect(p.locator('.nb-tools')).to_have_count(0);expect(p.locator('.nb-inline')).to_be_visible();p.locator('.nb-inline [data-mark="strong"]').click();expect(ed.locator('strong')).to_have_text('첫 문단')

    def test_leaving_browser_and_window_blur_do_not_leave_controls_behind(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').first.click();p.mouse.move(-10,-10);expect(p.locator('.nb-tools')).to_have_count(0);p.evaluate("window.dispatchEvent(new Event('scroll'))");expect(p.locator('.nb-tools')).to_have_count(0)
        ed.locator(':scope > div').last.hover();expect(p.locator('.nb-tools')).to_be_visible();p.evaluate("window.dispatchEvent(new Event('blur'));window.dispatchEvent(new Event('scroll'));document.dispatchEvent(new Event('selectionchange'))");expect(p.locator('.nb-tools')).to_have_count(0)

if __name__=='__main__':unittest.main()

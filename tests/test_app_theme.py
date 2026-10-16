"""App appearance persists locally without replacing editors or writing records."""
import unittest
from playwright.sync_api import expect
import test_archive as ui


class AppThemeTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown

    def setUp(self):
        ui.ArchiveTests.setUp(self)

    def open_themes(self):
        self.page.locator('[data-menu]').click()
        self.page.locator('[data-app-theme-open]').click()
        expect(self.page.get_by_role('radiogroup', name='앱 테마')).to_be_visible()

    def test_three_palettes_persist_through_reload_and_views_without_writes(self):
        original = self.page.evaluate('JSON.stringify(window.__store)')
        backgrounds = []
        for theme in ['lemon', 'mono', 'glass']:
            with self.subTest(theme=theme):
                self.open_themes()
                self.page.locator('[data-app-theme-choice="'+theme+'"]').click()
                expect(self.page.locator('html')).to_have_attribute('data-app-theme', theme)
                expect(self.page.locator('[data-app-theme-choice="'+theme+'"]')).to_have_attribute('aria-checked', 'true')
                self.page.get_by_role('button', name='이렇게 쓸게요').click()
                self.page.locator("nav [data-tab='home']").click()
                backgrounds.append(self.page.evaluate('getComputedStyle(document.body).background'))
                self.page.locator("nav [data-tab='proj']").click()
                self.page.locator('[data-open="work-p"]').click()
                expect(self.page.locator('[data-pmemo]')).to_contain_text('업무 프로젝트 메모')
                self.page.reload()
                expect(self.page.locator('html')).to_have_attribute('data-app-theme', theme)
                self.assertEqual(self.page.evaluate('localStorage.getItem("arecmik.app.theme")'), theme)
                self.assertEqual(self.page.evaluate('JSON.stringify(window.__store)'), original)
        self.assertEqual(len(set(backgrounds)), 3)
        self.assertEqual(self.page.evaluate('window.__writes||[]'), [])

    def test_switching_theme_keeps_editor_element_caret_and_unsaved_content(self):
        self.page.locator('[data-archive-open="mom"][data-id="work-m"]').click()
        editor = self.page.locator('#record-body')
        editor.fill('이 내용과 커서는 테마를 바꿔도 유지돼요')
        self.page.keyboard.press('End')
        before = self.page.evaluate("""() => {
          window.__editor=document.querySelector('#record-body');
          return {text:window.__editor.textContent,offset:getSelection().anchorOffset};
        }""")
        self.page.evaluate("window.ArecmikTheme.apply('lemon')")
        self.assertTrue(self.page.evaluate("document.querySelector('#record-body')===window.__editor"))
        self.assertEqual(self.page.evaluate('getSelection().anchorOffset'), before['offset'])
        expect(editor).to_have_text(before['text'])
        self.page.locator('[data-record-save]').click()
        self.page.wait_for_function("window.__store.moms.find(x=>x.id==='work-m').t.includes('커서는')")

    def test_mobile_keyboard_selection_and_invalid_saved_preference(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.evaluate("localStorage.setItem('arecmik.app.theme','unknown')")
        self.page.reload()
        expect(self.page.locator('html')).to_have_attribute('data-app-theme', 'glass')
        self.open_themes()
        self.page.locator('[data-app-theme-choice="glass"]').focus()
        self.page.keyboard.press('ArrowDown')
        expect(self.page.locator('html')).to_have_attribute('data-app-theme', 'lemon')
        self.page.keyboard.press('End')
        expect(self.page.locator('html')).to_have_attribute('data-app-theme', 'mono')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
        expect(self.page.get_by_role('button', name='이렇게 쓸게요')).to_be_in_viewport()


if __name__ == '__main__':
    unittest.main()

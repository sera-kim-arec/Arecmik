"""Multiple monthly/legacy documents must not resurrect or overwrite a day."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors

class JournalEditingIntegrityTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    patch=editors.BlockEditorTests.patch

    def seed(self,duplicates=False):
        self.patch('notes','month-a',{'title':'월 일지 A','space':'work','log':True,'mon':'2026-10','html':'<div class="h2 dayh">10/15 (목)</div><div>첫 날 원문</div><div class="h2 dayh">10/16 (금)</div><div>둘째 날 원문</div>'})
        if duplicates:
            self.patch('notes','month-b',{'title':'월 일지 B','space':'work','log':True,'mon':'2026-10','html':'<div class="h2 dayh">10/15 (목)</div><div>중복 날짜 원문</div><div class="h2 dayh">10/17 (토)</div><div>다른 문서의 보존할 날짜</div>'})
            self.patch('notes','legacy-day',{'title':'이전 일지','space':'work','log':True,'date':'2026-10-15','html':'<div>옛 날짜 원문</div>'})
        ui.record_source(self.page,'log');self.page.locator('[data-elog="2026-10-15"]').click()
        return self.page.locator('[data-log="2026-10-15"]')

    def test_deleting_a_duplicated_day_updates_monthly_and_legacy_copies(self):
        p=self.page;ed=self.seed(True);ed.click();p.keyboard.press('Control+a');p.keyboard.press('Backspace');p.locator('nav [data-tab="home"]').click()
        p.wait_for_function("!JSON.stringify(__store.notes).includes('중복 날짜 원문')&&!JSON.stringify(__store.notes).includes('옛 날짜 원문')&&!JSON.stringify(__store.notes).includes('첫 날 원문')")
        notes=p.evaluate("__store.notes.filter(n=>['month-a','month-b'].includes(n.id))");self.assertIn('둘째 날 원문',notes[0]['html']);self.assertIn('다른 문서의 보존할 날짜',notes[1]['html'])
        p.reload();p.locator('nav [data-tab="rec"]').click();ui.record_source(p,'log');expect(p.locator('[data-elog="2026-10-16"]')).to_have_text('둘째 날 원문')
        self.assertNotIn('중복 날짜 원문',p.locator('#main').inner_text());self.assertNotIn('첫 날 원문',p.locator('#main').inner_text());self.assertNotIn('옛 날짜 원문',p.locator('#main').inner_text())

    def test_failed_delete_is_atomic_and_retains_originals_and_local_recovery(self):
        p=self.page;ed=self.seed(True);before=p.evaluate("__store.notes.filter(n=>['month-a','month-b','legacy-day'].includes(n.id))")
        p.evaluate('window.__failWrites=true');ed.click();p.keyboard.press('Control+a');p.keyboard.press('Backspace');p.locator('nav [data-tab="home"]').click();expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집')
        self.assertEqual(p.evaluate("__store.notes.filter(n=>['month-a','month-b','legacy-day'].includes(n.id))"),before)
        expect(p.locator('[data-local-recovery]')).to_be_visible()

    def test_two_quick_edits_in_one_month_keep_both_days(self):
        p=self.page;ed=self.seed();p.evaluate('window.__writeDelayMs=350')
        ed.click();p.keyboard.press('Control+a');p.keyboard.insert_text('첫 날 수정 내용');p.locator('[data-elog="2026-10-16"]').click()
        second=p.locator('[data-log="2026-10-16"]');second.click();p.keyboard.press('Control+a');p.keyboard.insert_text('둘째 날 수정 내용');p.locator('nav [data-tab="home"]').click()
        p.wait_for_function("__store.notes.find(n=>n.id==='month-a').html.includes('첫 날 수정 내용')&&__store.notes.find(n=>n.id==='month-a').html.includes('둘째 날 수정 내용')")
        p.reload();p.locator('nav [data-tab="rec"]').click();ui.record_source(p,'log');expect(p.locator('[data-elog="2026-10-15"]')).to_have_text('첫 날 수정 내용');expect(p.locator('[data-elog="2026-10-16"]')).to_have_text('둘째 날 수정 내용')

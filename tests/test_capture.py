"""Low effort writing preserves the existing drafts, space and original data."""
import unittest
from playwright.sync_api import expect
import test_archive as ui


class CaptureTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown

    def test_visible_home_entry_keeps_failed_draft_and_retries_once_without_creating_record(self):
        p=self.page;p.set_viewport_size({'width':390,'height':844})
        p.locator('nav [data-tab="home"]').click()
        fold=p.locator('[data-layout-fold="undated"]')
        if fold.get_attribute('open') is not None:fold.locator('summary').click()
        expect(p.locator('[data-layout-fold="undated"]')).not_to_have_attribute('open','')
        expect(p.locator('#udi')).to_be_visible()
        p.locator('#udi').fill('먼저 한 줄로 적어 둔 업무')
        p.evaluate('window.__failWrites=true')
        p.locator('[data-layout-add-task]').click()
        expect(p.locator('.toast')).to_contain_text('입력 내용을 유지')
        expect(p.locator('#udi')).to_have_value('먼저 한 줄로 적어 둔 업무')
        p.reload();expect(p.locator('#udi')).to_have_value('먼저 한 줄로 적어 둔 업무')
        p.evaluate('window.__writeDelayMs=300')
        p.locator('[data-layout-add-task]').evaluate('button=>{button.click();button.click()}')
        p.wait_for_function("window.__store.todos.some(t=>t.title==='먼저 한 줄로 적어 둔 업무')")
        expect(p.locator('#udi')).to_have_value('')
        rows=p.evaluate("window.__store.todos.filter(t=>t.title==='먼저 한 줄로 적어 둔 업무')")
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['space'],rows[0]['date'],rows[0]['projectId']),('work','',''))
        self.assertEqual(p.evaluate('window.__store.moms.length'),len(ui.SEED['moms']))
        p.locator('[data-sp="life"]').click();p.locator('#udi').fill('개인 할 일 임시 입력')
        p.locator('[data-sp="work"]').click();expect(p.locator('#udi')).to_have_value('')
        p.locator('[data-sp="life"]').click();expect(p.locator('#udi')).to_have_value('개인 할 일 임시 입력')

    def test_one_click_record_opens_at_body_and_saves_a_single_line_with_default_context(self):
        p=self.page;p.locator('.layout-write-group>[data-record-new]').click()
        expect(p.locator('#record-body')).to_be_focused()
        expect(p.locator('#record-project')).to_have_value('')
        day=p.locator('#record-day').input_value()
        p.keyboard.insert_text('오늘 기억하고 싶은 한 줄')
        p.locator('[data-record-save]').click()
        expect(p.locator('.archive-list')).to_contain_text('오늘 기억하고 싶은 한 줄')
        saved=p.evaluate("window.__store.moms.filter(m=>m.t==='오늘 기억하고 싶은 한 줄')")
        self.assertEqual(len(saved),1)
        self.assertEqual((saved[0]['space'],saved[0]['d'],saved[0]['pid']),('work',day,''))
        p.locator('.archive-list [data-id="'+saved[0]['id']+'"][data-archive-open]').click()
        expect(p.locator('#record-body')).to_have_text('오늘 기억하고 싶은 한 줄')
        expect(p.locator('#record-day')).to_have_value(day)

    def test_grouped_records_omit_duplicate_dates_but_search_retains_date_context(self):
        p=self.page
        expect(p.locator('.archive-day')).to_contain_text(['2026. 10. 15'])
        expect(p.locator('[data-archive-open="mom"][data-id="work-m"] .archive-context')).not_to_contain_text('2026-10-15')
        p.locator('[data-search]').click();p.locator('#sqi').fill('업무 회의 회고')
        expect(p.locator('#sqr [data-sgo="mom"] .archive-context')).to_contain_text('2026-10-15')

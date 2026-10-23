"""Task detail layout preserves drafts, hidden settings and subtask edits."""
import unittest

from playwright.sync_api import expect
import test_archive as ui


class TaskDetailTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown

    def open_task(self):
        ui.archive_filter(self.page,'todo')
        self.page.locator('#rq').fill('보고서 제출')
        self.page.locator('[data-archive-open="todo"]').click()
        expect(self.page.locator('#sheet.task-sheet textarea#e-t')).to_be_visible()

    def test_primary_fields_visible_and_optional_settings_save_when_folded(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.open_task()
        for selector in ['#e-d', '#e-h', '#e-p', '#e-n', '[data-memo-photo="e-n"]']:
            expect(self.page.locator(selector)).to_be_visible()
        expect(self.page.locator('#e-e')).to_be_hidden()
        expect(self.page.locator('#e-sadd')).to_be_hidden()
        expect(self.page.locator('#sheet [data-conn-record]')).to_be_hidden()
        self.page.locator('[data-task-options]>summary').click()
        self.page.locator('#e-d').fill('2026-10-21')
        self.page.locator('#e-e').fill('2026-10-23')
        self.page.locator('#e-l').fill('서울 사무실')
        self.page.locator('#e-k').fill('https://example.com/report')
        self.page.locator('[data-task-options]>summary').click()
        expect(self.page.locator('[data-task-options]>summary')).to_contain_text('서울 사무실')
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').end==='2026-10-23'")
        self.open_task()
        expect(self.page.locator('#e-e')).to_be_visible()
        expect(self.page.locator('#e-l')).to_have_value('서울 사무실')
        expect(self.page.locator('#e-k')).to_have_value('https://example.com/report')
        self.assertLessEqual(self.page.locator('#sheet').evaluate('e=>e.scrollWidth'), self.page.locator('#sheet').evaluate('e=>e.clientWidth'))

    def test_long_title_and_custom_repeat_draft_survive_reload(self):
        self.open_task()
        title = '[오퍼] 창원상온FC_IB 주간 스텝 이동환 근무 일정과 확인 사항'
        self.page.locator('#e-t').fill(title)
        self.page.set_viewport_size({'width': 390, 'height': 844})
        expect(self.page.locator('#e-t')).to_have_value(title)
        self.page.wait_for_function("document.querySelector('#e-t').clientHeight >= document.querySelector('#e-t').scrollHeight")
        self.page.locator('#e-d').fill('2026-10-21')
        self.page.locator('[data-task-options]>summary').click()
        self.page.locator('#e-r').select_option('c')
        self.page.locator('#e-rn').fill('2')
        self.page.locator('#e-ru').select_option('m')
        self.page.locator('#sheet [data-sx="0"]').click()
        self.page.reload()
        self.open_task()
        expect(self.page.locator('#e-t')).to_have_value(title)
        expect(self.page.locator('#e-rn')).to_be_visible()
        expect(self.page.locator('#e-rn')).to_have_value('2')
        expect(self.page.locator('#e-ru')).to_have_value('m')
        expect(self.page.locator('#e-rw')).to_be_hidden()
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').title"), '보고서 제출')
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').rep==='c'")
        saved = self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t')")
        self.assertEqual((saved['title'], saved['repN'], saved['repU']), (title, 2, 'm'))

    def test_invalid_end_date_opens_fold_and_keeps_saved_data(self):
        self.open_task()
        self.page.locator('#e-d').fill('2026-10-21')
        self.page.locator('[data-task-options]>summary').click()
        self.page.locator('#e-e').fill('2026-10-20')
        self.page.locator('[data-task-options]>summary').click()
        self.page.locator('[data-esave]').click()
        expect(self.page.locator('#e-e')).to_be_visible()
        expect(self.page.locator('#e-e')).to_be_focused()
        expect(self.page.locator('#e-e-error')).to_contain_text('끝 날짜')
        self.assertFalse(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').end"))
        self.page.locator('#e-e').fill('2026-10-23')
        expect(self.page.locator('#e-e-error')).to_have_count(0)
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').end==='2026-10-23'")

    def test_subtask_completion_and_draft_survive_collapsing(self):
        self.open_task()
        self.page.locator('[data-task-subtasks]>summary').click()
        self.page.locator('#e-sadd').fill('자료 확인')
        self.page.locator('#e-sadd').press('Enter')
        self.page.locator('[data-esub="0"]').click()
        self.page.locator('[data-task-subtasks]>summary').click()
        expect(self.page.locator('[data-task-subtasks]>summary')).to_contain_text('1개')
        self.page.locator('#sheet [data-sx="0"]').click()
        self.open_task()
        expect(self.page.locator('[data-esubt="0"]')).to_be_visible()
        expect(self.page.locator('[data-esubt="0"]')).to_have_value('자료 확인')
        expect(self.page.locator('[data-esub="0"]')).to_have_class('ck on')
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').subs?.length===1")
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').subs[0]"), {'t': '자료 확인', 'done': True})


if __name__ == '__main__':
    unittest.main()

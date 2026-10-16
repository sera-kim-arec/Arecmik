"""Date-only events stay events when created, edited, and reloaded."""
import unittest

from playwright.sync_api import expect
import test_archive as ui


class OptionalEventTimeTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown

    def calendar(self):
        self.page.locator("nav [data-tab='home']").click()
        self.page.locator('[data-cv="m"]').click()
        if self.page.viewport_size['width'] <= 900:
            self.page.locator('[data-pick="2026-10-20"]').click()
            if not self.page.locator('.qa').count():
                self.page.locator('[data-day-add="2026-10-20"]').click()
        else:
            self.page.locator('[data-cadd2="2026-10-20"]').click()
        self.page.locator('[data-qt="ev"]').click()

    def saved(self, title):
        self.page.wait_for_function('(title)=>window.__store.todos.some(t=>t.title===title)', arg=title)
        return self.page.evaluate('(title)=>window.__store.todos.find(t=>t.title===title)', title)

    def open_event(self, row):
        if not self.page.locator('#srch.on').count():
            self.page.locator('[data-search]').click()
        self.page.locator('#sqi').fill(row['title'])
        self.page.locator('#sqr [data-sgo="todo"]').click()
        expect(self.page.locator('#e-kind')).to_have_value('event')

    def test_calendar_date_only_event_survives_edit_reload_and_mobile(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.calendar()
        expect(self.page.locator('#qah')).to_have_value('')
        self.page.locator('#qat').fill('휴가')
        self.page.locator('[data-qasave]').click()
        row = self.saved('휴가')
        self.assertEqual((row['kind'], row['time'], row['date']), ('event', '', '2026-10-20'))
        expect(self.page.locator('[data-drag="'+row['id']+'"]').first).to_contain_text('종일')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
        self.open_event(row)
        expect(self.page.locator('#e-h')).to_have_value('')
        self.page.locator('#e-t').fill('휴가 변경')
        self.page.locator('[data-esave]').click()
        self.page.reload()
        row = self.saved('휴가 변경')
        self.assertEqual((row['kind'], row['time']), ('event', ''))
        self.open_event(row)
        expect(self.page.locator('#e-h')).to_have_value('')

    def test_removing_existing_time_keeps_event_and_explicit_task_conversion_works(self):
        self.calendar()
        self.page.locator('#qat').fill('진료 예약')
        self.page.locator('#qah').fill('14:30')
        self.page.locator('[data-qasave]').click()
        row = self.saved('진료 예약')
        self.open_event(row)
        self.page.locator('[data-etclr]').click()
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function('(id)=>window.__store.todos.find(t=>t.id===id).time===""', arg=row['id'])
        row = self.saved('진료 예약')
        self.assertEqual(row['kind'], 'event')
        self.open_event(row)
        self.page.locator('#e-h').fill('11:00')
        self.page.locator('#e-kind').select_option('todo')
        expect(self.page.locator('#e-h')).to_have_value('')
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function('(id)=>window.__store.todos.find(t=>t.id===id).kind==="todo"', arg=row['id'])
        self.assertEqual(self.saved('진료 예약')['time'], '')

    def test_time_can_be_added_to_a_date_only_event(self):
        self.calendar()
        self.page.locator('#qat').fill('약속')
        self.page.locator('[data-qasave]').click()
        row = self.saved('약속')
        self.open_event(row)
        self.page.locator('#e-h').fill('18:00')
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function('(id)=>window.__store.todos.find(t=>t.id===id).time==="18:00"', arg=row['id'])
        self.assertEqual(self.saved('약속')['kind'], 'event')

    def test_project_date_only_event_and_calendar_plain_task_remain_distinct(self):
        self.page.locator("nav [data-tab='proj']").click()
        self.page.locator('[data-open="work-p"]').click()
        self.page.locator('[data-pqk="e"]').click()
        self.page.locator('[data-pqd]').fill('2026-10-21')
        self.page.locator('#pq-t').fill('출장')
        self.page.locator('#pq-t').press('Enter')
        row = self.saved('출장')
        self.assertEqual((row['kind'], row['time'], row['date'], row['projectId']), ('event', '', '2026-10-21', 'work-p'))
        self.calendar()
        self.page.locator('[data-qt="todo"]').click()
        self.page.locator('#qat').fill('자료 준비')
        self.page.locator('[data-qasave]').click()
        row = self.saved('자료 준비')
        self.assertEqual((row['kind'], row['time']), ('todo', ''))

    def test_cleared_calendar_time_does_not_return_after_expanding_options(self):
        self.calendar()
        self.page.locator('#qat').fill('기념일')
        self.page.locator('#qah').fill('09:00')
        self.page.locator('[data-qtclear]').click()
        self.page.locator('[data-qmore]').click()
        expect(self.page.locator('#qah')).to_have_value('')
        self.page.locator('[data-qasave]').click()
        row = self.saved('기념일')
        self.assertEqual((row['kind'], row['time']), ('event', ''))

    def test_clear_time_overrides_time_in_title_and_explicit_time_can_be_restored(self):
        self.calendar()
        self.page.locator('#qat').fill('3시 상담')
        self.page.locator('[data-qtclear]').click()
        self.page.locator('[data-qasave]').click()
        row = self.saved('상담')
        self.assertEqual((row['kind'], row['time']), ('event', ''))
        self.calendar()
        self.page.locator('#qat').fill('설명회')
        self.page.locator('[data-qtclear]').click()
        self.page.locator('#qah').fill('16:00')
        self.page.locator('[data-qasave]').click()
        row = self.saved('설명회')
        self.assertEqual((row['kind'], row['time']), ('event', '16:00'))


if __name__ == '__main__':
    unittest.main()

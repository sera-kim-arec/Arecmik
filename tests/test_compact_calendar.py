"""Busy days stay small in the month and retain a complete, usable day list."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_workspace as workspace


class CompactCalendarTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    patch=workspace.WorkspaceTests.patch
    today=workspace.WorkspaceTests.today

    def busy_day(self):
        day=self.today()
        for i in range(10):
            self.patch('todos','busy-'+str(i),{'title':'자세한 제목을 그대로 열어 확인할 일정 '+str(i),'space':'work','date':day,'time':f'{9+i:02}:00' if i<5 else '', 'kind':'event' if i<5 else 'todo','done':False})
        p=self.page;p.locator('nav [data-tab="home"]').click();p.locator('[data-cv="m"]').click()
        return p.locator('.mc[data-pick="'+day+'"]')

    def test_busy_selected_month_day_is_bounded_and_more_opens_every_original_item(self):
        p=self.page;p.set_viewport_size({'width':1365,'height':1000});cell=self.busy_day();before=p.evaluate('JSON.stringify(__store)')
        expect(cell.locator('i[data-drag]')).to_have_count(3);expect(cell.locator('[data-day-more]')).to_have_text('+7개 더');self.assertLess(p.locator('.mg').bounding_box()['height'],650)
        cell.locator('[data-day-more]').click();expect(p.locator('.dside .it')).to_have_count(10);expect(p.locator('.qa')).to_have_count(0);expect(p.locator('.dside')).to_be_focused();self.assertEqual(p.evaluate('JSON.stringify(__store)'),before)
        p.locator('.dside [data-edit="busy-9"]').click();expect(p.locator('#e-t')).to_have_value('자세한 제목을 그대로 열어 확인할 일정 9')
        p.locator('[data-esave]').click();p.locator('.dside [data-ck="busy-9"]').click();p.wait_for_function("__store.todos.find(t=>t.id==='busy-9').done===true")
        p.reload();expect(p.locator('.dside .it')).to_have_count(10);expect(p.locator('.dside .it[data-drag="busy-9"]')).to_have_class('it dn')

    def test_phone_keeps_complete_day_list_and_large_completion_targets(self):
        p=self.page;p.set_viewport_size({'width':390,'height':844});cell=self.busy_day();expect(cell.locator('.month-item-count')).to_have_text('10개');expect(cell.locator('[data-day-more]')).to_be_hidden();expect(p.locator('.dside .it')).to_have_count(10)
        for width in [320,390,768]:
            p.set_viewport_size({'width':width,'height':900});self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
            for target in p.locator('.dside [data-ck]').all():
                r=target.bounding_box();self.assertGreaterEqual(r['width'],44);self.assertGreaterEqual(r['height'],44)
        p.locator('.dside [data-ck="busy-9"]').click();p.wait_for_function("__store.todos.find(t=>t.id==='busy-9').done===true")

    def test_empty_week_uses_less_height_and_retains_date_entry(self):
        p=self.page;p.set_viewport_size({'width':1365,'height':1000});p.locator('nav [data-tab="home"]').click();p.locator('[data-cv="3"]').click();before=p.evaluate('JSON.stringify(__store)')
        for row in p.locator('.wc').all():self.assertLess(row.bounding_box()['height'],120)
        p.locator('.wc').last.locator('[data-cadd2]').click();expect(p.locator('#qat')).to_be_focused();self.assertEqual(p.evaluate('JSON.stringify(__store)'),before);p.locator('#qat').fill('촘촘해진 화면에서도 일정 추가');p.locator('[data-qasave]').click();p.wait_for_function("__store.todos.some(t=>t.title==='촘촘해진 화면에서도 일정 추가')")

if __name__=='__main__':unittest.main()

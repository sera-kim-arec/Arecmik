"""Select inclusive calendar ranges without breaking clicks or moving events."""
import unittest

from playwright.sync_api import expect
import test_archive as ui


class CalendarRangeTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        self.page.set_viewport_size({'width': 1280, 'height': 1250})
        self.page.locator("nav [data-tab='home']").click()
        self.page.locator('[data-cv="m"]').click()

    def point(self, day):
        rect = self.page.locator('[data-pick="'+day+'"]').bounding_box()
        return {'x': rect['x']+rect['width']/2, 'y': rect['y']+rect['height']-14}

    def drag(self, start, end, release=True):
        a, b = self.point(start), self.point(end)
        self.page.mouse.move(**a)
        self.page.mouse.down()
        self.page.mouse.move(**b, steps=12)
        if release:
            self.page.mouse.up()

    def save(self, title):
        self.page.locator('#qat').fill(title)
        self.page.locator('[data-qasave]').click()
        self.page.wait_for_function('(t)=>window.__store.todos.some(x=>x.title===t)', arg=title)
        return self.page.evaluate('(t)=>window.__store.todos.find(x=>x.title===t)', title)

    def test_mouse_range_highlights_and_saves_one_inclusive_date_only_event(self):
        self.drag('2026-10-20', '2026-10-23', release=False)
        expect(self.page.locator('.range-selected')).to_have_count(4)
        expect(self.page.locator('#cal-range-status')).to_contain_text('4일')
        self.assertEqual(self.page.evaluate('window.__store.todos.length'), len(ui.SEED['todos']))
        self.page.mouse.up()
        expect(self.page.locator('#qad-start')).to_have_value('2026-10-20')
        expect(self.page.locator('#qad-end')).to_have_value('2026-10-23')
        expect(self.page.locator('[data-qt="ev"]')).to_have_class('on')
        expect(self.page.locator('#qah')).to_have_value('')
        row = self.save('제주 여행')
        self.assertEqual((row['date'], row['end'], row['kind'], row['time']), ('2026-10-20', '2026-10-23', 'event', ''))
        self.assertEqual(self.page.evaluate('window.__store.todos.length'), len(ui.SEED['todos'])+1)
        for day in ['20', '21', '22', '23']:
            expect(self.page.locator('[data-pick="2026-10-'+day+'"] [data-drag="'+row['id']+'"]').first).to_be_visible()
        expect(self.page.locator('[data-pick="2026-10-24"] [data-drag="'+row['id']+'"]')).to_have_count(0)

    def test_reverse_cross_row_and_month_boundary_ranges_normalize_dates(self):
        for start, end in [('2026-10-26', '2026-10-23'), ('2026-10-02', '2026-09-30')]:
            with self.subTest(start=start, end=end):
                self.drag(start, end)
                expect(self.page.locator('#qad-start')).to_have_value(end)
                expect(self.page.locator('#qad-end')).to_have_value(start)
                self.page.locator('[data-qax]').click()
        self.assertEqual(self.page.evaluate('window.__store.todos.length'), len(ui.SEED['todos']))

    def test_escape_and_release_outside_cancel_without_writing(self):
        self.drag('2026-10-20', '2026-10-22', release=False)
        self.page.keyboard.press('Escape')
        self.page.mouse.up()
        expect(self.page.locator('.qa')).to_have_count(0)
        expect(self.page.locator('.range-selected')).to_have_count(0)
        self.drag('2026-10-20', '2026-10-22', release=False)
        self.page.mouse.move(10, 10)
        self.page.mouse.up()
        expect(self.page.locator('.qa')).to_have_count(0)
        self.assertEqual(self.page.evaluate('window.__store.todos.length'), len(ui.SEED['todos']))

    def test_click_and_plus_still_add_single_day_without_stale_range(self):
        self.page.mouse.click(**self.point('2026-10-20'))
        expect(self.page.locator('.qa')).to_have_count(0)
        self.drag('2026-10-20', '2026-10-22')
        self.page.locator('[data-qax]').click()
        # Wait for the post-drag compatibility click guard to expire.
        self.page.wait_for_timeout(720)
        self.page.locator('[data-cadd2="2026-10-25"]').click()
        expect(self.page.locator('#qad-start')).to_have_value('2026-10-25')
        expect(self.page.locator('#qad-end')).to_have_value('')

    def test_failure_keeps_title_range_and_project_for_retry_and_blocks_duplicates(self):
        self.drag('2026-10-20', '2026-10-22')
        self.page.locator('#qat').fill('팀 워크숍')
        self.page.locator('[data-qdd]').click()
        self.page.locator('[data-qp="work-p"]').click()
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-qasave]').click()
        expect(self.page.locator('.toast')).to_contain_text('선택한 기간을 유지')
        expect(self.page.locator('#qat')).to_have_value('팀 워크숍')
        expect(self.page.locator('#qad-end')).to_have_value('2026-10-22')
        expect(self.page.locator('[data-qdd]')).to_contain_text('업무 프로젝트')
        self.assertEqual(self.page.evaluate('window.__store.todos.length'), len(ui.SEED['todos']))
        self.page.evaluate('window.__failWrites=false;window.__writeDelayMs=500')
        self.page.locator('[data-qasave]').click()
        expect(self.page.locator('[data-qasave]')).to_be_disabled()
        self.page.keyboard.press('Enter')
        self.page.keyboard.press('Escape')
        self.page.wait_for_function("window.__store.todos.some(t=>t.title==='팀 워크숍')")
        self.assertEqual(self.page.evaluate("window.__store.todos.filter(t=>t.title==='팀 워크숍').length"), 1)
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.title==='팀 워크숍').projectId"), 'work-p')

    def test_manual_range_edits_validation_and_more_options_preserve_dates(self):
        self.drag('2026-10-20', '2026-10-22')
        self.page.locator('#qat').fill('가족 여행')
        self.page.locator('#qad-end').fill('2026-10-19')
        self.page.locator('[data-qasave]').click()
        expect(self.page.locator('.toast')).to_contain_text('끝 날짜는 시작 날짜')
        self.page.locator('#qad-start').fill('2026-10-19')
        self.page.locator('#qad-end').fill('2026-10-24')
        self.page.locator('[data-qmore]').click()
        self.page.locator('[data-qm="note"]').fill('숙소 예약 완료')
        self.page.locator('[data-qmore]').click()
        expect(self.page.locator('#qad-start')).to_have_value('2026-10-19')
        expect(self.page.locator('#qad-end')).to_have_value('2026-10-24')
        row = self.save('가족 여행')
        self.assertEqual((row['date'], row['end'], row['note']), ('2026-10-19', '2026-10-24', '숙소 예약 완료'))

    def test_existing_event_drag_moves_dates_and_preserves_duration(self):
        self.drag('2026-10-20', '2026-10-22')
        row = self.save('이동할 여행')
        source = self.page.locator('[data-pick="2026-10-20"] [data-drag="'+row['id']+'"]')
        target = self.page.locator('[data-pick="2026-10-24"]')
        source.drag_to(target)
        self.page.wait_for_function('(id)=>window.__store.todos.find(t=>t.id===id).date==="2026-10-24"', arg=row['id'])
        self.assertEqual(self.page.evaluate('(id)=>window.__store.todos.find(t=>t.id===id).end', row['id']), '2026-10-26')
        expect(self.page.locator('.qa')).to_have_count(0)

    def test_week_grid_range_also_opens_event_editor(self):
        self.page.locator('[data-cv="7"]').click()
        days = self.page.locator('.wc[data-pick]').evaluate_all('(els)=>els.map(el=>el.dataset.pick)')
        self.drag(days[0], days[2])
        expect(self.page.locator('#qad-start')).to_have_value(days[0])
        expect(self.page.locator('#qad-end')).to_have_value(days[2])

    def test_realtime_updates_do_not_interrupt_selection_or_reset_editor(self):
        self.drag('2026-10-20', '2026-10-22', release=False)
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await m.addDoc(m.collection({},'refs'),{title:'다른 기기의 변경',space:'work'});
        }""")
        self.page.wait_for_timeout(50)
        expect(self.page.locator('.range-selected')).to_have_count(3)
        self.page.mouse.up()
        self.page.locator('#qat').fill('전송 중에도 유지할 제목')
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await m.addDoc(m.collection({},'refs'),{title:'추가 동기화',space:'work'});
        }""")
        self.page.wait_for_timeout(50)
        expect(self.page.locator('#qat')).to_have_value('전송 중에도 유지할 제목')
        expect(self.page.locator('#qad-end')).to_have_value('2026-10-22')

    def test_mobile_long_press_selects_range_and_swipe_remains_scrollable(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        session = self.context.new_cdp_session(self.page)
        session.send('Emulation.setTouchEmulationEnabled', {'enabled': True})
        self.page.locator('[data-pick="2026-10-20"]').scroll_into_view_if_needed()
        a, b = self.point('2026-10-20'), self.point('2026-10-22')
        def touch(kind, point=None):
            session.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [{**point, 'id': 1}] if point else []})
        touch('touchStart', a)
        self.page.wait_for_timeout(480)
        expect(self.page.locator('#cal-range-status')).to_be_visible()
        touch('touchMove', b)
        touch('touchEnd')
        expect(self.page.locator('#qad-start')).to_have_value('2026-10-20')
        expect(self.page.locator('#qad-end')).to_have_value('2026-10-22')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
        self.page.locator('[data-qax]').click()
        self.page.wait_for_timeout(720)
        self.page.locator('[data-pick="2026-10-13"]').scroll_into_view_if_needed()
        a = self.point('2026-10-13')
        before = self.page.evaluate('scrollY')
        touch('touchStart', a)
        for step in range(1, 7):
            touch('touchMove', {**a, 'y': a['y']-step*20})
        touch('touchEnd')
        self.page.wait_for_function('(n)=>scrollY>n', arg=before)
        expect(self.page.locator('.qa')).to_have_count(0)
        expect(self.page.locator('.range-selected')).to_have_count(0)


if __name__ == '__main__':
    unittest.main()

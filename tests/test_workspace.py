"""Desktop retrieval and pending work use the original records and editors."""
import unittest
from playwright.sync_api import expect
import test_archive as ui


class WorkspaceTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown

    def patch(self, collection, ident, fields):
        self.page.evaluate("""async ([c,id,data])=>{
          const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await f.setDoc(f.doc(f.collection({},c),id),data,{merge:true});
        }""", [collection, ident, fields])

    def today(self):
        return self.page.evaluate("()=>{const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')}")

    def test_pc_pending_work_is_beside_calendar_and_clicking_title_opens_details(self):
        self.patch('todos','work-late',{'title':'밀린 업무를 놓치지 않기','space':'work','date':'2020-01-01','done':False})
        self.patch('todos','work-today',{'title':'오늘 반드시 확인할 업무','space':'work','date':self.today(),'done':False})
        p=self.page;p.set_viewport_size({'width':1365,'height':1000})
        before=p.evaluate('JSON.stringify(window.__store)')
        p.locator('nav [data-tab="home"]').click()
        expect(p.locator('.dcol .undbox [data-edit="work-t"]')).to_be_visible()
        expect(p.locator('[data-layout-focus="today"]')).to_contain_text('1')
        expect(p.locator('[data-layout-focus="late"]')).to_contain_text('1')
        self.assertGreater(p.locator('.undbox').bounding_box()['x'],p.locator('.cmain').bounding_box()['x'])
        p.locator('[data-layout-fold="undated"]>summary').click()
        p.locator('[data-layout-focus="late"]').click()
        expect(p.locator('[data-layout-fold="undated"]')).to_have_attribute('open','')
        p.locator('[data-ie="todos|work-late|title"]').click()
        expect(p.locator('#e-t')).to_have_value('밀린 업무를 놓치지 않기')
        expect(p.locator('.ieon')).to_have_count(0)
        p.go_back()
        p.locator('.ch [data-cm="-1"]').click();p.locator('[data-layout-focus="today"]').click()
        expect(p.locator('.dside')).to_contain_text('오늘 반드시 확인할 업무')
        p.locator('.dside [data-edit="work-today"]').focus()
        p.keyboard.press('Enter')
        expect(p.locator('#e-t')).to_have_value('오늘 반드시 확인할 업무')
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

    def test_pc_search_shortcut_finds_task_memo_and_back_restores_search(self):
        p=self.page;p.set_viewport_size({'width':1365,'height':900})
        expect(p.locator('.layout-search-label')).to_be_visible()
        p.keyboard.press('Control+k');expect(p.locator('#sqi')).to_be_focused()
        p.locator('#sqi').fill('검토 의견');p.keyboard.press('Enter')
        expect(p.locator('#e-n')).to_contain_text('검토 의견')
        p.go_back();expect(p.locator('#sqi')).to_have_value('검토 의견')
        expect(p.locator('#sqr [data-sgo="todo"]')).to_have_count(1)
        p.keyboard.press('Escape');expect(p.locator('#srch')).not_to_have_class('srov on')
        p.set_viewport_size({'width':390,'height':844})
        expect(p.locator('.layout-search-label')).not_to_be_visible()
        expect(p.locator('[data-search]')).to_be_visible()

    def test_work_month_keeps_tasks_beside_calendar_in_narrow_pc_and_ignores_old_panel_height(self):
        p=self.page
        self.patch('todos','work-month-event',{'title':'월 달력에서 확인할 업무 일정','space':'work','kind':'event','date':self.today()})
        p.evaluate("localStorage.setItem('rz_dsh','1200')")
        p.reload();p.locator('nav [data-tab="home"]').click()
        before=p.evaluate('JSON.stringify(window.__store)')
        for width in [1365,1024,901,900,800,760]:
            with self.subTest(width=width):
                p.set_viewport_size({'width':width,'height':1000})
                p.evaluate('scrollTo(0,0)')
                calendar=p.locator('.mg').bounding_box();day=p.locator('.dside').bounding_box()
                pending=p.locator('[data-layout-fold="undated"]').bounding_box()
                self.assertGreater(day['x'],calendar['x']+calendar['width'])
                self.assertAlmostEqual(day['y'],calendar['y'],delta=1)
                self.assertAlmostEqual(pending['x'],day['x'],delta=1)
                self.assertLess(day['height'],500)
                event=p.locator('.mc [data-drag="work-month-event"]')
                self.assertGreaterEqual(event.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)'),11)
                self.assertGreater(event.bounding_box()['height'],10)
                self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
        p.locator('.dside [data-edit="work-month-event"]').click()
        expect(p.locator('#e-t')).to_have_value('월 달력에서 확인할 업무 일정')
        p.go_back()
        p.locator('[data-sp="life"]').click()
        expect(p.locator('.layout-work-home')).to_have_count(0)
        p.locator('[data-sp="work"]').click()
        expect(p.locator('.layout-work-home')).to_have_count(1)
        self.assertEqual(p.evaluate('localStorage.getItem("rz_dsh")'),'1200')
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

    def test_work_month_keeps_single_column_on_phone_and_touch_tablet(self):
        p=self.page;p.locator('nav [data-tab="home"]').click()
        before=p.evaluate('JSON.stringify(window.__store)')
        def assert_stacked(width):
            p.set_viewport_size({'width':width,'height':1000})
            p.evaluate('scrollTo(0,0)')
            boxes=[p.locator(s).bounding_box() for s in ['.mg','.dside','[data-layout-fold="undated"]','[data-layout-fold="journal"]']]
            for above,below in zip(boxes,boxes[1:]):
                self.assertGreaterEqual(below['y'],above['y']+above['height'])
                self.assertAlmostEqual(below['x'],above['x'],delta=1)
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
        for width in [320,390,759]:
            assert_stacked(width)
        cdp=self.context.new_cdp_session(p)
        cdp.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':5})
        self.assertTrue(p.evaluate('matchMedia("(pointer:coarse)").matches'))
        for width in [768,900]:
            assert_stacked(width)
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

    def test_record_feed_is_written_content_and_sources_are_explicit_and_searchable(self):
        p=self.page;before=p.evaluate('JSON.stringify(window.__store)')
        expect(p.locator('.archive-list')).to_contain_text('업무 회의 회고')
        expect(p.locator('.archive-list [data-archive-open="ref"],.archive-list [data-archive-open="expense"],.archive-list [data-archive-open="todo"]')).to_have_count(0)
        p.locator('[data-archive-filter="ref"]').click()
        expect(p.locator('.archive-list')).to_contain_text('기존 자료')
        expect(p.locator('[data-archive-filter="expense"]')).to_have_count(0)
        p.locator('[data-archive-filter=""]').click();p.locator('#rq').fill('업무 도서')
        expect(p.locator('.archive-list')).to_contain_text('업무 도서')
        p.locator('#rq').fill('팀 연락처')
        expect(p.locator('.archive-list [data-archive-open="ref"]')).to_have_count(1)
        p.locator('#rq').fill('')
        expect(p.locator('.archive-list [data-archive-open="ref"]')).to_have_count(0)
        p.locator('[data-sp="life"]').click()
        expect(p.locator('.archive-list')).to_contain_text('즐거웠던 하루')
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(0)
        p.locator('[data-archive-filter="todo"]').click()
        expect(p.locator('.archive-list')).to_contain_text('숙소 예약')
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

    def test_all_record_types_are_visible_without_horizontal_scrolling_on_phone(self):
        p=self.page
        for width in [320,390,768]:
            p.set_viewport_size({'width':width,'height':844})
            types=p.locator('.layout-record-types')
            self.assertTrue(types.evaluate('el=>el.scrollWidth<=el.clientWidth'))
            for button in types.locator('button').all():
                box=button.bounding_box()
                self.assertGreaterEqual(box['height'],44)
                self.assertGreaterEqual(box['x'],0)
                self.assertLessEqual(box['x']+box['width'],width)
            p.locator('[data-archive-filter="ref"]').click()
            expect(p.locator('.archive-list')).to_contain_text('업무 자료')
            p.locator('[data-archive-filter=""]').click()
        p.set_viewport_size({'width':1365,'height':900})
        self.assertLess(types.bounding_box()['x']+types.bounding_box()['width'],p.locator('.archive-list').bounding_box()['x'])

    def test_reference_title_opens_original_and_fold_preference_does_not_depend_on_last_project(self):
        p=self.page;p.locator('nav [data-tab="home"]').click()
        fold=p.locator('[data-layout-fold="refs"]');fold.locator('summary').click()
        fold.locator('[data-ie="refs|work-r|title"]').click()
        expect(p.locator('#r-t')).to_have_value('업무 자료')
        p.go_back();expect(fold).to_have_attribute('open','')
        p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="work-p"]').click()
        p.locator('nav [data-tab="home"]').click()
        expect(fold).to_have_attribute('open','')

    def test_work_hides_expense_navigation_but_life_and_saved_costs_remain_accessible(self):
        p=self.page;before=p.evaluate('JSON.stringify(window.__store)')
        expect(p.locator('[data-archive-filter="expense"]')).to_have_count(0)
        self.assertNotIn('지출',p.locator('#rq').get_attribute('placeholder'))
        p.locator('[data-search]').click()
        self.assertNotIn('지출',p.locator('#sqi').get_attribute('placeholder'))
        p.locator('#sqi').fill('업무 도서')
        p.locator('#sqr [data-sgo="expense"]').click()
        expect(p.locator('#x-a')).to_have_value('20,000')
        p.go_back();p.keyboard.press('Escape')
        p.locator('[data-sp="life"]').click()
        expect(p.locator('[data-archive-filter="expense"]')).to_be_visible()
        self.assertIn('지출',p.locator('#rq').get_attribute('placeholder'))
        p.locator('[data-archive-filter="expense"]').click()
        expect(p.locator('.archive-list')).to_contain_text('숙박 결제')
        p.locator('[data-search]').click()
        self.assertIn('지출',p.locator('#sqi').get_attribute('placeholder'))
        p.locator('#sqi').fill('찾을 수 없는 내용')
        p.locator('[data-search-space]').click()
        self.assertNotIn('지출',p.locator('#sqi').get_attribute('placeholder'))
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

"""Organized views preserve original records, navigation and account-local state."""
import unittest
from playwright.sync_api import expect
import test_archive as ui


class LayoutTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown

    def patch(self, collection, ident, fields):
        self.page.evaluate("""async ([c,id,data])=>{
          const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await f.setDoc(f.doc(f.collection({},c),id),data,{merge:true});
        }""", [collection, ident, fields])

    def project(self, ident='work-p'):
        self.page.locator('nav [data-tab="proj"]').click()
        self.page.locator('[data-open="'+ident+'"]').click()

    def test_reminder_summary_is_live_and_keeps_work_life_separate(self):
        self.patch('logs','memo_work',{'html':'<div>반드시 기억할 업무</div>'})
        self.patch('logs','memo_life',{'html':'<div>내가 기억할 일상</div>'})
        p=self.page;p.locator('nav [data-tab="home"]').click()
        summary=p.locator('[data-layout-fold="reminder"]>summary')
        expect(summary).to_contain_text('반드시 기억할 업무')
        self.assertLess(summary.bounding_box()['y'],p.locator('.ch').bounding_box()['y'])
        ui.reveal(p,'[data-memo="memo_work"]')
        p.locator('[data-memo="memo_work"]').fill('수정한 메모도 접어 두면 보여요')
        expect(summary).to_contain_text('수정한 메모도 접어 두면 보여요')
        p.wait_for_function("window.__store.logs.some(x=>x.id==='memo_work'&&x.html.includes('수정한 메모'))")
        p.locator('[data-sp="life"]').click()
        expect(p.locator('[data-layout-fold="reminder"]>summary')).to_contain_text('내가 기억할 일상')
        expect(p.locator('[data-layout-fold="reminder"]>summary')).not_to_contain_text('업무')

    def test_fold_preferences_survive_reload_without_writing_record_data(self):
        self.patch('projects','work-p',{'tbl':{'on':True,'fields':[]}})
        self.patch('projects','life-p',{'tbl':{'on':True,'fields':[]}})
        before=self.page.evaluate('JSON.stringify(window.__store)')
        p=self.page;self.project()
        fold=p.locator('[data-layout-fold="status"]')
        expect(fold).not_to_have_attribute('open','')
        fold.locator('summary').click()
        p.wait_for_function("localStorage.getItem('arecmik:fold:ui-test:proj:work:work-p:status')==='1'")
        p.locator('[data-sp="life"]').click();self.project('life-p')
        expect(p.locator('[data-layout-fold="status"]')).not_to_have_attribute('open','')
        p.locator('[data-sp="work"]').click();self.project()
        expect(p.locator('[data-layout-fold="status"]')).to_have_attribute('open','')
        p.reload();self.project()
        expect(p.locator('[data-layout-fold="status"]')).to_have_attribute('open','')
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

    def test_reminder_preview_keeps_separate_lines_and_opens_original_rich_memo(self):
        html='<div><strong>프로모션 지급 가능 여부 확인하기</strong></div><p>채용 서비스의 MCP / AI 연동 가이드 확인하기<br>이번 주 면접 일정 공유하기</p><div>정산 자료 다시 확인하기</div>'
        self.patch('logs','memo_work',{'html':html})
        p=self.page;p.locator('nav [data-tab="home"]').click()
        before=p.evaluate('JSON.stringify(window.__store)')
        fold=p.locator('[data-layout-fold="reminder"]');summary=fold.locator('summary')
        expect(summary.locator('.layout-reminder-line')).to_have_text(['프로모션 지급 가능 여부 확인하기','채용 서비스의 MCP / AI 연동 가이드 확인하기'])
        expect(summary.locator('.layout-reminder-more')).to_contain_text('2줄 더 보기')
        for width in [1365,390,320]:
            p.set_viewport_size({'width':width,'height':900})
            lines=summary.locator('.layout-reminder-line').all()
            self.assertGreater(lines[1].bounding_box()['y'],lines[0].bounding_box()['y'])
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
        summary.click()
        editor=p.locator('[data-memo="memo_work"]')
        expect(summary.locator('.layout-fold-hint')).to_be_hidden()
        expect(editor.locator('strong')).to_have_text('프로모션 지급 가능 여부 확인하기')
        expect(editor).to_contain_text('정산 자료 다시 확인하기')
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)
        editor.fill('첫 번째로 기억할 일\n두 번째로 기억할 일\n세 번째로 기억할 일')
        summary.click()
        expect(summary.locator('.layout-reminder-line')).to_have_text(['첫 번째로 기억할 일','두 번째로 기억할 일'])
        expect(summary.locator('.layout-reminder-more')).to_contain_text('1줄 더 보기')
        p.wait_for_function("__store.logs.some(l=>l.id==='memo_work'&&l.html.includes('세 번째로 기억할 일'))")
        p.reload()
        expect(p.locator('[data-layout-fold="reminder"] .layout-reminder-line')).to_have_text(['첫 번째로 기억할 일','두 번째로 기억할 일'])

    def test_single_classification_and_composed_search_have_recoverable_empty_state(self):
        self.patch('notes','work-n',{'pid':'work-p'})
        self.patch('projects','other-work',{'name':'다른 업무','space':'work','status':'active'})
        p=self.page
        expect(p.locator('[aria-label="기록과 자료실"]')).to_have_count(1)
        expect(p.locator('.rh [data-rt]')).to_have_count(0)
        ui.archive_filter(p,'doc');p.locator('#rq').fill('중요한 결정')
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        ui.reveal(p,'[data-archive-project]')
        p.locator('[data-archive-project]').select_option('work-p')
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        p.locator('[data-archive-project]').select_option('other-work')
        expect(p.locator('.archive-empty')).to_contain_text('조건에 맞는 기록이 없어요')
        p.locator('.archive-empty [data-archive-reset]').click()
        expect(p.locator('#rq')).to_have_value('')
        expect(p.locator('.archive-list')).to_contain_text('업무 회의록')

    def test_folder_view_back_restores_the_original_search_and_filters(self):
        p=self.page;ui.archive_filter(p,'doc');p.locator('#rq').fill('회의록')
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        p.locator('[data-rt="doc"]').click()
        expect(p.locator('[data-folder-manage]')).to_be_visible()
        p.go_back()
        expect(p.locator('#rq')).to_have_value('회의록')
        expect(p.locator('[data-archive-filter="doc"]')).to_have_attribute('aria-pressed','true')
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)

    def test_new_record_and_reference_are_visible_after_writing_under_other_filters(self):
        p=self.page;p.locator('[data-archive-filter="ref"]').click()
        ui.record_new(p);p.locator('#record-body').fill('새 기록을 필터 뒤에 숨기지 않기')
        p.locator('[data-record-save]').click()
        expect(p.locator('.archive-list')).to_contain_text('새 기록을 필터 뒤에 숨기지 않기')
        ui.archive_filter(p,'doc')
        p.locator('.layout-write>summary').click();p.locator('.layout-write [data-newref]').click()
        p.locator('#r-t').fill('새 자료도 바로 보여요');p.locator('#r-b').fill('기억할 자료 내용');p.locator('[data-rsave]').click()
        expect(p.locator('.archive-list')).to_contain_text('새 자료도 바로 보여요')
        self.assertEqual(p.evaluate("window.__store.refs.filter(r=>r.title==='새 자료도 바로 보여요').length"),1)

    def test_journal_and_long_document_use_original_editors_and_remain_findable(self):
        p=self.page;p.locator('.layout-write>summary').click();p.locator('[data-journal-write]').click()
        editor=p.locator('[data-log][contenteditable]').first
        editor.fill('정리된 화면에서도 원래 일지를 저장해요')
        p.locator('[data-rt="archive"]').click();ui.archive_filter(p,'log')
        expect(p.locator('.archive-list')).to_contain_text('정리된 화면에서도 원래 일지를 저장해요')
        p.locator('.layout-write>summary').click();p.locator('.layout-write [data-newdoc]').click()
        p.locator('.dt').fill('원래 문서 편집기의 긴 글');p.locator('[data-db]').fill('폴더와 프로젝트에 연결할 본문')
        p.locator('nav [data-tab="rec"]').click();ui.archive_filter(p,'doc')
        expect(p.locator('.archive-list')).to_contain_text('원래 문서 편집기의 긴 글')

    def test_connected_vendor_opens_even_when_its_section_was_saved_closed(self):
        self.patch('projects','work-p',{'tbl':{'on':True,'fields':[]}})
        self.patch('ents','work-row',{'pid':'work-p','title':'연결한 업체','v':{},'connections':[{'c':'notes','id':'work-n','sourceId':'work-row'}]})
        self.patch('notes','work-n',{'connections':[{'c':'ents','id':'work-row','sourceId':'work-n'}]})
        p=self.page;self.project();fold=p.locator('[data-layout-fold="status"]')
        fold.locator('summary').click();fold.locator('summary').click()
        p.locator('nav [data-tab="rec"]').click();p.locator('[data-archive-open="doc"][data-id="work-n"]').click()
        p.locator('article.doc .connection-open').filter(has_text='연결한 업체').click()
        expect(p.locator('[data-rname="work-row"]')).to_be_visible()
        expect(p.locator('[data-layout-fold="status"]')).to_have_attribute('open','')

    def test_calendar_connections_are_available_in_details_without_repeated_list_actions(self):
        self.patch('todos','work-t',{'kind':'event','date':'2026-10-20','projectId':'work-p'})
        p=self.page;p.set_viewport_size({'width':390,'height':844})
        p.locator('nav [data-tab="home"]').click()
        p.locator('[data-pick="2026-10-20"]').first.click()
        expect(p.locator('.dside [data-edit="work-t"]')).to_be_visible()
        expect(p.locator('.dside [data-conn-manage],.dside [data-conn-record]')).to_have_count(0)
        p.locator('.dside [data-edit="work-t"]').click()
        expect(p.locator('#sheet [data-conn-manage]')).to_have_count(1)
        ui.reveal(p,'#sheet [data-conn-record]')
        p.locator('#sheet [data-conn-record]').click()
        expect(p.locator('#record-day')).to_have_value('2026-10-20')
        expect(p.locator('#record-project')).to_have_value('work-p')
        p.locator('#record-body').fill('세부 화면에서 연결해 남긴 결정')
        p.locator('[data-record-save]').click()
        p.wait_for_function("window.__store.moms.some(m=>m.t==='세부 화면에서 연결해 남긴 결정')")
        saved=p.evaluate("window.__store.moms.find(m=>m.t==='세부 화면에서 연결해 남긴 결정')")
        self.assertEqual(saved['connections'][0]['id'],'work-t')
        self.assertTrue(p.evaluate('(id)=>window.__store.todos.find(t=>t.id===\'work-t\').connections.some(c=>c.id===id)',saved['id']))

    def test_materials_open_above_calendar_with_favorites_and_recent_items_without_search(self):
        self.patch('refs','work-r',{'fav':True})
        for i in range(4):
            self.patch('refs','recent-'+str(i),{'title':'최근 업무 자료 '+str(i),'space':'work','created':ui.STAMP+i+1})
        p=self.page;p.set_viewport_size({'width':390,'height':844})
        before=p.evaluate('JSON.stringify(window.__store)')
        p.locator('nav [data-tab="home"]').click()
        refs=p.locator('[data-layout-fold="refs"]')
        expect(refs.locator('summary')).to_contain_text('업무 자료')
        self.assertLess(refs.locator('summary').bounding_box()['y'],p.locator('.ch').bounding_box()['y'])
        refs.locator('summary').click()
        expect(refs.locator('[data-oref]')).to_have_count(3)
        expect(refs.locator('[data-oref]').first).to_contain_text('업무 자료')
        expect(refs.locator('[data-oref]')).to_contain_text(['업무 자료','최근 업무 자료 3','최근 업무 자료 2'])
        refs.locator('[data-oref="work-r"] span').click()
        expect(p.locator('[data-db]')).to_contain_text('팀 연락처')
        p.go_back();refs.locator('[data-goref]').click()
        expect(p.locator('[data-oref="recent-0"]')).to_be_visible()
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)
        p.locator('nav [data-tab="home"]').click();p.locator('[data-sp="life"]').click()
        expect(p.locator('[data-layout-fold="refs"]')).to_contain_text('여행 자료')
        expect(p.locator('[data-layout-fold="refs"]')).not_to_contain_text('업무 자료')

    def test_life_home_keeps_diary_close_to_calendar_with_a_long_task_list_and_old_height(self):
        p=self.page
        for i in range(8):
            self.patch('todos','life-pending-'+str(i),{'title':'여행 준비할 일 '+str(i),'space':'life','done':False})
        p.evaluate("localStorage.setItem('rz_dsh','1200')")
        p.reload();p.set_viewport_size({'width':1365,'height':900})
        p.locator('nav [data-tab="home"]').click();p.locator('[data-sp="life"]').click()
        before=p.evaluate('JSON.stringify(window.__store)')
        calendar=p.locator('.mg');journal=p.locator('[data-layout-fold="journal"]')
        pending=p.locator('[data-layout-fold="undated"]');spend=p.locator('[data-layout-fold="spend"]')
        cb=calendar.bounding_box();jb=journal.bounding_box();pb=pending.bounding_box();sb=spend.bounding_box()
        self.assertAlmostEqual(jb['x'],cb['x'],delta=1)
        self.assertAlmostEqual(jb['width'],cb['width'],delta=1)
        self.assertAlmostEqual(jb['y']-(cb['y']+cb['height']),16,delta=1)
        self.assertAlmostEqual(sb['y']-(pb['y']+pb['height']),16,delta=1)
        self.assertLess(p.locator('.dside').bounding_box()['height'],300)
        expect(p.locator('.layout-home-extras')).to_be_hidden()
        p.set_viewport_size({'width':390,'height':844})
        boxes=[p.locator(s).bounding_box() for s in ['.mg','.dside','[data-layout-fold="undated"]','[data-layout-fold="journal"]','[data-layout-fold="spend"]']]
        for above,below in zip(boxes,boxes[1:]):
            self.assertAlmostEqual(below['y']-above['y']-above['height'],16,delta=1)
        self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),390)
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

    def test_work_journal_stays_under_month_with_long_pending_list_on_pc(self):
        p=self.page
        for i in range(12):
            self.patch('todos','work-pending-'+str(i),{'title':'놓치지 않을 업무 '+str(i),'space':'work','done':False})
        p.locator('nav [data-tab="home"]').click()
        before=p.evaluate('JSON.stringify(window.__store)')
        for width in [1365,1108,1024,901,900,760]:
            with self.subTest(width=width):
                p.set_viewport_size({'width':width,'height':1000});p.evaluate('scrollTo(0,0)')
                cb=p.locator('.mg').bounding_box();jb=p.locator('[data-layout-fold="journal"]').bounding_box()
                pb=p.locator('[data-layout-fold="undated"]').bounding_box()
                self.assertAlmostEqual(jb['x'],cb['x'],delta=1)
                self.assertAlmostEqual(jb['width'],cb['width'],delta=1)
                self.assertAlmostEqual(jb['y']-cb['y']-cb['height'],16,delta=1)
                self.assertLess(jb['y'],pb['y']+pb['height'])
                expect(p.locator('.layout-home-extras')).to_be_hidden()
                self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
        p.set_viewport_size({'width':390,'height':844})
        boxes=[p.locator(s).bounding_box() for s in ['.mg','.dside','[data-layout-fold="undated"]','[data-layout-fold="journal"]']]
        for above,below in zip(boxes,boxes[1:]):
            self.assertAlmostEqual(below['y']-above['y']-above['height'],16,delta=1)
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

    def test_work_journal_keeps_unsaved_editor_across_pc_phone_and_touch_tablet(self):
        p=self.page;p.set_viewport_size({'width':1365,'height':900})
        p.locator('nav [data-tab="home"]').click()
        ui.reveal(p,'[data-log][contenteditable]')
        editor=p.locator('[data-log][contenteditable]')
        editor.fill('달력 바로 아래에서 작성한 업무일지')
        p.evaluate("window.__workJournal=document.querySelector('[data-log][contenteditable]')")
        for width in [800,390]:
            p.set_viewport_size({'width':width,'height':900})
            self.assertTrue(p.evaluate("window.__workJournal===document.querySelector('[data-log][contenteditable]')"))
            expect(editor).to_contain_text('달력 바로 아래에서 작성한 업무일지')
        cdp=self.context.new_cdp_session(p)
        cdp.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':5})
        p.set_viewport_size({'width':900,'height':1000})
        self.assertTrue(p.evaluate("window.__workJournal===document.querySelector('[data-log][contenteditable]')"))
        pending=p.locator('[data-layout-fold="undated"]').bounding_box()
        self.assertAlmostEqual(p.locator('[data-layout-fold="journal"]').bounding_box()['y']-pending['y']-pending['height'],16,delta=1)
        p.wait_for_function("window.__store.notes.some(n=>n.log&&n.space==='work'&&n.html?.includes('달력 바로 아래에서 작성한 업무일지'))")
        p.reload();ui.reveal(p,'[data-log][contenteditable]')
        expect(p.locator('[data-log][contenteditable]')).to_contain_text('달력 바로 아래에서 작성한 업무일지')
        p.locator('[data-sp="life"]').click();ui.reveal(p,'[data-log][contenteditable]')
        expect(p.locator('[data-log][contenteditable]')).not_to_contain_text('달력 바로 아래에서 작성한 업무일지')
        p.locator('[data-sp="work"]').click();ui.reveal(p,'[data-log][contenteditable]')
        expect(p.locator('[data-log][contenteditable]')).to_contain_text('달력 바로 아래에서 작성한 업무일지')

    def test_life_diary_and_spending_still_save_after_reflow(self):
        p=self.page;p.set_viewport_size({'width':1365,'height':900})
        p.locator('nav [data-tab="home"]').click();p.locator('[data-sp="life"]').click()
        ui.reveal(p,'[data-log][contenteditable]')
        editor=p.locator('[data-log][contenteditable]')
        editor.fill('배치가 바뀌어도 오늘의 일기를 보관해요')
        p.evaluate("window.__lifeDiary=document.querySelector('[data-log][contenteditable]')")
        p.set_viewport_size({'width':390,'height':844})
        self.assertTrue(p.evaluate("window.__lifeDiary===document.querySelector('[data-log][contenteditable]')"))
        expect(editor).to_contain_text('오늘의 일기를 보관해요')
        ui.reveal(p,'#spi');p.locator('#spi').fill('점심 9000');p.locator('#spi').press('Enter')
        p.wait_for_function("window.__store.exps.some(e=>e.t==='점심'&&e.a===9000&&e.sp==='life')")
        p.wait_for_function("window.__store.notes.some(n=>n.log&&n.space==='life'&&n.html?.includes('오늘의 일기를 보관해요'))")
        p.reload();ui.reveal(p,'[data-log][contenteditable]');ui.reveal(p,'#spi')
        expect(p.locator('[data-log][contenteditable]')).to_contain_text('오늘의 일기를 보관해요')
        expect(p.locator('.spend')).to_contain_text('9,000')
        p.locator('[data-sp="work"]').click()
        expect(p.locator('.spend')).to_have_count(0)
        expect(p.locator('.layout-life-home')).to_have_count(0)

    def test_tasks_stay_out_of_default_records_but_are_retrievable_without_data_loss(self):
        self.patch('todos','work-t',{'done':True,'doneDate':'2026-10-20','fav':True})
        self.patch('todos','work-undated',{'title':'날짜 없는 원래 할 일','space':'work','done':False})
        self.patch('todos','work-event',{'title':'이미 지난 원래 일정','space':'work','kind':'event','date':'2026-01-01'})
        p=self.page;before=p.evaluate('JSON.stringify(window.__store)')
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(0)
        expect(p.locator('.archive-list')).to_contain_text('업무 회의 회고')
        ui.archive_filter(p,'todo')
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(3)
        p.locator('[data-archive-open="todo"][data-id="work-t"]').click()
        expect(p.locator('#e-n')).to_contain_text('검토 의견')
        p.go_back();p.locator('[data-archive-reset]').first.click()
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(0)
        ui.archive_filter(p,'todo');p.locator('[data-archive-favorites]').click()
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(1)
        p.locator('[data-archive-reset]').first.click();p.locator('[data-search]').click();p.locator('#sqi').fill('검토 의견')
        expect(p.locator('#sqr [data-sgo="todo"][data-id="work-t"]')).to_have_count(1)
        p.locator('#sqi').press('Escape')
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(0)
        self.assertEqual(p.evaluate('JSON.stringify(window.__store)'),before)

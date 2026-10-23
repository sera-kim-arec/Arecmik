"""Connections exercise original editors against the isolated Firestore adapter."""
from pathlib import Path
import unittest

from playwright.sync_api import expect
import test_archive as archive


class ConnectionTests(unittest.TestCase):
    setUpClass = classmethod(archive.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(archive.ArchiveTests.tearDownClass.__func__)
    setUp = archive.ArchiveTests.setUp
    tearDown = archive.ArchiveTests.tearDown
    search = archive.ArchiveTests.search
    life = archive.ArchiveTests.life
    def patch(self, collection, ident, fields):
        self.page.evaluate("""async ([c,id,fields])=>{
          const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await f.setDoc(f.doc(f.collection({},c),id),fields,{merge:true});
        }""", [collection, ident, fields])

    def record(self):
        self.page.locator('nav [data-tab="rec"]').click()
        self.page.locator('[data-archive-open="mom"][data-id="work-m"]').click()
        expect(self.page.locator('#sheet .connections-panel')).to_be_visible()

    def manage(self):
        self.page.locator('#scrim.on #sheet [data-conn-manage],article.doc [data-conn-manage]').first.click()
        expect(self.page.locator('#connections-dialog')).to_be_visible()

    def connect_reference(self):
        self.record()
        self.manage()
        self.page.locator('#connection-query').fill('업무 자료')
        self.page.locator('[data-conn-add]').click()
        expect(self.page.locator('#connection-linked')).to_contain_text('업무 자료')
        self.page.locator('[data-conn-close]').click()

    def test_connect_reverse_live_rename_and_unlink_preserve_originals(self):
        self.connect_reference()
        p=self.page
        self.assertEqual(p.evaluate("window.__store.moms.find(m=>m.id==='work-m').connections.length"),1)
        self.assertEqual(p.evaluate("window.__store.refs.find(r=>r.id==='work-r').connections[0].id"),'work-m')
        self.patch('refs','work-r',{'title':'바뀐 자료 제목'})
        expect(p.locator('#sheet .connections-panel')).to_contain_text('바뀐 자료 제목')
        p.locator('#sheet .connection-open').filter(has_text='바뀐 자료 제목').click()
        expect(p.locator('[data-dt]')).to_have_value('바뀐 자료 제목')
        expect(p.locator('article.doc .connections-panel')).to_contain_text('업무 회의 회고')
        self.manage()
        p.locator('[data-conn-remove]').click()
        expect(p.locator('#connection-linked')).not_to_contain_text('업무 회의 회고')
        self.assertEqual(p.evaluate("window.__store.moms.find(m=>m.id==='work-m').connections"),[])
        self.assertEqual(p.evaluate("window.__store.refs.find(r=>r.id==='work-r').html"),'<div>팀 연락처</div>')

    def test_task_failure_preserves_draft_and_success_inherits_context(self):
        self.patch('moms','work-m',{'pid':'work-p'})
        self.record();p=self.page
        p.locator('#sheet [data-conn-task]').click()
        p.locator('#connection-task-title').fill('회의 다음 행동')
        p.evaluate("window.__failWritesFor='moms'")
        p.locator('#connection-task-form button[type="submit"]').click()
        expect(p.locator('.connections-error')).to_contain_text('저장하지 못했어요')
        self.assertFalse(p.evaluate("window.__store.todos.some(t=>t.title==='회의 다음 행동')"))
        expect(p.locator('#connection-task-title')).to_have_value('회의 다음 행동')
        p.locator('[data-conn-close]').first.click()
        p.locator('#sheet [data-conn-task]').click()
        expect(p.locator('#connection-task-title')).to_have_value('회의 다음 행동')
        p.evaluate('window.__failWritesFor=null')
        p.locator('#connection-task-form button[type="submit"]').click()
        expect(p.locator('#connections-dialog')).not_to_be_visible()
        task=p.evaluate("window.__store.todos.find(t=>t.title==='회의 다음 행동')")
        self.assertEqual((task['projectId'],task['space'],task['date']),('work-p','work',''))
        self.assertEqual(task['connections'][0]['id'],'work-m')
        p.locator('#sheet [data-sx="0"]').click()
        p.locator('nav [data-tab="home"]').click()
        expect(p.locator('.undbox')).to_contain_text('회의 다음 행동')

    def test_event_record_carries_actual_date_and_keeps_bidirectional_links(self):
        self.patch('todos','work-t',{'kind':'event','date':'2026-10-20','projectId':'work-p'})
        self.search('보고서 제출');p=self.page
        p.locator('#sqr [data-sgo="todo"]').click()
        archive.reveal(p,'#sheet [data-conn-record]')
        p.locator('#sheet [data-conn-record]').click()
        expect(p.locator('#record-day')).to_have_value('2026-10-20')
        expect(p.locator('#record-project')).to_have_value('work-p')
        expect(p.locator('.connections-origin')).to_contain_text('보고서 제출')
        p.locator('#record-body').fill('일정에서 결정한 내용')
        p.locator('[data-record-save]').click()
        p.wait_for_function("window.__store.moms.some(m=>m.t==='일정에서 결정한 내용')")
        saved=p.evaluate("window.__store.moms.find(m=>m.t==='일정에서 결정한 내용')")
        self.assertEqual(saved['connections'][0]['id'],'work-t')
        self.assertEqual((saved['d'],saved['pid']),('2026-10-20','work-p'))
        self.assertTrue(p.evaluate('(id)=>window.__store.todos.find(t=>t.id===\'work-t\').connections.some(c=>c.id===id)',saved['id']))

    def test_cross_space_and_deleted_candidates_cannot_be_linked(self):
        self.record();self.manage();p=self.page
        p.locator('#connection-query').fill('바닷가')
        expect(p.locator('#connection-candidates')).to_contain_text('연결 후보')
        p.locator('#connection-query').fill('업무 자료')
        button=p.locator('[data-conn-add]')
        button.evaluate("b=>b.dataset.connAdd=encodeURIComponent(JSON.stringify({c:'moms',id:'life-m'}))")
        button.click()
        expect(p.locator('.connections-error')).to_contain_text('같은 공간')
        self.assertFalse(p.evaluate("!!window.__store.moms.find(m=>m.id==='work-m').connections"))
        p.locator('#connection-query').fill('업무 자료 ')
        p.evaluate("window.__store.refs=window.__store.refs.filter(r=>r.id!=='work-r')")
        p.locator('[data-conn-add]').click()
        expect(p.locator('.connections-error')).to_contain_text('원본 항목')
        self.assertFalse(p.evaluate("!!window.__store.moms.find(m=>m.id==='work-m').connections"))

    def test_origin_draft_and_browser_back_survive_opening_linked_item(self):
        self.connect_reference();p=self.page
        p.locator('#record-body').fill('아직 저장하지 않은 원본 메모')
        p.locator('#sheet .connection-open').filter(has_text='업무 자료').click()
        expect(p.locator('[data-dt]')).to_have_value('업무 자료')
        p.go_back()
        expect(p.locator('#record-body')).to_have_text('아직 저장하지 않은 원본 메모')
        self.assertEqual(p.evaluate("window.__store.moms.find(m=>m.id==='work-m').t"),'업무 회의 회고')

    def test_delete_restore_and_backup_keep_original_connections(self):
        self.connect_reference();p=self.page
        p.locator('#sheet .connection-open').filter(has_text='업무 자료').click()
        p.locator('article.doc [data-more]').click();p.locator('.pop [data-ddel]').click()
        p.wait_for_function("!window.__store.refs.some(r=>r.id==='work-r')")
        p.locator('.toast button').click()
        p.wait_for_function("window.__store.refs.some(r=>r.id==='work-r')")
        self.record()
        expect(p.locator('#sheet .connections-panel')).to_contain_text('업무 자료')
        p.locator('#sheet [data-sx="0"]').click()
        p.locator('[data-menu]').click()
        with p.expect_download() as event:
            p.locator('[data-backup]').click()
        text=Path(event.value.path()).read_text()
        restored=p.evaluate("async text=>(await import('./backup-restore.js')).readBackup(text)",text)
        note=next(n for n in restored['moms'] if n['id']=='work-m')
        self.assertEqual(note['connections'][0]['id'],'work-r')

    def test_two_days_in_one_monthly_note_keep_distinct_connections(self):
        self.patch('notes','work-month',{'space':'work','log':True,'mon':'2026-10','html':"<div class='h2 dayh'>10/14 (수)</div><div>첫째 날의 일지</div><div class='h2 dayh'>10/15 (목)</div><div>둘째 날의 일지</div>", 'updated':1792022400000})
        p=self.page;archive.record_source(p,'log')
        first=p.locator('.lday').filter(has=p.locator('[data-elog="2026-10-14"]'))
        first.locator('[data-conn-manage]').first.click()
        p.locator('#connection-query').fill('2026-10-15 업무일지')
        p.locator('[data-conn-add]').click()
        expect(p.locator('#connection-linked')).to_contain_text('2026-10-15 업무일지')
        edges=p.evaluate("window.__store.notes.find(n=>n.id==='work-month').connections")
        self.assertEqual({(e['sourceDay'],e['day']) for e in edges},{('2026-10-14','2026-10-15'),('2026-10-15','2026-10-14')})
        p.locator('[data-conn-close]').first.click()
        first.locator('[data-conn-task]').click()
        p.locator('#connection-task-title').fill('첫째 날에서 나온 할 일')
        p.locator('#connection-task-form button[type="submit"]').click()
        expect(first.locator('.connections-panel')).to_contain_text('첫째 날에서 나온 할 일')
        second=p.locator('.lday').filter(has=p.locator('[data-elog="2026-10-15"]'))
        expect(second.locator('.connections-panel')).not_to_contain_text('첫째 날에서 나온 할 일')

    def test_mobile_completion_updates_original_and_space_does_not_leak(self):
        self.record();self.manage();p=self.page;p.set_viewport_size({'width':390,'height':844})
        p.locator('#connection-query').fill('보고서 제출');p.locator('[data-conn-add]').click()
        p.locator('[data-conn-close]').first.click()
        p.locator('#sheet [data-conn-complete]').click()
        p.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').done")
        expect(p.locator('#sheet [data-conn-complete]')).to_have_attribute('aria-pressed','true')
        self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),390)
        p.locator('#sheet [data-sx="0"]').click();self.life()
        expect(p.locator('main')).not_to_contain_text('보고서 제출')

    def test_manual_project_link_is_searchable_and_in_project_archive_filter(self):
        p=self.page;p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="work-p"]').click()
        archive.reveal(p,'.project-connections [data-conn-manage]')
        p.locator('.project-connections [data-conn-manage]').first.click()
        p.locator('#connection-query').fill('업무 자료');p.locator('[data-conn-add]').click()
        expect(p.locator('#connection-linked')).to_contain_text('업무 자료')
        p.locator('[data-conn-close]').first.click()
        expect(p.locator('.project-connections')).to_contain_text('업무 자료')
        p.locator('nav [data-tab="rec"]').click();p.locator('[data-archive-filter="ref"]').click();archive.reveal(p,'[data-archive-project]');p.locator('[data-archive-project]').select_option('work-p')
        expect(p.locator('.archive-list')).to_contain_text('업무 자료')
        self.assertFalse(p.evaluate("!!window.__store.refs.find(r=>r.id==='work-r').pid"))
        self.search('업무 프로젝트')
        expect(p.locator('#sqr [data-sgo="ref"][data-id="work-r"]')).to_contain_text('연결: 업무 프로젝트')
        p.locator('#sqr [data-sgo="ref"][data-id="work-r"]').click()
        p.locator('article.doc [data-conn-task]').click()
        expect(p.locator('#connection-task-project')).to_have_value('work-p')

    def test_failed_unlink_cannot_leave_one_sided_changes(self):
        self.connect_reference();self.manage();p=self.page
        p.evaluate("window.__failWritesFor='refs'");p.locator('[data-conn-remove]').click()
        expect(p.locator('.connections-error')).to_contain_text('저장하지 못했어요')
        self.assertEqual(p.evaluate("window.__store.moms.find(m=>m.id==='work-m').connections.length"),1)
        self.assertEqual(p.evaluate("window.__store.refs.find(r=>r.id==='work-r').connections.length"),1)
        p.evaluate('window.__failWritesFor=null');p.locator('[data-conn-remove]').click()
        expect(p.locator('#connection-linked')).not_to_contain_text('업무 자료')

    def test_repeated_occurrence_does_not_inherit_original_record_links(self):
        self.patch('todos','work-t',{'kind':'event','date':'2026-10-19','rep':'d'})
        self.record();self.manage();p=self.page
        p.locator('#connection-query').fill('보고서 제출');p.locator('[data-conn-add]').click()
        p.locator('[data-conn-close]').first.click();p.locator('#sheet [data-conn-complete]').click()
        p.wait_for_function("window.__store.todos.some(t=>t.date==='2026-10-20')")
        following=p.evaluate("window.__store.todos.find(t=>t.date==='2026-10-20')")
        self.assertNotIn('connections',following)
        # The native widget can copy unknown optional fields into a repeat. An
        # edge's sourceId must still prevent it attaching to a new occurrence.
        original=p.evaluate("window.__store.todos.find(t=>t.id==='work-t').connections")
        self.patch('todos',following['id'],{'connections':original})
        p.locator('#sheet [data-sx="0"]').click();self.search('보고서 제출')
        p.locator('#sqr [data-sgo="todo"][data-id="'+following['id']+'"]').click()
        expect(p.locator('#sheet .connections-panel')).not_to_contain_text('업무 회의 회고')

    def test_double_submit_creates_one_followup_and_draft_survives_reload(self):
        self.record();p=self.page;p.locator('#sheet [data-conn-task]').click()
        p.locator('#connection-task-title').fill('한 번만 만들 할 일')
        p.locator('[data-conn-close]').first.click();p.reload();self.record()
        p.locator('#sheet [data-conn-task]').click();expect(p.locator('#connection-task-title')).to_have_value('한 번만 만들 할 일')
        p.evaluate('window.__writeDelayMs=400')
        p.locator('#connection-task-form button[type="submit"]').evaluate('b=>{b.click();b.click();}')
        expect(p.locator('#connections-dialog')).not_to_be_visible()
        self.assertEqual(p.evaluate("window.__store.todos.filter(t=>t.title==='한 번만 만들 할 일').length"),1)

    def test_status_task_expense_flow_uses_original_ledger_amount_once(self):
        self.patch('projects','work-p',{'tbl':{'on':True,'fields':[{'k':'amount','n':'금액','t':'num'}]},'mods':{'memo':True,'cost':True}})
        self.patch('ents','work-row',{'pid':'work-p','title':'제작 업체','v':{'amount':100000},'created':1792022400000})
        self.patch('todos','work-t',{'projectId':'work-p','eid':'work-row'})
        self.patch('exps','work-e',{'tid':'work-t','eid':'work-row'})
        self.search('업무 도서');p=self.page;p.locator('#sqr [data-sgo="expense"][data-id="work-e"]').click()
        expect(p.locator('#sheet .connections-panel')).to_contain_text('보고서 제출')
        expect(p.locator('#sheet .connections-panel')).to_contain_text('제작 업체')
        p.locator('#sheet .connection-open').filter(has_text='보고서 제출').click()
        expect(p.locator('#sheet .connections-panel')).to_contain_text('20,000원')
        p.locator('#sheet .connection-open').filter(has_text='제작 업체').click()
        expect(p.locator('[data-rname="work-row"]')).to_be_visible()
        expect(p.locator('.hrf .connections-panel')).to_contain_text('업무 도서')
        self.assertEqual(p.evaluate("window.__store.exps.filter(e=>e.pid==='work-p').reduce((a,e)=>a+e.a,0)"),20000)

    def test_search_origin_returns_after_link_navigation_without_losing_query(self):
        self.patch('todos','work-t',{'kind':'event','date':'2026-10-20','projectId':'work-p'})
        self.search('보고서 제출');p=self.page;p.locator('#sqr [data-sgo="todo"]').click()
        archive.reveal(p,'#sheet [data-conn-record]')
        p.locator('#sheet [data-conn-record]').click()
        p.locator('#record-body').fill('검색에서 이어 쓴 임시 기록')
        p.go_back()
        expect(p.locator('#e-t')).to_have_value('보고서 제출')
        p.locator('#sheet [data-sx="0"]').click()
        expect(p.locator('#srch')).to_have_class('srov on')
        expect(p.locator('#sqi')).to_have_value('보고서 제출')

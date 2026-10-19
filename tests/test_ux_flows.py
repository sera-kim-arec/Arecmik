"""Reproduce audit failures through the actual UI, with no private account access."""
import copy
import json
import unittest
from playwright.sync_api import expect
import test_archive as ui


class UXFlowTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown
    search = ui.ArchiveTests.search

    def project(self):
        self.page.locator("nav [data-tab='proj']").click()
        self.page.locator('[data-open="work-p"]').click()

    def mutate(self, code):
        self.page.evaluate("async()=>{const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');const ref=(c,id)=>m.doc(m.collection({},c),id);"+code+"}")

    def link_task(self, extra=''):
        self.mutate("await m.updateDoc(ref('todos','work-t'),{projectId:'work-p'"+extra+"});")

    def delete_project(self):
        self.page.locator('[data-more="proj"]').click()
        self.page.locator('[data-pdel="work-p"]').click()
        self.page.locator('#sheet [data-sx="1"]').click()

    def test_quick_entry_failure_keeps_draft_after_reload_and_retries_once(self):
        self.project()
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('#pq-t').fill('남겨야 할 할 일')
        self.page.locator('#pq-t').press('Enter')
        expect(self.page.locator('.toast')).to_contain_text('입력 내용을 유지')
        expect(self.page.locator('#pq-t')).to_have_value('남겨야 할 할 일')
        self.assertFalse(self.page.evaluate("window.__store.todos.some(t=>t.title==='남겨야 할 할 일')"))
        self.page.reload(); self.project()
        expect(self.page.locator('#pq-t')).to_have_value('남겨야 할 할 일')
        self.page.evaluate('window.__writeDelayMs=500')
        self.page.locator('#pq-t').press('Enter')
        expect(self.page.locator('#save-status')).to_contain_text('전송 중')
        self.page.locator('[data-zoom="near"]').click()
        self.page.locator('#pq-t').press('Enter')
        self.page.wait_for_function("window.__store.todos.some(t=>t.title==='남겨야 할 할 일')")
        expect(self.page.locator('#pq-t')).to_have_value('')
        self.assertEqual(self.page.evaluate("window.__store.todos.filter(t=>t.title==='남겨야 할 할 일').length"), 1)

    def test_done_failure_stays_unchecked_and_retry_commits(self):
        self.link_task(); self.project()
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-ck="work-t"]').click()
        expect(self.page.locator('.toast')).to_contain_text('원래 상태')
        expect(self.page.locator('[data-drag="work-t"]')).not_to_have_class('it dn')
        self.assertFalse(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').done"))
        self.page.evaluate('window.__failWrites=false')
        self.page.locator('[data-retry-action]').click()
        self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').done")
        expect(self.page.locator('[data-ck="work-t"]')).to_be_enabled()

    def test_repeat_complete_and_cancel_are_atomic_and_restore_the_chain(self):
        self.link_task(",date:'2026-10-16',rep:'d'"); self.project()
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-ck="work-t"]').click()
        expect(self.page.locator('.toast')).to_contain_text('저장하지 못했어요')
        self.assertEqual(self.page.evaluate("window.__store.todos.filter(t=>t.title==='보고서 제출').length"), 1)
        self.page.evaluate('window.__failWrites=false')
        self.page.locator('[data-ck="work-t"]').click()
        self.page.wait_for_function("window.__store.todos.filter(t=>t.title==='보고서 제출').length===2")
        self.page.locator('[data-ck="work-t"]').click()
        self.page.wait_for_function("window.__store.todos.filter(t=>t.title==='보고서 제출').length===1")
        task=self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t')")
        self.assertEqual((task['rep'],task['done']),('d',False))

    def test_repeat_cancel_preserves_a_later_edit_to_next_occurrence(self):
        self.link_task(",date:'2026-10-16',rep:'d'"); self.project()
        self.page.locator('[data-ck="work-t"]').click()
        self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').repeatUndo")
        self.mutate("const task=window.__store.todos.find(t=>t.id==='work-t');await m.updateDoc(ref('todos',task.repeatUndo.nextId),{title:'다른 기기에서 바꾼 제목'});")
        self.page.locator('[data-ck="work-t"]').click()
        expect(self.page.locator('.toast')).to_contain_text('다음 반복을 수정')
        self.assertTrue(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').done"))
        self.assertTrue(self.page.evaluate("window.__store.todos.some(t=>t.title==='다른 기기에서 바꾼 제목')"))

    def test_project_delete_failure_is_atomic_for_all_related_records(self):
        self.link_task()
        self.mutate("await m.updateDoc(ref('notes','work-n'),{pid:'work-p'});await m.updateDoc(ref('moms','work-m'),{pid:'work-p'});")
        self.project(); self.page.evaluate("window.__failWritesFor='trash'")
        self.delete_project()
        expect(self.page.locator('.toast')).to_contain_text('삭제하지 못했어요')
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').projectId"),'work-p')
        self.assertEqual(self.page.evaluate("window.__store.notes.find(t=>t.id==='work-n').pid"),'work-p')
        self.assertEqual(self.page.evaluate("window.__store.moms.find(t=>t.id==='work-m').pid"),'work-p')
        self.assertEqual(self.page.evaluate("window.__store.exps.find(t=>t.id==='work-e').pid"),'work-p')

    def test_project_restore_does_not_replace_a_newer_assignment(self):
        self.link_task(); self.project(); self.delete_project()
        self.page.wait_for_function("!window.__store.projects.some(p=>p.id==='work-p')")
        self.mutate("await m.setDoc(ref('projects','other'),{name:'다른 프로젝트',space:'work',status:'active'});await m.updateDoc(ref('todos','work-t'),{projectId:'other'});")
        self.page.locator('[data-menu]').click();self.page.locator('[data-trash]').click()
        self.page.locator('[data-rest="projects_work-p"]').click()
        self.page.wait_for_function("window.__store.projects.some(p=>p.id==='work-p')")
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').projectId"),'other')
        self.assertEqual(self.page.evaluate("window.__store.exps.find(t=>t.id==='work-e').pid"),'work-p')

    def test_initial_read_failure_exposes_retry_and_recovers(self):
        self.context.add_init_script("window.__failSnapshot='notes'")
        self.page.reload()
        expect(self.page.locator('#sync-status')).to_contain_text('자료를 불러오지 못했어요')
        self.assertNotIn('불러오는 중',self.page.locator('#main').inner_text())
        self.page.evaluate('window.__failSnapshot=null')
        self.page.locator('[data-retry-load]').click()
        expect(self.page.locator('.archive-intro')).to_be_visible()
        expect(self.page.locator('#sync-status')).to_be_hidden()

    def test_invalid_edited_range_is_not_silently_truncated(self):
        self.link_task(",kind:'event',date:'2026-10-20',end:'2026-10-25'")
        self.search('보고서 제출'); self.page.locator('#sqr [data-sgo="todo"]').click()
        self.page.locator('#e-e').fill('2026-10-10'); self.page.locator('[data-esave]').click()
        expect(self.page.locator('#e-e')).to_have_attribute('aria-invalid','true')
        expect(self.page.locator('#e-e-error')).to_contain_text('끝 날짜')
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').end"),'2026-10-25')
        self.page.locator('#e-e').fill('2026-10-26'); self.page.locator('[data-esave]').click()
        self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').end==='2026-10-26'")

    def test_reference_draft_survives_dismissal_reload_and_clears_after_save(self):
        self.page.locator('[data-rt="ref"]').click(); self.page.locator('[data-newref]').click()
        self.page.locator('[data-rsave]').click()
        expect(self.page.locator('#r-t-error')).to_contain_text('자료 제목')
        self.page.locator('#r-t').fill('기억할 자료');self.page.locator('#r-b').fill('닫아도 보존할 내용')
        self.page.locator('#sheet [data-sx="0"]').click();self.page.reload()
        self.page.locator('[data-newref]').click()
        expect(self.page.locator('#r-t')).to_have_value('기억할 자료');expect(self.page.locator('#r-b')).to_have_text('닫아도 보존할 내용')
        self.page.locator('[data-rsave]').click()
        self.page.wait_for_function("window.__store.refs.some(r=>r.title==='기억할 자료')")
        self.page.locator('[data-newref]').click();expect(self.page.locator('#r-t')).to_have_value('')

    def test_browser_back_restores_project_and_archive_filters(self):
        self.mutate("await m.updateDoc(ref('notes','work-n'),{pid:'work-p'});")
        self.page.locator('[data-archive-month]').select_option('2026-10')
        self.project();self.page.locator('.project-records [data-archive-open="doc"]').click()
        expect(self.page.locator('[data-db]')).to_be_visible();self.page.go_back()
        expect(self.page.locator('.pname')).to_have_value('업무 프로젝트')
        self.page.locator('[data-view-back]').click()
        expect(self.page.locator('[data-open="work-p"]')).to_be_visible()
        self.page.go_back();expect(self.page.locator('[data-archive-month]')).to_have_value('2026-10')

    def test_mobile_calendar_targets_and_project_history_are_manageable(self):
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.locator("nav [data-tab='home']").click();self.page.locator('[data-cv="m"]').click()
        self.assertLess(self.page.locator('.mg').bounding_box()['height'],400)
        self.assertLess(self.page.locator('.dside').bounding_box()['y'],760)
        self.page.locator('[data-day-add]').click();expect(self.page.locator('#qah')).to_have_value('')
        self.page.locator('[data-qax]').click()
        self.link_task();self.project()
        box=self.page.locator('[data-ck="work-t"]').bounding_box();self.assertGreaterEqual(min(box['width'],box['height']),44)
        self.mutate("for(let i=0;i<20;i++)await m.setDoc(ref('notes','history-'+i),{pid:'work-p',space:'work',date:'2026-10-15',created:i,title:'관련 글 '+i,html:'<div>관련 내용</div>'});")
        self.page.locator('[data-zoom="near"]').click()
        expect(self.page.locator('.project-records .archive-row')).to_have_count(6)
        self.page.locator('[data-project-record-more]').click()
        expect(self.page.locator('.project-records .archive-row')).to_have_count(18)
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)

    def test_record_capture_can_pin_and_search_empty_state_offers_next_steps(self):
        self.page.locator('[data-record-new]').click();self.page.locator('#record-body').fill('핵심으로 고정할 기록')
        self.page.locator('#record-project').select_option('work-p');self.page.locator('#record-pin').check();self.page.locator('[data-record-save]').click()
        self.page.wait_for_function("window.__store.moms.some(m=>m.t==='핵심으로 고정할 기록'&&m.pinned)")
        self.project();expect(self.page.locator('.pm-core')).to_contain_text('핵심으로 고정할 기록')
        self.search('바닷가 산책');expect(self.page.locator('#sqr')).to_contain_text('WORK에서')
        self.page.locator('[data-search-space]').click();expect(self.page.locator('#sqr [data-sgo="mom"]')).to_have_count(1)

    def test_calendar_form_draft_restores_title_period_and_project_after_reload(self):
        self.page.locator("nav [data-tab='home']").click();self.page.locator('[data-cv="m"]').click()
        self.page.locator('[data-cadd2="2026-10-20"]').click();self.page.locator('[data-qt="ev"]').click()
        self.page.locator('#qat').fill('보관할 여행 일정');self.page.locator('#qad-end').fill('2026-10-23')
        self.page.locator('[data-qdd]').click();self.page.locator('[data-qp="work-p"]').click()
        self.page.locator('[data-qax]').click();self.page.reload()
        self.page.locator('[data-cadd2="2026-10-20"]').click()
        expect(self.page.locator('#qat')).to_have_value('보관할 여행 일정');expect(self.page.locator('#qad-end')).to_have_value('2026-10-23')
        expect(self.page.locator('[data-qdd]')).to_contain_text('업무 프로젝트')
        self.page.locator('[data-qasave]').click();self.page.wait_for_function("window.__store.todos.some(t=>t.title==='보관할 여행 일정')")
        self.page.locator('[data-cadd2="2026-10-20"]').click();expect(self.page.locator('#qat')).to_have_value('')

    def test_editing_title_does_not_undo_a_completion_from_another_device(self):
        self.search('보고서 제출');self.page.locator('#sqr [data-sgo="todo"]').click()
        self.page.locator('#e-t').fill('제목만 수정했어요')
        self.mutate("await m.updateDoc(ref('todos','work-t'),{done:true,doneDate:'2026-10-16',doneAt:1792108800000});")
        self.page.locator('[data-esave]').click();self.page.wait_for_function("window.__store.todos.find(t=>t.id==='work-t').title==='제목만 수정했어요'")
        self.assertTrue(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').done"))

    def test_malformed_backup_ids_and_counts_are_rejected_before_writes(self):
        self.import_file(self.backup())
        expect(self.page.locator('#backup-preview')).to_contain_text('추가할 기록 0개')
        for invalid in ['duplicate','count','path']:
            with self.subTest(invalid=invalid):
                backup=self.backup({'notes':[{'id':'new','title':'글','space':'work'}]})
                if invalid=='duplicate':backup['notes'].append(copy.deepcopy(backup['notes'][-1]));backup['counts']['notes']+=1
                elif invalid=='count':backup['counts']['notes']+=1
                else:backup['notes'][-1]['id']='other/record'
                self.import_file(backup,False)
                expect(self.page.locator('#backup-preview')).to_contain_text('백업')
                expect(self.page.locator('[data-backup-apply]')).to_be_disabled()
                self.assertFalse(self.page.evaluate("window.__store.notes.some(n=>n.id==='new')"))

    def backup(self, extra=None):
        data={c:copy.deepcopy(ui.SEED.get(c,[])) for c in ['todos','projects','notes','refs','ents','moms','logs','exps','fbk','imgs','trash']}
        if extra:
            for c,rows in extra.items():data[c].extend(rows)
        return {'app':'Arecmik','version':1,'complete':True,'counts':{c:len(rows) for c,rows in data.items()},**data}

    def import_file(self,data,open_menu=True):
        if open_menu:
            self.page.locator('[data-menu]').click();self.page.locator('[data-backup-import]').click()
        self.page.locator('#backup-file').set_input_files({'name':'Arecmik-backup.json','mimeType':'application/json','buffer':json.dumps(data,ensure_ascii=False).encode()})

    def test_backup_preview_and_restore_skip_existing_and_concurrent_records(self):
        backup=self.backup({'notes':[{'id':'missing','title':'백업 글','html':'<div>내용</div>','space':'work'},{'id':'raced','title':'옛 제목','space':'work'}]})
        original=self.page.evaluate('JSON.stringify(window.__store)')
        self.import_file(backup);expect(self.page.locator('#backup-preview')).to_contain_text('추가할 기록 2개')
        self.assertEqual(self.page.evaluate('JSON.stringify(window.__store)'),original)
        self.mutate("await m.setDoc(ref('notes','raced'),{title:'지금 새로 작성한 제목',space:'work'});")
        self.page.locator('[data-backup-apply]').click();self.page.wait_for_function("window.__store.notes.some(n=>n.id==='missing')")
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='raced').title"),'지금 새로 작성한 제목')
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='work-n').title"),'업무 회의록')
        self.import_file(backup);expect(self.page.locator('#backup-preview')).to_contain_text('추가할 기록 0개')
        expect(self.page.locator('[data-backup-apply]')).to_be_disabled()

    def test_partial_backup_is_rejected_and_interrupted_import_resumes(self):
        bad=self.backup();bad['complete']=False;self.import_file(bad)
        expect(self.page.locator('#backup-preview')).to_contain_text('전체 백업 파일')
        expect(self.page.locator('[data-backup-apply]')).to_be_disabled()
        data=self.backup({'todos':[{'id':'import-'+str(i),'title':'백업 할 일 '+str(i),'space':'work'} for i in range(101)],'projects':[{'id':'import-project','name':'백업 프로젝트','space':'work'}]})
        self.import_file(data,False);expect(self.page.locator('#backup-preview')).to_contain_text('추가할 기록 102개')
        self.page.evaluate("window.__failWritesFor='projects'");self.page.locator('[data-backup-apply]').click()
        expect(self.page.locator('#backup-preview')).to_contain_text('100개를 가져온 뒤 멈췄어요')
        self.page.evaluate('window.__failWritesFor=null');self.import_file(data,False)
        expect(self.page.locator('#backup-preview')).to_contain_text('추가할 기록 2개')
        self.page.locator('[data-backup-apply]').click();self.page.wait_for_function("window.__store.projects.some(p=>p.id==='import-project')")
        self.assertEqual(self.page.evaluate("window.__store.todos.filter(t=>t.id.startsWith('import-')).length"),101)


if __name__=='__main__':unittest.main()

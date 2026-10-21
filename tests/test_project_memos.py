"""Project history must remain recoverable and pins must share the original."""
import unittest

from playwright.sync_api import expect
import test_archive as ui


class ProjectMemoTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await m.updateDoc(m.doc(m.collection({},'moms'),'work-m'),{pid:'work-p'});
        }""")
        self.project()

    def project(self):
        self.page.locator("nav [data-tab='proj']").click()
        self.page.locator('[data-open="work-p"]').click()
        ui.project_details(self.page)
        expect(self.page.locator('.pmemo:not(.pcore)')).to_be_visible()

    def test_favorite_edit_original_and_remove_without_copying_or_losing_history(self):
        count = self.page.evaluate('window.__store.moms.length')
        expect(self.page.locator('[data-pmemo]')).to_contain_text('업무 프로젝트 메모')
        self.page.locator('[data-mpin="work-m"]').click()
        expect(self.page.locator('[data-mpin="work-m"]')).to_have_attribute('aria-pressed','true')
        self.page.locator('nav [data-tab="rec"]').click()
        self.page.locator('[data-archive-favorites]').click()
        self.page.locator('[data-archive-open="mom"][data-id="work-m"]').click()
        self.page.locator('#record-body').fill('회의 후 확정한 최종 조건')
        self.page.locator('[data-record-save]').click()
        expect(self.page.locator('.archive-list')).to_contain_text('회의 후 확정한 최종 조건')
        self.page.locator('[data-archive-favorite="mom"][data-id="work-m"]').click()
        expect(self.page.locator('.archive-empty')).to_contain_text('즐겨찾기가 없어요')
        self.project()
        expect(self.page.locator('[data-mt="work-m"]')).to_contain_text('회의 후 확정한 최종 조건')
        expect(self.page.locator('[data-pmemo]')).to_contain_text('업무 프로젝트 메모')
        self.assertEqual(self.page.evaluate('window.__store.moms.length'), count)

    def test_failed_quick_record_keeps_text_and_date_across_reload(self):
        self.page.locator('[data-pmi]').fill('아직 전송하지 못한 상담 기록')
        self.page.locator('[data-pmd]').fill('2026-10-12')
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-pmadd]').click()
        expect(self.page.locator('.toast')).to_contain_text('저장하지 못했어요')
        expect(self.page.locator('[data-pmi]')).to_have_value('아직 전송하지 못한 상담 기록')
        self.assertEqual(self.page.evaluate('window.__store.moms.length'), len(ui.SEED['moms']))
        self.page.reload()
        self.project()
        expect(self.page.locator('[data-pmi]')).to_have_value('아직 전송하지 못한 상담 기록')
        expect(self.page.locator('[data-pmd]')).to_have_value('2026-10-12')
        self.page.locator('[data-pmadd]').click()
        expect(self.page.locator('[data-pmi]')).to_have_value('')
        saved = self.page.evaluate("window.__store.moms.filter(m=>m.t==='아직 전송하지 못한 상담 기록')")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['d'], '2026-10-12')

    def test_visible_record_entry_with_core_off_and_full_editor_share_original(self):
        p=self.page
        p.evaluate("""async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.updateDoc(f.doc(f.collection({},'projects'),'work-p'),{mods:{memo:false}});} """)
        self.project()
        expect(p.locator('[data-pmemo]')).to_have_count(0)
        expect(p.locator('[data-layout-fold="history"]')).to_have_count(0)
        expect(p.locator('.layout-project-journal [data-pmi]')).to_be_visible()
        expect(p.locator('[data-mt="work-m"]')).to_be_visible()
        expect(p.locator('.project-records [data-archive-open="mom"]')).to_have_count(0)
        p.locator('.project-journal-head [data-record-new]').click()
        expect(p.locator('#record-project')).to_have_value('work-p')
        p.locator('#record-body').fill('프로젝트에서 자세히 남긴 결정')
        p.locator('[data-record-save]').click()
        expect(p.locator('.layout-project-journal')).to_contain_text('프로젝트에서 자세히 남긴 결정')
        self.assertEqual(p.evaluate("window.__store.moms.filter(m=>m.t==='프로젝트에서 자세히 남긴 결정').length"),1)
        p.locator('.project-journal-head [data-project-record-all]').click()
        expect(p.locator('.archive-list')).to_contain_text('프로젝트에서 자세히 남긴 결정')
        expect(p.locator('[data-archive-project]')).to_have_value('work-p')
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(0)

    def test_legacy_photos_remain_visible_and_inline_edits_do_not_duplicate_them(self):
        p=self.page
        p.evaluate("""async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.setDoc(f.doc(f.collection({},'imgs'),'project-photo'),{d:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1XcAAAAASUVORK5CYII='});await f.updateDoc(f.doc(f.collection({},'moms'),'work-m'),{imgs:['project-photo']});} """)
        self.project()
        photo=p.locator('.pm-record-content img[data-img="project-photo"]')
        expect(photo).to_have_count(1)
        p.wait_for_function("document.querySelector('.pm-record-content img')?.naturalWidth>0")
        p.locator('[data-mt="work-m"]').fill('사진과 함께 남긴 최종 결정')
        p.wait_for_function("window.__store.moms.find(m=>m.id==='work-m').t==='사진과 함께 남긴 최종 결정'")
        saved=p.evaluate("window.__store.moms.find(m=>m.id==='work-m')")
        self.assertEqual(saved['imgs'],['project-photo'])
        self.assertNotIn('data-img',saved['h'])
        p.reload();self.project()
        expect(p.locator('.pm-record-content img[data-img="project-photo"]')).to_have_count(1)
        expect(p.locator('[data-mt="work-m"]')).to_contain_text('사진과 함께 남긴 최종 결정')

    def test_inline_edit_failure_can_be_recovered_after_reload(self):
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-mt="work-m"]').fill('저장 실패에도 보존할 중요한 변경')
        expect(self.page.locator('#save-status')).to_contain_text('저장되지 않은 편집')
        self.page.reload()
        self.page.locator('[data-local-recovery]').click()
        expect(self.page.locator('.recovery-preview')).to_contain_text('저장 실패에도 보존할 중요한 변경')
        self.page.locator('[data-recover-edit]').click()
        expect(self.page.locator('[data-db]')).to_contain_text('저장 실패에도 보존할 중요한 변경')
        self.assertEqual(self.page.evaluate("window.__store.moms.find(m=>m.id==='work-m').t"), '업무 회의 회고')

    def test_delete_failure_preserves_original_and_success_can_be_undone(self):
        for failed_collection in ['trash', 'moms']:
            self.page.evaluate('(c)=>window.__failWritesFor=c', failed_collection)
            self.page.locator('[data-mdel="work-m"]').click()
            expect(self.page.locator('.toast')).to_contain_text('삭제하지 못했어요')
            expect(self.page.locator('[data-mt="work-m"]')).to_be_visible()
            self.assertEqual(self.page.evaluate('window.__store.trash.length'), 0)
        self.page.evaluate('window.__failWritesFor=null')
        self.page.locator('[data-mdel="work-m"]').click()
        expect(self.page.locator('[data-mt="work-m"]')).to_have_count(0)
        self.assertEqual(self.page.evaluate('window.__store.trash.length'), 1)
        self.page.locator('.toast button').click()
        expect(self.page.locator('[data-mt="work-m"]')).to_contain_text('업무 회의 회고')

    def test_mobile_history_paginates_and_pin_failure_keeps_state(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          for(let i=0;i<15;i++)await m.setDoc(m.doc(m.collection({},'moms'),'history-'+i),{
            pid:'work-p',space:'work',d:'2026-10-14',at:i,t:'상담 기록 '+i
          });
        }""")
        self.page.locator('[data-pmfold]').click()
        self.page.locator('[data-pmfold]').click()
        expect(self.page.locator('.pmr')).to_have_count(5)
        self.page.locator('[data-pmmore]').click()
        expect(self.page.locator('.pmr')).to_have_count(16)
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-mpin="work-m"]').click()
        expect(self.page.locator('.toast')).to_contain_text('변경하지 못했어요')
        expect(self.page.locator('[data-mpin="work-m"]')).to_have_attribute('aria-pressed', 'false')
        self.page.locator('[data-pmfold]').click()
        expect(self.page.locator('.pmr')).to_have_count(0)
        expect(self.page.locator('[data-pmi]')).to_be_visible()

    def test_backdated_quick_record_is_visible_in_the_recent_list_without_losing_older_records(self):
        p=self.page
        p.evaluate("""async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');for(let i=0;i<8;i++)await f.setDoc(f.doc(f.collection({},'moms'),'later-'+i),{pid:'work-p',space:'work',d:'2026-10-20',t:'최근 진행 '+i,at:i});} """)
        expect(p.locator('.pmr')).to_have_count(5)
        p.locator('[data-pmd]').fill('2026-10-01')
        p.locator('[data-pmi]').fill('나중에 옮겨 적은 지난 결정')
        p.locator('[data-pmadd]').click()
        expect(p.locator('.pmr')).to_contain_text(['최근 진행 7','최근 진행 6','최근 진행 5','최근 진행 4','최근 진행 3','최근 진행 2','최근 진행 1','최근 진행 0','업무 회의 회고','나중에 옮겨 적은 지난 결정'])
        self.assertEqual(p.evaluate("window.__store.moms.filter(m=>m.pid==='work-p').length"),10)
        p.locator('.project-journal-head [data-record-new]').click()
        p.locator('#record-day').fill('2026-09-01')
        p.locator('#record-body').fill('자세히 쓰기로 옮긴 더 오래된 기록')
        p.locator('[data-record-save]').click()
        expect(p.locator('.pmr').last).to_contain_text('자세히 쓰기로 옮긴 더 오래된 기록')
        self.assertEqual(p.evaluate("window.__store.moms.filter(m=>m.pid==='work-p').length"),11)

    def test_unsaved_edit_blocks_delete_instead_of_losing_changes(self):
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-mt="work-m"]').fill('삭제 전에 보존해야 할 최신 내용')
        expect(self.page.locator('#save-status')).to_contain_text('저장되지 않은 편집')
        self.page.locator('[data-mdel="work-m"]').click()
        expect(self.page.locator('.toast')).to_contain_text('편집 내용을 먼저 저장')
        self.assertEqual(self.page.evaluate('window.__store.trash.length'), 0)
        self.assertTrue(self.page.evaluate("window.__store.moms.some(m=>m.id==='work-m')"))
        self.page.locator('[data-local-recovery]').click()
        expect(self.page.locator('.recovery-preview')).to_contain_text('삭제 전에 보존해야 할 최신 내용')

    def test_slow_save_and_view_changes_do_not_duplicate_new_record(self):
        self.page.evaluate('window.__writeDelayMs=700')
        self.page.locator('[data-pmi]').fill('한 번만 저장할 진행 기록')
        self.page.locator('[data-pmi]').press('Enter')
        self.page.locator('[data-pmfold]').click()
        self.page.locator('[data-pmi]').press('Enter')
        self.page.wait_for_function("window.__store.moms.some(m=>m.t==='한 번만 저장할 진행 기록')")
        expect(self.page.locator('[data-pmi]')).to_have_value('')
        self.assertEqual(self.page.evaluate("window.__store.moms.filter(m=>m.t==='한 번만 저장할 진행 기록').length"), 1)


if __name__ == '__main__':
    unittest.main()

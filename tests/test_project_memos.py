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
        expect(self.page.locator('.pmemo')).to_be_visible()

    def test_pin_edit_original_and_unpin_without_copying_or_losing_history(self):
        count = self.page.evaluate('window.__store.moms.length')
        expect(self.page.locator('[data-pmemo]')).to_contain_text('업무 프로젝트 메모')
        self.page.locator('[data-mpin="work-m"]').click()
        expect(self.page.locator('.pm-core')).to_contain_text('업무 회의 회고')
        self.assertEqual(self.page.evaluate('window.__store.moms.length'), count)
        self.page.locator('.pm-core-open').click()
        self.page.locator('#record-body').fill('상담 후 확정한 최종 조건')
        self.page.locator('[data-record-save]').click()
        expect(self.page.locator('.pm-core')).to_contain_text('상담 후 확정한 최종 조건')
        expect(self.page.locator('[data-mt="work-m"]')).to_contain_text('상담 후 확정한 최종 조건')
        self.page.locator('.pm-core [data-mpin="work-m"]').click()
        expect(self.page.locator('.pm-core-open')).to_have_count(0)
        expect(self.page.locator('[data-mt="work-m"]')).to_contain_text('상담 후 확정한 최종 조건')
        self.assertEqual(self.page.evaluate('window.__store.moms.length'), count)

    def test_failed_quick_record_keeps_text_and_date_across_reload(self):
        self.page.locator('[data-pmi]').fill('아직 전송하지 못한 상담 기록')
        self.page.locator('[data-pmd]').fill('2026-10-12')
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-pmi]').press('Enter')
        expect(self.page.locator('.toast')).to_contain_text('저장하지 못했어요')
        expect(self.page.locator('[data-pmi]')).to_have_value('아직 전송하지 못한 상담 기록')
        self.assertEqual(self.page.evaluate('window.__store.moms.length'), len(ui.SEED['moms']))
        self.page.reload()
        self.project()
        expect(self.page.locator('[data-pmi]')).to_have_value('아직 전송하지 못한 상담 기록')
        expect(self.page.locator('[data-pmd]')).to_have_value('2026-10-12')
        self.page.locator('[data-pmi]').press('Enter')
        expect(self.page.locator('[data-pmi]')).to_have_value('')
        saved = self.page.evaluate("window.__store.moms.filter(m=>m.t==='아직 전송하지 못한 상담 기록')")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['d'], '2026-10-12')

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
        expect(self.page.locator('.pmr')).to_have_count(12)
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

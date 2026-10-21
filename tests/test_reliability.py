"""Regression checks for interrupted writes, sync, money, dates, and backups."""
import json
from pathlib import Path
import unittest

from playwright.sync_api import expect
import test_archive as ui


class ReliabilityTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown
    life = ui.ArchiveTests.life
    search = ui.ArchiveTests.search

    def project(self):
        self.life()
        self.page.evaluate("""async () => {
          const m = await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await m.updateDoc(m.doc(m.collection({},'projects'),'life-p'), {
            tbl:{on:true,fields:[{k:'f1',n:'메모',t:'text'}]}
          });
          await m.setDoc(m.doc(m.collection({},'ents'),'life-row'), {
            pid:'life-p',title:'가구',v:{},items:[]
          });
        }""")
        self.page.locator("nav [data-tab='proj']").click()
        self.page.locator("[data-open='life-p']").click()
        ui.project_details(self.page)

    def test_record_draft_survives_dismissal_and_reload(self):
        ui.record_new(self.page)
        self.page.locator('#record-body').fill('실수로 닫아도 남아야 할 기록')
        self.page.locator('#scrim').click(position={'x': 5, 'y': 5})
        ui.record_new(self.page)
        expect(self.page.locator('#record-body')).to_contain_text('실수로 닫아도 남아야 할 기록')
        self.page.reload()
        ui.record_new(self.page)
        expect(self.page.locator('#record-body')).to_contain_text('실수로 닫아도 남아야 할 기록')
        self.page.locator('[data-record-save]').click()
        expect(self.page.locator('#scrim')).not_to_have_class('scrim on')
        self.assertEqual(self.page.evaluate("window.__store.moms.filter(m=>m.t.includes('실수로 닫아도')).length"), 1)
        self.assertEqual(self.page.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('arecmik:record:ui-test:')&&localStorage[k].includes('실수로 닫아도')).length"), 0)

    def test_new_title_is_saved_when_immediately_leaving(self):
        ui.record_source(self.page, 'doc')
        self.page.locator('button.newd[data-newdoc]').click()
        self.page.evaluate("""() => {
          const el = document.querySelector('.dt');
          el.value = '제목만 적은 소중한 기록';
          el.dispatchEvent(new Event('input',{bubbles:true}));
          document.querySelector('[data-closedoc]').click();
        }""")
        self.page.wait_for_function("window.__store.notes.some(n=>n.title==='제목만 적은 소중한 기록')")
        self.assertEqual(self.page.evaluate('window.__store.notes.length'), len(ui.SEED['notes']) + 1)

    def test_reload_keeps_last_edit_and_recovers_without_overwrite(self):
        self.page.locator("[data-archive-open='doc'][data-id='work-n']").click()
        self.page.locator('[data-db]').fill('이미 저장한 문장')
        self.page.wait_for_function("window.__store.notes.find(n=>n.id==='work-n').html.includes('이미 저장한 문장')")
        self.page.evaluate("""() => {
          const el = document.querySelector('[data-db]');
          el.innerHTML = '<div>방금 덧붙인 중요한 문장</div>';
          el.dispatchEvent(new Event('input',{bubbles:true}));
          location.reload();
        }""")
        self.page.wait_for_load_state('load')
        # A pagehide write may finish; otherwise the local recovery must retain it.
        self.page.wait_for_function("window.__store?.notes?.some(n=>n.id==='work-n')")
        saved = self.page.evaluate("window.__store.notes.find(n=>n.id==='work-n').html")
        if '방금 덧붙인' not in saved:
            self.page.locator('[data-local-recovery]').click()
            expect(self.page.locator('.recovery-preview')).to_contain_text('방금 덧붙인 중요한 문장')
            self.page.locator('[data-recover-edit]').click()
            expect(self.page.locator('[data-db]')).to_contain_text('방금 덧붙인 중요한 문장')
            original = self.page.evaluate("window.__store.notes.find(n=>n.id==='work-n').html")
            self.assertIn('이미 저장한 문장', original)

    def test_pending_edit_is_recoverable_after_write_failure(self):
        self.page.locator("[data-archive-open='doc'][data-id='work-n']").click()
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-db]').fill('서버에 보내지 못한 글')
        expect(self.page.locator('#save-status')).to_contain_text('저장되지 않은 편집')
        self.page.reload()
        self.page.locator('[data-local-recovery]').click()
        expect(self.page.locator('.recovery-preview')).to_contain_text('서버에 보내지 못한 글')
        self.page.locator('[data-recover-edit]').click()
        expect(self.page.locator('[data-db]')).to_contain_text('서버에 보내지 못한 글')
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='work-n').html"), '<div>중요한 결정</div>')

    def test_realtime_update_and_view_changes_keep_unsubmitted_task(self):
        self.project()
        self.page.locator('#pq-t').fill('아직 입력 중인 할 일')
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await m.addDoc(m.collection({},'refs'),{title:'다른 기기 자료',space:'life',html:''});
        }""")
        self.page.locator('[data-zoom="near"]').click()
        expect(self.page.locator('#pq-t')).to_have_value('아직 입력 중인 할 일')
        self.page.locator('[data-sp="work"]').click()
        self.page.locator('[data-open="work-p"]').click()
        ui.project_details(self.page)
        expect(self.page.locator('#pq-t')).to_have_value('')
        self.page.locator('[data-sp="life"]').click()
        self.page.locator('[data-open="life-p"]').click()
        ui.project_details(self.page)
        expect(self.page.locator('#pq-t')).to_have_value('아직 입력 중인 할 일')

    def test_expense_amount_is_not_a_product_model_or_count(self):
        self.project()
        for text, amount in [('아이폰 16 120만', 1200000), ('커피 2잔 1만원', 10000), ('1500 점심', 1500), ('노트 1,200원', 1200)]:
            with self.subTest(text=text):
                count = self.page.evaluate('window.__store.exps.length')
                field = self.page.locator('[data-pci="life-p"]')
                field.fill(text)
                field.press('Enter')
                self.page.wait_for_function('(n)=>window.__store.exps.length===n', arg=count+1)
                self.assertEqual(self.page.evaluate('window.__store.exps.at(-1).a'), amount)
                expect(field).to_have_value('')

    def test_thousands_separator_and_batch_payments(self):
        self.project()
        self.page.locator('[data-hrow="life-row"]').click()
        field = self.page.locator('[data-hia="life-row"]')
        field.fill('소파 1,200')
        field.press('Enter')
        self.page.wait_for_function("window.__store.ents[0].items.length===1")
        self.assertEqual(self.page.evaluate('window.__store.ents[0].items[0].a'), 1200)
        payment = self.page.locator('[data-hrpay="life-row"]')
        payment.fill('계약금 50만, 금액 없는 잔금')
        payment.press('Enter')
        expect(self.page.locator('.toast')).to_contain_text('금액을 하나씩')
        self.assertEqual(self.page.evaluate('window.__store.exps.length'), len(ui.SEED['exps']))
        payment.fill('계약금 50만, 잔금 100만')
        self.page.evaluate("window.__failWritesFor='exps'")
        payment.press('Enter')
        expect(self.page.locator('.toast')).to_contain_text('저장하지 못했어요')
        expect(payment).to_have_value('계약금 50만, 잔금 100만')
        self.assertEqual(self.page.evaluate('window.__store.exps.length'), len(ui.SEED['exps']))
        self.page.evaluate('window.__failWritesFor=null')
        payment.press('Enter')
        expect(payment).to_have_value('')
        self.assertEqual(self.page.evaluate('window.__store.exps.length'), len(ui.SEED['exps']) + 2)

    def test_failed_task_and_expense_edit_stay_open_for_retry(self):
        self.search('보고서 제출')
        self.page.locator('#sqr [data-sgo="todo"]').click()
        self.page.locator('#e-t').fill('수정한 보고서 제목')
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-esave]').click()
        expect(self.page.locator('#scrim')).to_have_class('scrim on')
        expect(self.page.locator('[data-esave]')).to_be_enabled()
        expect(self.page.locator('#e-t')).to_have_value('수정한 보고서 제목')
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').title"), '보고서 제출')
        self.page.evaluate('window.__failWrites=false')
        self.page.locator('[data-esave]').click()
        expect(self.page.locator('#scrim')).not_to_have_class('scrim on')
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='work-t').title"), '수정한 보고서 제목')
        if self.page.locator('#srch.on').count():
            self.page.keyboard.press('Escape')
        self.life()
        self.search('숙박 결제')
        self.page.locator('#sqr [data-sgo="expense"]').click()
        self.page.locator('#x-t').fill('수정한 숙박 결제')
        self.page.evaluate('window.__failWrites=true')
        self.page.locator('[data-xsave]').click()
        expect(self.page.locator('#x-t')).to_have_value('수정한 숙박 결제')
        expect(self.page.locator('[data-xsave]')).to_be_enabled()
        expect(self.page.locator('#scrim')).to_have_class('scrim on')

    def test_invalid_dates_are_rejected_without_clearing_input(self):
        self.project()
        count = self.page.evaluate('window.__store.todos.length')
        for text in ['2/31 병원 가기', '13/1 여행 준비']:
            self.page.locator('#pq-t').fill(text)
            self.page.locator('#pq-t').press('Enter')
            expect(self.page.locator('.toast')).to_contain_text('없는 날짜')
            expect(self.page.locator('#pq-t')).to_have_value(text)
            self.assertEqual(self.page.evaluate('window.__store.todos.length'), count)

    def test_partial_backup_is_blocked_and_complete_backup_has_counts(self):
        downloads = []
        self.page.on('download', lambda download: downloads.append(download))
        self.page.evaluate("window.__failRead='exps'")
        self.page.locator('[data-menu]').click()
        self.page.locator('[data-backup]').click()
        expect(self.page.locator('.toast')).to_contain_text('백업에 실패했어요')
        self.assertEqual(downloads, [])
        self.page.evaluate('window.__failRead=null')
        self.page.locator('[data-menu]').click()
        with self.page.expect_download() as result:
            self.page.locator('[data-backup]').click()
        backup = json.loads(Path(result.value.path()).read_text())
        self.assertTrue(backup['complete'])
        self.assertEqual(len(backup['exps']), len(ui.SEED['exps']))
        for name, count in backup['counts'].items():
            self.assertEqual(len(backup[name]), count)


if __name__ == '__main__':
    unittest.main()

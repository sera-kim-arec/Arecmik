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

    def test_single_classification_and_composed_search_have_recoverable_empty_state(self):
        self.patch('notes','work-n',{'pid':'work-p'})
        self.patch('projects','other-work',{'name':'다른 업무','space':'work','status':'active'})
        p=self.page
        expect(p.locator('[aria-label="기록 분류"]')).to_have_count(1)
        expect(p.locator('.rh [data-rt]')).to_have_count(0)
        p.locator('[data-archive-filter="doc"]').click();p.locator('#rq').fill('중요한 결정')
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
        p=self.page;p.locator('[data-archive-filter="doc"]').click();p.locator('#rq').fill('회의록')
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        p.locator('[data-rt="doc"]').click()
        expect(p.locator('[data-folder-manage]')).to_be_visible()
        p.go_back()
        expect(p.locator('#rq')).to_have_value('회의록')
        expect(p.locator('[data-archive-filter="doc"]')).to_have_attribute('aria-pressed','true')
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)

    def test_new_record_and_reference_are_visible_after_writing_under_other_filters(self):
        p=self.page;p.locator('[data-archive-filter="expense"]').click()
        ui.record_new(p);p.locator('#record-body').fill('새 기록을 필터 뒤에 숨기지 않기')
        p.locator('[data-record-save]').click()
        expect(p.locator('.archive-list')).to_contain_text('새 기록을 필터 뒤에 숨기지 않기')
        p.locator('[data-archive-filter="doc"]').click()
        p.locator('.layout-write>summary').click();p.locator('.layout-write [data-newref]').click()
        p.locator('#r-t').fill('새 자료도 바로 보여요');p.locator('#r-b').fill('기억할 자료 내용');p.locator('[data-rsave]').click()
        expect(p.locator('.archive-list')).to_contain_text('새 자료도 바로 보여요')
        self.assertEqual(p.evaluate("window.__store.refs.filter(r=>r.title==='새 자료도 바로 보여요').length"),1)

    def test_journal_and_long_document_use_original_editors_and_remain_findable(self):
        p=self.page;p.locator('.layout-write>summary').click();p.locator('[data-journal-write]').click()
        editor=p.locator('[data-log][contenteditable]').first
        editor.fill('정리된 화면에서도 원래 일지를 저장해요')
        p.locator('[data-rt="archive"]').click();p.locator('[data-archive-filter="log"]').click()
        expect(p.locator('.archive-list')).to_contain_text('정리된 화면에서도 원래 일지를 저장해요')
        p.locator('.layout-write>summary').click();p.locator('.layout-write [data-newdoc]').click()
        p.locator('.dt').fill('원래 문서 편집기의 긴 글');p.locator('[data-db]').fill('폴더와 프로젝트에 연결할 본문')
        p.locator('nav [data-tab="rec"]').click();p.locator('[data-archive-filter="doc"]').click()
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

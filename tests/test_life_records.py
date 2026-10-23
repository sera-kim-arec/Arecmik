"""Personal experiences and reusable scraps keep separate writing/find flows."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class LifeRecordTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    patch=editors.BlockEditorTests.patch

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        self.page.locator('[data-sp="life"]').click()

    def filter(self,value):
        ui.reveal(self.page,'[data-archive-record-type]')
        self.page.locator('[data-archive-record-type]').select_option(value)

    def open_record(self):
        self.search('바닷가 산책');self.page.locator('#sqr [data-sgo="mom"]').click()

    def stored(self,c,id):
        return self.page.evaluate('([c,id])=>__store[c].find(x=>x.id===id)',[c,id])

    def test_book_and_movie_records_save_and_can_be_found_by_kind(self):
        p=self.page
        for kind,title in [('book','책을 읽고 남긴 나의 생각'),('movie','영화를 보고 남긴 감상')]:
            ui.record_new(p);p.locator('#record-body').fill(title);p.locator('#record-type').select_option(kind);p.locator('[data-record-save]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
            saved=p.evaluate('title=>__store.moms.find(m=>m.t===title)',title);self.assertEqual(saved['recordType'],kind);self.assertEqual(saved['space'],'life')
            p.locator('[data-archive-filter=""]').click();self.filter(kind);expect(p.locator('.archive-list .archive-row')).to_have_count(1);expect(p.locator('.archive-list')).to_contain_text(title)
            p.locator('.archive-row').click();expect(p.locator('#record-type')).to_have_value(kind);p.locator('#sheet [data-sx]').click();p.locator('[data-archive-filter=""]').click()
        self.search('독서');expect(p.locator('#sqr [data-sgo="mom"]')).to_have_count(1);expect(p.locator('#sqr')).to_contain_text('책을 읽고 남긴')

    def test_legacy_content_is_not_guessed_or_rewritten_and_journals_remain_daily(self):
        p=self.page;before=p.evaluate('JSON.stringify(__store)');self.filter('unclassified');expect(p.locator('.archive-list')).to_contain_text('바닷가 산책');expect(p.locator('.archive-list')).not_to_contain_text('즐거웠던 하루');self.filter('daily');expect(p.locator('.archive-list')).to_contain_text('즐거웠던 하루');expect(p.locator('.archive-list')).not_to_contain_text('여행 자료');self.assertEqual(p.evaluate('JSON.stringify(__store)'),before)
        p.locator('[data-sp="work"]').click();expect(p.locator('[data-archive-record-type]')).to_have_count(0);ui.record_new(p);expect(p.locator('#record-type')).to_have_count(0);p.locator('#sheet [data-sx]').click()

    def test_scrap_is_captured_in_library_and_stays_out_of_personal_record_feed(self):
        p=self.page;p.locator('[data-archive-filter="ref"]').click();expect(p.locator('.layout-write-group>[data-newref]')).to_have_text('＋ 자료 보관');p.locator('.layout-write-group>[data-newref]').click();expect(p.locator('#record-type')).to_have_count(0);expect(p.locator('#r-space')).to_have_value('life');p.locator('#r-t').fill('관점을 넓혀 준 인터뷰');p.locator('#r-b').fill('다시 읽을 질문과 인사이트');p.locator('[data-rsave]').click();expect(p.locator('.archive-list')).to_contain_text('관점을 넓혀 준 인터뷰')
        p.locator('[data-archive-filter=""]').click();expect(p.locator('.archive-list')).not_to_contain_text('관점을 넓혀 준 인터뷰');self.search('인사이트');expect(p.locator('#sqr [data-sgo="ref"]')).to_have_count(1);self.assertEqual(p.evaluate("__store.moms.filter(m=>m.t.includes('인터뷰')).length"),0)

    def test_type_filter_resets_for_library_and_work_and_new_records_use_current_type(self):
        p=self.page;self.filter('book');ui.record_new(p);expect(p.locator('#record-type')).to_have_value('book');p.locator('#record-body').fill('지금 읽은 책에서 떠올린 것');p.locator('[data-record-save]').click();expect(p.locator('.archive-list')).to_contain_text('지금 읽은 책에서 떠올린 것');self.filter('book');p.locator('[data-archive-filter="ref"]').click();expect(p.locator('.archive-list')).to_contain_text('여행 자료');expect(p.locator('[data-archive-record-type]')).to_have_count(0)
        p.locator('[data-archive-filter=""]').click();ui.reveal(p,'[data-archive-record-type]');expect(p.locator('[data-archive-record-type]')).to_have_value('');p.locator('[data-sp="work"]').click();expect(p.locator('.archive-list')).to_contain_text('업무 회의 회고');expect(p.locator('.archive-list')).not_to_contain_text('지금 읽은 책에서 떠올린 것')

    def test_record_type_draft_and_failure_keep_content_and_choice(self):
        p=self.page;ui.record_new(p);p.locator('#record-body').fill('저장 실패 후에도 남을 영화 감상');p.locator('#record-type').select_option('movie');p.evaluate('window.__failWrites=true');p.locator('[data-record-save]').click();expect(p.locator('.toast')).to_contain_text('저장하지 못했어요');expect(p.locator('#record-type')).to_have_value('movie');p.locator('#sheet [data-sx]').click();p.reload();ui.record_new(p);expect(p.locator('#record-type')).to_have_value('movie');expect(p.locator('#record-body')).to_contain_text('저장 실패 후에도');p.locator('[data-record-save]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(p.evaluate("__store.moms.filter(m=>m.t.includes('실패 후에도')&&m.recordType==='movie').length"),1)

    def test_body_only_save_preserves_remote_type_and_concurrent_type_edits_conflict(self):
        p=self.page;self.open_record();p.locator('#record-body').fill('휴대폰 분류를 보존할 내 본문');self.patch('moms','life-m',{'recordType':'book'});p.locator('[data-record-save]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(self.stored('moms','life-m')['recordType'],'book')
        self.search('휴대폰 분류');p.locator('#sqr [data-sgo="mom"]').click();p.locator('#record-type').select_option('movie');self.patch('moms','life-m',{'recordType':'daily'});p.locator('[data-record-save]').click();expect(p.locator('.save-conflict')).to_be_visible();self.assertEqual(self.stored('moms','life-m')['recordType'],'daily')

    def test_long_article_type_autosaves_without_changing_other_fields_and_is_filterable(self):
        p=self.page;self.search('숙소 후보');p.locator('#sqr [data-sgo="doc"]').click();p.locator('[data-dtype]').select_option('movie');p.wait_for_function("__store.notes.find(n=>n.id==='life-n').recordType==='movie'");self.assertEqual(self.stored('notes','life-n')['html'],'<div>조용한 바닷가</div>');p.locator('nav [data-tab="rec"]').click();self.filter('movie');expect(p.locator('.archive-list .archive-row')).to_have_count(1);expect(p.locator('.archive-list')).to_contain_text('숙소 후보');expect(p.locator('.archive-list .archive-kind')).to_have_text('영화 기록')

    def test_old_record_draft_without_type_field_does_not_clear_saved_type(self):
        p=self.page;self.open_record();p.locator('#record-body').fill('이전 버전에 쓰던 내 기록');p.locator('#sheet [data-sx]').click();p.evaluate("()=>{const key='arecmik:record:ui-test:life:life-m',draft=JSON.parse(localStorage.getItem(key));delete draft.recordType;delete draft.guard.initialFields['record-type'];localStorage.setItem(key,JSON.stringify(draft))}");self.patch('moms','life-m',{'recordType':'book'});self.open_record();expect(p.locator('#record-type')).to_have_value('book');p.locator('[data-record-save]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(self.stored('moms','life-m')['recordType'],'book');self.assertIn('이전 버전',self.stored('moms','life-m')['h'])

    def test_small_phone_and_desktop_forms_and_filters_fit_without_extra_required_fields(self):
        p=self.page
        for index,width in enumerate([320,390,1365]):
            p.set_viewport_size({'width':width,'height':900});self.filter('book');self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width);ui.record_new(p);expect(p.locator('#record-type')).to_have_value('book' if index==0 else '');self.assertGreaterEqual(p.locator('#record-type').bounding_box()['height'],44);self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width);p.locator('#record-type').select_option('');p.locator('#sheet [data-sx]').click()


if __name__=='__main__':unittest.main()

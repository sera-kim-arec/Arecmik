"""Real archive UI: original identities, safe reclassification, and library retrieval.

Firebase is the shared in-memory adapter; no personal account is accessed.
"""
import unittest
from pathlib import Path
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class ArchiveLibraryTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown
    patch = editors.BlockEditorTests.patch
    search = ui.ArchiveTests.search

    def library(self):
        self.page.locator('[data-archive-filter="ref"]').click()
        expect(self.page.locator('.archive-library')).to_be_visible()

    def records(self):
        self.page.locator('[data-archive-filter=""]').click()

    def folders(self):
        self.patch('notes', 'root', {'title':'인사', 'space':'work', 'isFolder':True})
        self.patch('notes', 'child', {'title':'입사 안내', 'space':'work', 'isFolder':True, 'fid':'root'})
        self.patch('notes', 'private', {'title':'나의 독서', 'space':'life', 'isFolder':True})
        self.patch('notes', 'work-n', {'fid':'child', 'archivePurpose':'resource'})
        self.patch('refs', 'work-r', {'fid':'child'})

    def stored(self, collection, ident):
        return self.page.evaluate('([c,id])=>__store[c].find(x=>x.id===id)', [collection, ident])

    def test_two_purposes_do_not_rewrite_or_copy_existing_content(self):
        p=self.page; before=p.evaluate('JSON.stringify(__store)')
        expect(p.locator('.layout-record-types>button')).to_have_count(2)
        expect(p.locator('.archive-list')).to_contain_text('업무 회의록')
        expect(p.locator('.archive-list')).not_to_contain_text('업무 자료')
        self.library();expect(p.locator('.archive-list')).to_contain_text('기존 자료')
        expect(p.locator('.archive-list')).not_to_contain_text('업무 회의록')
        self.assertEqual(p.evaluate('JSON.stringify(__store)'), before)

    def test_article_reclassification_keeps_original_id_editor_and_project_connections(self):
        p=self.page
        self.patch('notes','work-n',{'pid':'work-p','custom':'보존','connections':[{'c':'moms','id':'work-m'}]})
        before=self.stored('notes','work-n')
        p.locator('[data-archive-open="doc"][data-id="work-n"]').click()
        p.locator('[data-dpurpose]').select_option('resource')
        p.wait_for_function("__store.notes.find(x=>x.id==='work-n').archivePurpose==='resource'")
        p.locator('[data-closedoc]').click()
        expect(p.locator('.archive-list [data-id="work-n"]')).to_have_count(0)
        self.library();p.locator('[data-archive-open="doc"][data-id="work-n"]').click()
        expect(p.locator('[data-db]')).to_contain_text('중요한 결정')
        expect(p.locator('[data-dpurpose]')).to_have_value('resource')
        after=self.stored('notes','work-n');after.pop('archivePurpose');after.pop('updated')
        self.assertEqual(after,before)
        self.assertEqual(p.evaluate('__store.notes.length'),len(ui.SEED['notes']))

    def test_library_contains_parent_descendants_and_unfiled_without_other_space(self):
        p=self.page;self.folders();self.library()
        p.locator('[data-archive-folder="root"]').click()
        expect(p.locator('.archive-list .archive-row')).to_have_count(2)
        expect(p.locator('.archive-list')).to_contain_text('업무 회의록')
        expect(p.locator('.archive-list')).to_contain_text('업무 자료')
        expect(p.locator('.archive-navigation')).not_to_contain_text('나의 독서')
        p.locator('[data-archive-folder="none"]').click()
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        expect(p.locator('.archive-list')).to_contain_text('기존 자료')

    def test_old_favorite_is_promoted_before_recent_page_and_not_duplicated(self):
        p=self.page
        self.patch('refs','legacy-r',{'fav':True,'created':1})
        for i in range(42):self.patch('refs','new-'+str(i),{'title':'최근 자료 '+str(i),'space':'work','created':ui.STAMP+i})
        self.library()
        expect(p.locator('.archive-section-title').first).to_contain_text('자주 꺼내 보는 자료')
        expect(p.locator('.archive-list .archive-row').first).to_have_attribute('data-id','legacy-r')
        expect(p.locator('.archive-list [data-archive-open="ref"][data-id="legacy-r"]')).to_have_count(1)
        p.locator('[data-archive-more]').click()
        expect(p.locator('.archive-list .archive-row')).to_have_count(44)

    def test_favorites_and_search_are_scoped_but_global_search_finds_both(self):
        p=self.page;self.patch('moms','work-m',{'pinned':True});self.patch('refs','work-r',{'fav':True})
        p.locator('[data-archive-favorites]').click();expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        expect(p.locator('.archive-list')).to_contain_text('업무 회의 회고')
        self.library();p.locator('[data-archive-favorites]').click();expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        expect(p.locator('.archive-list')).to_contain_text('업무 자료')
        self.records();p.locator('#rq').fill('팀 연락처')
        expect(p.locator('.archive-empty')).to_contain_text('조건에 맞는 기록이 없어요')
        self.search('팀 연락처');expect(p.locator('#sqr [data-sgo="ref"]')).to_have_count(1)

    def test_resource_reader_keeps_list_search_folder_and_browser_back(self):
        p=self.page;self.folders();self.library();p.locator('[data-archive-folder="root"]').click();p.locator('#rq').fill('팀 연락처')
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
        expect(p.locator('#r-folder')).to_have_value('child')
        p.go_back();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        expect(p.locator('#rq')).to_have_value('팀 연락처')
        expect(p.locator('[data-archive-folder="root"]')).to_have_attribute('aria-pressed','true')
        p.go_back();expect(p.locator('[data-archive-folder=""]')).to_have_attribute('aria-pressed','true')

    def test_quick_capture_uses_selected_folder_derives_title_and_keeps_block_editor(self):
        p=self.page;self.folders();self.library();p.locator('[data-archive-folder="child"]').click()
        p.locator('.layout-write-group>[data-newref]').click()
        expect(p.locator('#r-folder')).to_have_value('child')
        p.locator('#r-b').fill('다시 쓸 입사 안내문\nhttps://example.com')
        p.evaluate('window.__failWrites=true');p.locator('[data-rsave]').click()
        expect(p.locator('#r-b')).to_contain_text('다시 쓸 입사 안내문')
        p.locator('#sheet [data-sx]').click()
        p.locator('.layout-write-group>[data-newref]').click()
        expect(p.locator('#r-folder')).to_have_value('child');expect(p.locator('#r-b')).to_contain_text('입사 안내문')
        p.evaluate('window.__failWrites=false');p.locator('[data-rsave]').click()
        expect(p.locator('#scrim')).not_to_have_class('scrim on')
        saved=p.evaluate("__store.refs.find(x=>x.title==='다시 쓸 입사 안내문')")
        self.assertEqual((saved['fid'],saved['archivePurpose']),('child','resource'))
        self.assertIn('https://example.com',saved['html'])

    def test_long_article_created_in_library_uses_current_folder_without_a_copy(self):
        p=self.page;self.folders();self.library();p.locator('[data-archive-folder="child"]').click()
        before=p.evaluate('__store.notes.length')
        p.locator('.layout-write>summary').click();p.locator('.layout-write [data-newdoc]').click()
        expect(p.locator('[data-dpurpose]')).to_have_value('resource')
        expect(p.locator('[data-dfold]')).to_have_value('child')
        p.locator('.dt').fill('다시 읽을 업무 안내');p.locator('[data-db]').fill('기존 블록 편집기로 쓴 안내문')
        p.locator('[data-closedoc]').click()
        expect(p.locator('.archive-library')).to_be_visible()
        expect(p.locator('.archive-list')).to_contain_text('다시 읽을 업무 안내')
        p.wait_for_function("__store.notes.some(x=>x.title==='다시 읽을 업무 안내'&&x.html.includes('안내문'))")
        self.assertEqual(p.evaluate('__store.notes.length'),before+1)
        self.assertEqual(p.evaluate("__store.notes.find(x=>x.title==='다시 읽을 업무 안내').archivePurpose"),'resource')

    def test_resource_can_be_reclassified_without_losing_remote_body_or_favorite(self):
        p=self.page;self.patch('refs','work-r',{'fav':True,'custom':'원본'});self.library()
        p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
        p.locator('#r-purpose').select_option('record')
        self.patch('refs','work-r',{'html':'<div>휴대폰에서 수정한 내용</div>'})
        p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        expect(p.locator('.archive-list [data-id="work-r"]')).to_have_count(0)
        self.records();expect(p.locator('.archive-list')).to_contain_text('휴대폰에서 수정한 내용')
        saved=self.stored('refs','work-r');self.assertEqual(saved['archivePurpose'],'record');self.assertTrue(saved['fav']);self.assertEqual(saved['custom'],'원본')

    def test_conflicting_resource_purpose_preserves_draft_and_remote_choice(self):
        p=self.page;self.patch('refs','work-r',{'archivePurpose':'resource'});self.library()
        p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
        p.locator('#r-purpose').select_option('record');p.locator('#r-b').fill('내가 쓰던 내용')
        self.patch('refs','work-r',{'archivePurpose':'record'})
        # A concurrent same-value change is safe; a new local reversal conflicts.
        p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        self.records();p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
        p.locator('#r-purpose').select_option('resource')
        # A previous client clearing an explicit classification is a distinct edit.
        self.patch('refs','work-r',{'archivePurpose':''})
        p.locator('[data-rsave]').click();expect(p.locator('.save-conflict')).to_be_visible()
        expect(p.locator('#r-b')).to_contain_text('내가 쓰던 내용')
        self.assertEqual(self.stored('refs','work-r')['archivePurpose'],'')

    def test_old_resource_draft_missing_purpose_preserves_remote_classification(self):
        p=self.page;self.library();p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
        p.locator('#r-b').fill('이전 버전의 작성 내용');p.locator('#sheet [data-sx]').click()
        p.evaluate("()=>{const key='arecmik:form:ui-test:ref:work-r',d=JSON.parse(localStorage.getItem(key));delete d.fields['r-purpose'];delete d.guard.initialFields['r-purpose'];localStorage.setItem(key,JSON.stringify(d))}")
        self.patch('refs','work-r',{'archivePurpose':'record'});self.records()
        p.locator('[data-archive-open="ref"][data-id="work-r"]').click();expect(p.locator('#r-purpose')).to_have_value('record')
        p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        self.assertEqual(self.stored('refs','work-r')['archivePurpose'],'record')

    def test_inline_new_folder_stays_in_library_and_reloads_with_saved_material(self):
        p=self.page;self.library();p.locator('.archive-folder-heading [data-newf]').click()
        p.locator('#folder-title').fill('참고 문서');p.locator('[data-folder-create]').click()
        expect(p.locator('.archive-library')).to_be_visible();folder=p.evaluate("__store.notes.find(x=>x.isFolder&&x.title==='참고 문서')")
        expect(p.locator('[data-archive-folder="'+folder['id']+'"]').first).to_have_attribute('aria-pressed','true')
        p.locator('.layout-write-group>[data-newref]').click();expect(p.locator('#r-folder')).to_have_value(folder['id'])
        p.locator('#r-b').fill('다음에 찾을 안내문');p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        p.reload();self.library();expect(p.locator('.archive-list')).to_contain_text('다음에 찾을 안내문')

    def test_mobile_folder_selection_and_targets_fit_with_desktop_sidebar(self):
        p=self.page;self.folders();self.library()
        out=Path('/workspace/arecmik-archive-library-release');out.mkdir(exist_ok=True)
        for width in [320,390,768,1365]:
            p.set_viewport_size({'width':width,'height':950})
            if width<=900:
                p.locator('[data-archive-folder-select]').select_option('root')
                expect(p.locator('.archive-folders')).not_to_be_visible()
            else:p.locator('[data-archive-folder="root"]').click()
            expect(p.locator('.archive-list .archive-row')).to_have_count(2)
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
            for selector in ['.layout-record-types>button','[data-archive-favorites]','.archive-favorite']:
                for button in p.locator(selector).all():self.assertGreaterEqual(button.bounding_box()['height'],44)
            p.screenshot(path=str(out/f'library-{width}.png'),full_page=True)
            p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
            p.screenshot(path=str(out/f'write-{width}.png'),full_page=True)
            p.locator('#sheet [data-sx]').click()
        self.records();p.screenshot(path=str(out/'records-1365.png'),full_page=True)


if __name__=='__main__':unittest.main()

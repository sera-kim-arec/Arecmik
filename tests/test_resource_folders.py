"""Purpose-scoped browsing over the original folder hierarchy and documents."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class ResourceFolderTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown=ui.ArchiveTests.tearDown
    patch=editors.BlockEditorTests.patch
    search=ui.ArchiveTests.search

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        for ident,title,space,parent in [('root','회사','work',''),('child','채용 서식','work','root'),('personal','독서','life','')]:
            self.patch('notes',ident,{'title':title,'isFolder':True,'space':space,'fid':parent,'created':1})
        self.patch('notes','work-n',{'fid':'child'})
        self.patch('refs','work-r',{'fid':'child','fav':True,'custom':'보존할 부가 정보'})

    def browse(self):
        self.page.locator('[data-archive-filter="ref"]').click()
        self.page.locator('[data-rt="ref"]').click()
        expect(self.page.locator('.library-list')).to_be_visible()

    def child(self):
        self.browse();self.page.locator('.folder-entry[data-fold="root"]').click();self.page.locator('.folder-entry[data-fold="child"]').click()

    def stored(self,c,id):
        return self.page.evaluate('([c,id])=>__store[c].find(x=>x.id===id)',[c,id])

    def open_search_ref(self):
        self.search('업무 자료');self.page.locator('#sqr [data-sgo="ref"]').click();ui.ref_settings(self.page)

    def test_library_folder_keeps_records_out_and_back_returns_to_parent(self):
        p=self.page;self.child();expect(p.locator('.library-list>.ct')).to_contain_text('회사 / 채용 서식');expect(p.locator('.library-list>.ct')).to_contain_text('자료 1개')
        expect(p.locator('.library-list [data-odoc="work-n"]')).to_have_count(0);expect(p.locator('.library-list [data-oref="work-r"]')).to_be_visible();expect(p.locator('.library-list')).not_to_contain_text('여행 자료')
        p.go_back();expect(p.locator('.folder-entry[data-fold="child"]')).to_be_visible();expect(p.locator('.folder-entry[data-fold="child"]')).to_contain_text('자료 1개')
        p.go_back();expect(p.locator('.folder-entry[data-fold="root"]')).to_be_visible();self.assertEqual(len(p.evaluate('__store.refs')),len(ui.SEED['refs']));self.assertEqual(self.stored('notes','work-n')['fid'],'child')

    def test_new_resource_defaults_to_open_folder_and_survives_reload(self):
        p=self.page;self.child();p.locator('[data-newref]').click();expect(p.locator('#r-folder')).to_have_value('child');expect(p.locator('#r-folder option:checked')).to_have_text('회사 / 채용 서식');expect(p.locator('#r-folder option[value="personal"]')).to_have_count(0)
        p.locator('#r-t').fill('입사 안내문');p.locator('#r-b').fill('준비 서류와 안내 링크');p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');expect(p.locator('.library-list')).to_contain_text('입사 안내문')
        saved=p.evaluate("__store.refs.find(r=>r.title==='입사 안내문')");self.assertEqual((saved['space'],saved['fid']),('work','child'))
        p.reload();p.locator('.folder-entry[data-fold="root"]').click();p.locator('.folder-entry[data-fold="child"]').click();p.locator('.library-list [data-oref="'+saved['id']+'"] b').click();expect(p.locator('[data-dfold]')).to_have_value('child');expect(p.locator('[data-db]')).to_contain_text('준비 서류')

    def test_legacy_unfiled_resource_can_be_filed_without_rewriting_remote_body(self):
        p=self.page;self.browse();p.locator('.folder-scope [data-fold="none"]').click();expect(p.locator('.library-list [data-oref="legacy-r"]')).to_be_visible();expect(p.locator('.library-list [data-oref="work-r"]')).to_have_count(0)
        p.locator('.library-list [data-oref="legacy-r"] b').click();ui.ref_settings(p);expect(p.locator('#r-folder')).to_have_value('');p.locator('#r-folder').select_option('child');self.patch('refs','legacy-r',{'html':'<div>다른 기기에서 고친 대표번호</div>'});p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        saved=self.stored('refs','legacy-r');self.assertEqual(saved['fid'],'child');self.assertIn('다른 기기',saved['html']);self.assertNotIn('space',saved)
        p.locator('[data-closedoc]').click();p.locator('.folder-scope [data-fold=""]').click();p.locator('.folder-entry[data-fold="root"]').click();p.locator('.folder-entry[data-fold="child"]').click();expect(p.locator('.library-list [data-oref="legacy-r"]')).to_be_visible()

    def test_folder_path_search_opens_the_same_resource_and_filing_preserves_other_fields(self):
        p=self.page;self.search('회사 채용');expect(p.locator('#sqr [data-sgo="ref"][data-id="work-r"]')).to_be_visible();expect(p.locator('#sqr [data-sgo="doc"][data-id="work-n"]')).to_be_visible()
        p.locator('#sqr [data-sgo="ref"][data-id="work-r"]').click();ui.ref_settings(p);expect(p.locator('#r-folder')).to_have_value('child');p.locator('#r-folder').select_option('root');p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        saved=self.stored('refs','work-r');self.assertEqual(saved['fid'],'root');self.assertTrue(saved['fav']);self.assertEqual(saved['custom'],'보존할 부가 정보')

    def test_search_from_a_different_folder_opens_unfiled_resource_and_keeps_navigation(self):
        p=self.page;self.child();self.search('기존 자료');p.locator('#sqr [data-sgo="ref"]').click();expect(p.locator('[data-dt]')).to_have_value('기존 자료');expect(p.locator('[data-dfold]')).to_have_value('');p.locator('[data-closedoc]').click();p.locator('#sqi').press('Escape');expect(p.locator('.library-list [data-oref="work-r"]')).to_be_visible()

    def test_body_edit_preserves_a_remote_folder_move_and_conflicting_move_is_stopped(self):
        p=self.page;self.open_search_ref();p.locator('#r-b').fill('작성 중인 내 본문');self.patch('refs','work-r',{'fid':'root'});p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(self.stored('refs','work-r')['fid'],'root');self.assertIn('내 본문',self.stored('refs','work-r')['html'])
        self.open_search_ref();p.locator('#r-folder').select_option('child');self.patch('refs','work-r',{'fid':''});p.locator('[data-rsave]').click();expect(p.locator('.save-conflict')).to_be_visible();self.assertEqual(self.stored('refs','work-r')['fid'],'')

    def test_old_draft_without_folder_field_does_not_remove_an_existing_folder(self):
        p=self.page;self.open_search_ref();p.locator('#r-b').fill('폴더 기능 이전에 쓴 임시 내용');p.locator('#sheet [data-sx]').click();p.evaluate("()=>{const key='arecmik:form:ui-test:ref:work-r',draft=JSON.parse(localStorage.getItem(key));delete draft.fields['r-folder'];delete draft.guard.initialFields['r-folder'];localStorage.setItem(key,JSON.stringify(draft))}");self.open_search_ref();expect(p.locator('#r-folder')).to_have_value('child');p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(self.stored('refs','work-r')['fid'],'child')

    def test_switching_space_resets_folder_and_restores_saved_draft_options(self):
        p=self.page;self.open_search_ref();p.locator('#r-space').select_option('life');expect(p.locator('#r-folder')).to_have_value('');expect(p.locator('#r-folder option[value="child"]')).to_have_count(0);p.locator('#r-folder').select_option('personal');p.locator('#r-b').fill('옮기는 중 작성한 내용');p.locator('#sheet [data-sx]').click()
        self.open_search_ref();expect(p.locator('#r-space')).to_have_value('life');expect(p.locator('#r-folder')).to_have_value('personal');expect(p.locator('#r-b')).to_contain_text('옮기는 중');p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        saved=self.stored('refs','work-r');self.assertEqual((saved['space'],saved['fid']),('life','personal'));self.assertTrue(saved['fav']);self.assertEqual(self.stored('notes','work-n')['fid'],'child')

    def test_failure_keeps_draft_and_retry_does_not_duplicate_new_resource(self):
        p=self.page;self.child();p.locator('[data-newref]').click();p.locator('#r-t').fill('다시 저장할 양식');p.locator('#r-b').fill('보존될 본문');p.evaluate('window.__failWrites=true');p.locator('[data-rsave]').click();expect(p.locator('.toast')).to_contain_text('저장하지 못했어요');expect(p.locator('#r-t')).to_have_value('다시 저장할 양식');expect(p.locator('#r-folder')).to_have_value('child')
        p.locator('#sheet [data-sx]').click();p.locator('[data-newref]').click();expect(p.locator('#r-b')).to_contain_text('보존될 본문');p.evaluate('window.__failWrites=false;window.__writeDelayMs=150');p.locator('[data-rsave]').dblclick();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(p.evaluate("__store.refs.filter(r=>r.title==='다시 저장할 양식'&&r.fid==='child').length"),1)

    def test_folder_deleted_during_new_resource_form_requires_explicit_destination(self):
        p=self.page;self.child();p.locator('[data-newref]').click();p.locator('#r-t').fill('아직 저장하지 않은 자료');p.evaluate("async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.deleteDoc(f.doc(f.collection({},'notes'),'child'))}");p.locator('[data-rsave]').click();expect(p.locator('#r-folder-error')).to_contain_text('폴더를 다시 선택');expect(p.locator('#r-t')).to_have_value('아직 저장하지 않은 자료');self.assertFalse(p.evaluate("__store.refs.some(r=>r.title==='아직 저장하지 않은 자료')"))
        p.locator('#r-folder').select_option('root');p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(p.evaluate("__store.refs.find(r=>r.title==='아직 저장하지 않은 자료').fid"),'root')

    def test_delete_folder_and_undo_preserve_resources_and_are_atomic_on_failure(self):
        p=self.page;self.child();p.locator('[data-folder-manage]').click();expect(p.locator('#folder-manager')).to_contain_text('자료 1개');before=p.evaluate('JSON.stringify(__store)');p.evaluate("window.__failWritesFor='refs'");p.locator('#folder-manager [data-folder-delete="child"]').click();p.locator('#sheet [data-sx="1"]').click();expect(p.locator('.toast')).to_contain_text('삭제하지 못했어요');self.assertEqual(p.evaluate('JSON.stringify(__store)'),before)
        p.evaluate('window.__failWritesFor=null');p.locator('[data-folder-manage]').click();p.locator('#folder-manager [data-folder-delete="child"]').click();p.locator('#sheet [data-sx="1"]').click();expect(p.locator('#folder-manager [data-folder-delete="child"]')).to_have_count(0);self.assertEqual(self.stored('refs','work-r')['fid'],'root');self.assertEqual(self.stored('notes','work-n')['fid'],'root');p.locator('.toast button').click();expect(p.locator('#folder-manager [data-folder-delete="child"]')).to_be_visible();self.assertEqual(self.stored('refs','work-r')['fid'],'child');self.assertEqual(self.stored('notes','work-n')['fid'],'child')

    def test_mobile_folder_navigation_and_controls_fit_and_keyboard_opens_resource(self):
        p=self.page;self.child()
        for width in [320,390,768,1365]:
            p.set_viewport_size({'width':width,'height':900});self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width);row=p.locator('.library-list [data-oref="work-r"]');expect(row).to_be_visible()
            row.focus();row.press('Enter');expect(p.locator('[data-dfold]')).to_have_value('child');self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width);p.locator('[data-closedoc]').click()
        p.set_viewport_size({'width':390,'height':900})
        for selector in ['.library-row .fv','.library-row .library-copy','.library-create [data-newref]','.folder-scope [data-fold="none"]']:
            box=p.locator(selector).bounding_box();self.assertGreaterEqual(box['height'],44)


if __name__=='__main__':unittest.main()

"""Folders have a real parent, visible children and safe failure/retry behavior."""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class NestedFolderTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    patch=editors.BlockEditorTests.patch
    search=ui.ArchiveTests.search

    def browse(self):
        p=self.page
        if p.locator('[data-archive-filter="doc"]').count():p.locator('[data-archive-filter="doc"]').click();p.locator('[data-rt="doc"]').click()
        expect(p.locator('.folder-toolbar')).to_be_visible()

    def parent(self):
        self.patch('notes','folder-work',{'isFolder':True,'title':'업무 자료','space':'work','fid':'','created':1});self.browse();self.page.locator('.folder-entry[data-fold="folder-work"]').click()

    def create(self,title):
        p=self.page;p.locator('#folder-title').fill(title);p.locator('[data-folder-create]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        return p.evaluate("title=>__store.notes.find(n=>n.isFolder&&n.title===title)",title)

    def test_root_folder_and_enter_submission_work_without_an_existing_parent(self):
        p=self.page;self.browse();p.locator('.folder-toolbar [data-newf]').click();expect(p.locator('#folder-parent')).to_have_value('');p.locator('#folder-title').fill('회의 자료');p.locator('#folder-title').press('Enter');expect(p.locator('#scrim')).not_to_have_class('scrim on')
        folder=p.evaluate("__store.notes.find(n=>n.isFolder&&n.title==='회의 자료')");self.assertEqual((folder['fid'],folder['space']),('','work'));expect(p.locator('.dsplit>section>.ct')).to_contain_text('회의 자료')

    def test_child_and_grandchild_have_visible_paths_and_new_articles_keep_the_parent(self):
        p=self.page;self.parent();p.locator('.folder-toolbar [data-newf]').click();expect(p.locator('#folder-parent')).to_have_value('folder-work');child=self.create('계약·서식');self.assertEqual(child['fid'],'folder-work');expect(p.locator('.dsplit>section>.ct')).to_contain_text('업무 자료 / 계약·서식')
        p.locator('.folder-toolbar [data-newf]').click();expect(p.locator('#folder-parent')).to_have_value(child['id']);grand=self.create('2026년');self.assertEqual(grand['fid'],child['id'])
        p.locator('.dsplit>section [data-newdoc]').click();expect(p.locator('[data-dfold]')).to_have_value(grand['id']);expect(p.locator('[data-dfold] option:checked')).to_have_text('업무 자료 / 계약·서식 / 2026년');p.locator('[data-dt]').fill('고용 계약서 안내');p.locator('[data-db]').fill('정리한 내용을 다시 찾기');p.wait_for_function("__store.notes.some(n=>n.title==='고용 계약서 안내'&&n.html.includes('다시 찾기'))")
        p.reload();self.browse();p.locator('.folder-entry[data-fold="folder-work"]').click();p.locator('.folder-entry[data-fold="'+child['id']+'"]').click();p.locator('.folder-entry[data-fold="'+grand['id']+'"]').click();expect(p.locator('.dsplit>section .dr')).to_contain_text('고용 계약서 안내')

    def test_failure_keeps_title_and_location_and_retry_creates_only_one_child(self):
        p=self.page;self.parent();p.locator('.folder-toolbar [data-newf]').click();p.locator('#folder-title').fill('보관할 문서');p.evaluate('window.__failWrites=true');p.locator('[data-folder-create]').click();expect(p.locator('#folder-create-error')).to_contain_text('입력한 이름과 위치는 유지');expect(p.locator('#folder-title')).to_have_value('보관할 문서');expect(p.locator('#folder-parent')).to_have_value('folder-work');self.assertEqual(p.evaluate("__store.notes.filter(n=>n.title==='보관할 문서').length"),0)
        p.evaluate('window.__failWrites=false');p.locator('[data-folder-create]').dblclick();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.assertEqual(p.evaluate("__store.notes.filter(n=>n.title==='보관할 문서'&&n.fid==='folder-work').length"),1)

    def test_a_deleted_parent_is_not_silently_replaced_by_a_root_folder(self):
        p=self.page;self.parent();p.locator('.folder-toolbar [data-newf]').click();p.locator('#folder-title').fill('새 하위 폴더');p.evaluate("async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.deleteDoc(f.doc(f.collection({},'notes'),'folder-work'))}")
        p.locator('[data-folder-create]').click();expect(p.locator('#folder-create-error')).to_contain_text('상위 폴더가 없어졌어요');self.assertEqual(p.evaluate("__store.notes.filter(n=>n.title==='새 하위 폴더').length"),0);expect(p.locator('#folder-title')).to_have_value('새 하위 폴더');p.locator('#folder-parent').select_option('');folder=self.create('새 하위 폴더');self.assertEqual(folder['fid'],'')

    def test_manager_can_create_a_child_and_mobile_lists_preserve_hierarchy(self):
        p=self.page;self.patch('notes','folder-life',{'isFolder':True,'title':'개인 자료','space':'life','fid':''});self.parent();p.locator('[data-folder-manage]').click();p.locator('#folder-manager [data-newf][data-parent="folder-work"]').click();p.locator('[data-folder-back]').click();expect(p.locator('#folder-manager')).to_be_visible();p.locator('#folder-manager [data-newf][data-parent="folder-work"]').click();expect(p.locator('#folder-parent option[value="folder-life"]')).to_have_count(0);child=self.create('업무 양식')
        for width in [320,390,768,1365]:
            p.set_viewport_size({'width':width,'height':900});p.locator('.folder-toolbar [data-fold]').click();entry=p.locator('.folder-entry[data-fold="'+child['id']+'"]');expect(entry).to_be_visible();self.assertGreaterEqual(entry.bounding_box()['height'],44);self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width);entry.click()
        p.locator('.folder-toolbar [data-newf]').click();p.locator('[data-folder-create]').click();expect(p.locator('#folder-title')).to_have_attribute('aria-invalid','true');expect(p.locator('#folder-title-error')).to_have_text('폴더 이름을 적어 주세요.')

if __name__=='__main__':unittest.main()

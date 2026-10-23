"""Purpose remains consistent through folders, article trees and creation.

The underlying notes/refs collections deliberately contain both purposes. These
flows must follow the user's choice of records or materials, not storage format.
"""
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors
import test_save_safety as saving


class ArchivePurposeScopeTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown
    patch = editors.BlockEditorTests.patch
    search = ui.ArchiveTests.search
    stored = saving.SaveSafetyTests.stored
    wait_saved = saving.SaveSafetyTests.wait_saved

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        for ident, title, parent in [('scope-root', '업무 보관', ''),
                                     ('scope-child', '면접', 'scope-root')]:
            self.patch('notes', ident, {'isFolder': True, 'title': title,
                                       'space': 'work', 'fid': parent, 'created': 1})
        self.patch('notes', 'work-n', {'fid': 'scope-child'})
        self.patch('refs', 'work-r', {'fid': 'scope-child'})
        self.patch('notes', 'guide-note', {'title': '반복해서 쓸 면접 안내문',
                   'html': '<div>담당자용 진행 순서</div>', 'space': 'work',
                   'fid': 'scope-child', 'archivePurpose': 'resource', 'created': ui.STAMP})
        self.patch('refs', 'experience-ref', {'title': '이번 면접을 마친 소감',
                   'html': '<div>질문 순서를 바꾼 이유</div>', 'space': 'work',
                   'fid': 'scope-child', 'archivePurpose': 'record', 'created': ui.STAMP})

    def choose_mode(self, resource):
        self.page.locator('[data-archive-filter="' + ('ref' if resource else '') + '"]').click()

    def browse_child(self, resource):
        self.choose_mode(resource)
        self.page.locator('.archive-legacy-folders').click()
        self.page.locator('.folder-entry[data-fold="scope-root"]').click()
        self.page.locator('.folder-entry[data-fold="scope-child"]').click()
        expect(self.page.locator('.library-list')).to_be_visible()

    def assert_purpose_rows(self, scope, resource):
        expected = [('data-odoc', 'guide-note'), ('data-oref', 'work-r')] if resource else [
                    ('data-odoc', 'work-n'), ('data-oref', 'experience-ref')]
        hidden = [('data-odoc', 'work-n'), ('data-oref', 'experience-ref')] if resource else [
                  ('data-odoc', 'guide-note'), ('data-oref', 'work-r')]
        for attribute, ident in expected:
            expect(scope.locator('[' + attribute + '="' + ident + '"]')).to_be_visible()
        for attribute, ident in hidden:
            expect(scope.locator('[' + attribute + '="' + ident + '"]')).to_have_count(0)

    def test_modes_and_nested_folders_follow_purpose_instead_of_collection(self):
        p = self.page
        expect(p.locator('.rh h1')).to_have_text('업무 기록')
        expect(p.locator('.archive-day').first).to_be_visible()
        self.browse_child(False)
        self.assert_purpose_rows(p.locator('.library-list'), False)
        expect(p.locator('.library-list>.ct')).to_contain_text('기록 2개')
        p.locator('[data-rt="archive"]').click()
        self.choose_mode(True)
        expect(p.locator('.rh h1')).to_have_text('자료실')
        expect(p.locator('.archive-day')).to_have_count(0)
        self.browse_child(True)
        self.assert_purpose_rows(p.locator('.library-list'), True)
        expect(p.locator('.library-list>.ct')).to_contain_text('자료 2개')
        self.assertEqual(self.stored('notes', 'guide-note')['archivePurpose'], 'resource')
        self.assertEqual(self.stored('refs', 'experience-ref')['archivePurpose'], 'record')

    def test_search_detail_tree_and_folder_link_keep_actual_document_purpose(self):
        p = self.page
        self.search('반복해서 쓸 면접 안내문')
        p.locator('#sqr [data-sgo="doc"]').click()
        expect(p.locator('[data-dpurpose]')).to_have_value('resource')
        tree = p.locator('.tree')
        expect(tree.locator('[data-tree-ref="experience-ref"]')).to_have_count(0)
        expect(tree.locator('[data-odoc="work-n"]')).to_have_count(0)
        tree.locator('[data-ftog="scope-child"]').click()
        self.assert_purpose_rows(p.locator('.library-list'), True)
        p.locator('.library-list [data-oref="work-r"] b').click()
        expect(p.locator('.tree [data-odoc="guide-note"]')).to_be_visible()
        expect(p.locator('.tree [data-tree-ref="experience-ref"]')).to_have_count(0)

    def test_new_documents_from_each_folder_keep_purpose_and_parent(self):
        p = self.page
        for resource in [False, True]:
            self.browse_child(resource)
            p.locator('.library-create [data-newdoc]').click()
            expect(p.locator('[data-dpurpose]')).to_have_value('resource' if resource else 'record')
            expect(p.locator('[data-dfold]')).to_have_value('scope-child')
            ident = p.locator('[data-dt]').get_attribute('data-dt')
            p.locator('[data-dt]').fill('새 면접 안내문' if resource else '새 면접 회고')
            p.locator('[data-db]').fill('작성한 본문을 보존해요')
            self.wait_saved()
            row = self.stored('notes', ident)
            self.assertEqual((row['archivePurpose'], row['fid']),
                             ('resource' if resource else 'record', 'scope-child'))
            p.locator('[data-closedoc]').click()
            expect(p.locator('.library-list [data-odoc="' + ident + '"]')).to_be_visible()
            p.locator('[data-rt="archive"]').click()

    def test_detail_tree_plus_creates_resource_in_the_clicked_folder(self):
        p = self.page
        self.choose_mode(True)
        p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
        p.locator('.tree [data-fnewin="scope-child"]').click()
        expect(p.locator('[data-dpurpose]')).to_have_value('resource')
        expect(p.locator('[data-dfold]')).to_have_value('scope-child')
        ident = p.locator('[data-dt]').get_attribute('data-dt')
        self.assertNotEqual(ident, 'work-r')
        p.locator('[data-dt]').fill('같은 폴더의 새 참고 문서')
        self.wait_saved()
        self.assertEqual(self.stored('notes', ident)['fid'], 'scope-child')
        self.assertEqual(self.stored('notes', ident)['archivePurpose'], 'resource')

    def test_reclassification_keeps_original_and_removes_it_from_previous_purpose(self):
        p = self.page
        self.choose_mode(True)
        p.locator('[data-archive-open="doc"][data-id="guide-note"]').click()
        before = self.stored('notes', 'guide-note')
        count = p.evaluate('__store.notes.length')
        p.locator('[data-dpurpose]').select_option('record')
        expect(p.locator('.tree')).to_have_attribute('data-purpose', 'record')
        expect(p.locator('[data-document-location]')).to_contain_text('업무 기록')
        self.wait_saved()
        p.locator('[data-closedoc]').click()
        expect(p.locator('.archive-list [data-archive-open="doc"][data-id="guide-note"]')).to_have_count(0)
        self.choose_mode(False)
        p.locator('[data-archive-open="doc"][data-id="guide-note"]').click()
        expect(p.locator('[data-db]')).to_contain_text('담당자용 진행 순서')
        after = self.stored('notes', 'guide-note')
        self.assertEqual((after['id'], after['fid'], after['html']),
                         (before['id'], before['fid'], before['html']))
        self.assertEqual(p.evaluate('__store.notes.length'), count)

    def test_mobile_folder_browsing_and_keyboard_open_keep_scope_without_overflow(self):
        p = self.page
        for width in [320, 390]:
            p.set_viewport_size({'width': width, 'height': 900})
            self.browse_child(True)
            self.assert_purpose_rows(p.locator('.library-list'), True)
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'), width)
            row = p.locator('.library-list [data-odoc="guide-note"]')
            row.focus()
            row.press('Enter')
            expect(p.locator('[data-db]')).to_contain_text('담당자용 진행 순서')
            expect(p.locator('[data-dpurpose]')).to_have_value('resource')
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'), width)
            p.locator('[data-closedoc]').click()
            self.assert_purpose_rows(p.locator('.library-list'), True)
            p.locator('[data-rt="archive"]').click()

    def test_library_row_favorite_and_copy_target_original_without_opening_it(self):
        p = self.page
        self.patch('refs', 'guide-note', {'title': '같은 ID의 별도 자료',
                   'html': '<div>다른 자료의 본문</div>', 'space': 'work',
                   'archivePurpose': 'resource', 'fid': 'scope-child'})
        p.evaluate("""()=>{window.__copied=[];Object.defineProperty(navigator,'clipboard',{
            configurable:true,value:{writeText:async text=>{
                if(window.__copyFail)throw new Error('Clipboard unavailable');
                window.__copied.push(text);
            }}})}""")
        self.browse_child(True)
        for attribute, collection, ident, body in [
                ('data-odoc', 'notes', 'guide-note', '담당자용 진행 순서'),
                ('data-oref', 'refs', 'work-r', '팀 연락처')]:
            row = p.locator('.library-list [' + attribute + '="' + ident + '"]')
            row.locator('[data-archive-favorite]').click()
            p.wait_for_function('([c,id])=>__store[c].find(x=>x.id===id).fav===true',
                                arg=[collection, ident])
            expect(p.locator('.library-list')).to_be_visible()
            expect(p.locator('article.doc')).to_have_count(0)
            row.locator('[data-copy]').click()
            p.wait_for_function('(body)=>window.__copied.includes(body)', arg=body)
            expect(p.locator('.library-list')).to_be_visible()
            expect(p.locator('article.doc')).to_have_count(0)
        self.assertFalse(self.stored('refs', 'guide-note').get('fav', False))
        self.assertEqual(p.evaluate('window.__copied'), ['담당자용 진행 순서', '팀 연락처'])
        p.evaluate('window.__copyFail=true')
        p.locator('.library-list [data-odoc="guide-note"] [data-copy]').click()
        expect(p.locator('.toast')).to_contain_text('복사하지 못했어요')
        expect(p.locator('.library-list')).to_be_visible()
        expect(p.locator('article.doc')).to_have_count(0)

    def test_home_materials_use_purpose_and_search_creation_keeps_material_context(self):
        p = self.page
        p.locator('nav [data-tab="home"]').click()
        material = p.locator('[data-layout-fold="refs"]')
        expect(material.locator('summary')).to_contain_text('3개')
        expect(material.locator('summary')).not_to_contain_text('이번 면접을 마친 소감')
        ui.reveal(p, '[data-layout-fold="refs"] #rfq')
        expect(material.locator('[data-odoc="guide-note"]')).to_be_visible()
        expect(material.locator('[data-oref="work-r"]')).to_be_visible()
        expect(material.locator('[data-odoc="work-n"]')).to_have_count(0)
        expect(material.locator('[data-oref="experience-ref"]')).to_have_count(0)
        material.locator('[data-odoc="guide-note"] b').click()
        expect(p.locator('[data-dpurpose]')).to_have_value('resource')
        expect(p.locator('[data-db]')).to_contain_text('담당자용 진행 순서')
        p.go_back()
        expect(p.locator('.hhead')).to_be_visible()
        ui.reveal(p, '[data-layout-fold="refs"] #rfq')
        material.locator('#rfq').fill('진행 순서')
        expect(material.locator('[data-odoc="guide-note"]')).to_be_visible()
        expect(material.locator('[data-oref="work-r"]')).to_have_count(0)
        material.locator('#rfq').fill('이번 면접을 마친 소감')
        expect(material.locator('.emp')).to_contain_text('찾는 자료가 없어요')
        material.locator('[data-newdoc][data-title]').click()
        expect(p.locator('[data-dpurpose]')).to_have_value('resource')
        expect(p.locator('[data-dt]')).to_have_value('이번 면접을 마친 소감')
        ident = p.locator('[data-dt]').get_attribute('data-dt')
        self.assertEqual(self.stored('notes', ident)['archivePurpose'], 'resource')
        self.assertEqual(self.stored('refs', 'experience-ref')['archivePurpose'], 'record')


if __name__ == '__main__':
    unittest.main()

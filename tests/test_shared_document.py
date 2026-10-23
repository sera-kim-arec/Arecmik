"""Records and materials share the actual document form and normal entry paths."""
import unittest
from pathlib import Path
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors
import test_save_safety as saving
from test_memo_images import PNG


class SharedDocumentTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    patch=editors.BlockEditorTests.patch
    search=ui.ArchiveTests.search
    wait_saved=saving.SaveSafetyTests.wait_saved
    stored=saving.SaveSafetyTests.stored

    def material(self,ident='work-r'):
        self.page.locator('[data-archive-filter="ref"]').click()
        self.page.locator('[data-archive-open="ref"][data-id="'+ident+'"]').click()
        expect(self.page.locator('article.doc[data-doc-collection="refs"]')).to_be_visible()

    def more(self):self.page.locator('article.doc [data-more]').click()

    def test_record_and_material_have_same_fields_layout_and_writing_controls(self):
        p=self.page;out=Path('/workspace/arecmik-shared-document-release');out.mkdir(exist_ok=True)
        for width in [320,390,1365]:
            p.set_viewport_size({'width':width,'height':950});p.locator('[data-archive-open="doc"][data-id="work-n"]').click()
            labels=p.locator('article.doc :is(input,select,[contenteditable])').evaluate_all('els=>els.map(e=>[e.tagName,e.getAttribute("aria-label"),e.getAttribute("data-ph")])')
            body=p.locator('[data-db]');style=body.evaluate('e=>[getComputedStyle(e).fontSize,getComputedStyle(e).lineHeight,getComputedStyle(e).minHeight]')
            p.screenshot(path=str(out/f'record-{width}.png'),full_page=True);p.locator('[data-closedoc]').click();self.material()
            self.assertEqual(p.locator('article.doc :is(input,select,[contenteditable])').evaluate_all('els=>els.map(e=>[e.tagName,e.getAttribute("aria-label"),e.getAttribute("data-ph")])'),labels)
            self.assertEqual(p.locator('[data-db]').evaluate('e=>[getComputedStyle(e).fontSize,getComputedStyle(e).lineHeight,getComputedStyle(e).minHeight]'),style)
            expect(p.locator('.resource-settings')).to_have_count(0)
            expect(p.locator('[data-dpj]')).to_be_visible();self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
            p.screenshot(path=str(out/f'material-{width}.png'),full_page=True)
            self.more();expect(p.locator('.pop [data-dimg]')).to_be_visible();expect(p.locator('.pop [data-ddel]')).to_be_visible()
            p.locator('.pop [data-archive-favorite]').click();self.wait_saved()
            p.locator('[data-closedoc]').click();p.locator('[data-archive-filter=""]').click()

    def test_existing_material_supports_same_project_folder_and_life_type_fields(self):
        p=self.page;self.patch('notes','folder',{'isFolder':True,'title':'참고','space':'life'})
        p.locator('[data-sp="life"]').click();self.material('life-r')
        p.locator('[data-dpurpose]').select_option('record');p.locator('[data-dtype]').select_option('movie')
        p.locator('[data-dfold]').select_option('folder');p.locator('[data-dpj]').select_option('life-p')
        p.locator('[data-db]').fill('감상과 연결된 자료 내용');self.wait_saved();r=self.stored('refs','life-r')
        self.assertEqual((r['archivePurpose'],r['recordType'],r['fid'],r['pid']),('record','movie','folder','life-p'))
        self.assertIn('감상과 연결된',r['html']);self.assertEqual(p.evaluate('__store.refs.length'),len(ui.SEED['refs']))
        p.locator('[data-closedoc]').click();p.locator('[data-archive-filter=""]').click()
        ui.reveal(p,'[data-archive-record-type]');p.locator('[data-archive-record-type]').select_option('movie')
        expect(p.locator('.archive-list')).to_contain_text('여행 자료');expect(p.locator('.archive-kind')).to_have_text('영화 기록')

    def test_search_home_and_folder_tree_open_the_common_form_and_return_to_origin(self):
        p=self.page;self.search('업무 자료');p.locator('#sqr [data-sgo="ref"]').click()
        expect(p.locator('article.doc [data-db]')).to_contain_text('팀 연락처');expect(p.locator('#scrim')).not_to_have_class('scrim on')
        p.go_back();expect(p.locator('#sqi')).to_have_value('업무 자료');p.locator('#sqi').press('Escape')
        p.locator('nav [data-tab="home"]').click();ui.reveal(p,'[data-oref="work-r"]')
        p.locator('[data-oref="work-r"] b').click();expect(p.locator('article.doc[data-doc-collection="refs"]')).to_be_visible()
        p.go_back();expect(p.locator('.hhead')).to_be_visible()
        p.locator('nav [data-tab="rec"]').click();p.locator('[data-archive-open="doc"][data-id="work-n"]').click()
        p.locator('[data-tree-ref="work-r"]').click();expect(p.locator('article.doc[data-doc-collection="refs"]')).to_be_visible()
        p.go_back();expect(p.locator('article.doc[data-doc-collection="notes"]')).to_be_visible()

    def test_new_material_from_home_uses_the_same_form_and_material_purpose(self):
        p=self.page;p.locator('nav [data-tab="home"]').click()
        ui.reveal(p,'[data-layout-fold="refs"] [data-newdoc]')
        p.locator('[data-layout-fold="refs"] [data-newdoc]').click()
        expect(p.locator('article.doc [data-db]')).to_be_visible()
        expect(p.locator('[data-dpurpose]')).to_have_value('resource')
        expect(p.locator('#scrim')).not_to_have_class('scrim on')

    def test_linked_material_and_back_preserve_record_sheet_draft(self):
        p=self.page;self.patch('moms','work-m',{'connections':[{'c':'refs','id':'work-r','sourceId':'work-m'}]})
        p.locator('[data-archive-open="mom"][data-id="work-m"]').click();p.locator('#record-body').fill('작성 중이던 회고')
        p.locator('#sheet .connection-open').filter(has_text='업무 자료').click()
        expect(p.locator('article.doc[data-doc-collection="refs"]')).to_be_visible()
        self.more();p.go_back();expect(p.locator('.pop')).to_have_count(0)
        expect(p.locator('article.doc[data-doc-collection="refs"]')).to_be_visible()
        ui.ref_settings(p);p.go_back();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        expect(p.locator('article.doc[data-doc-collection="refs"]')).to_be_visible()
        p.go_back();expect(p.locator('#record-body')).to_contain_text('작성 중이던 회고')
        expect(p.locator('#scrim')).to_have_class('scrim on')

    def test_shared_photo_menu_saves_into_existing_material(self):
        p=self.page;self.material();self.more()
        with p.expect_file_chooser() as picker:p.locator('.pop [data-dimg]').click()
        picker.value.set_files({'name':'photo.png','mimeType':'image/png','buffer':PNG})
        expect(p.locator('[data-db] [data-img]')).to_have_count(1);self.wait_saved()
        self.assertIn('data-img',self.stored('refs','work-r')['html']);self.assertEqual(p.evaluate('__store.notes.length'),len(ui.SEED['notes']))

    def test_shared_trash_menu_keeps_unsaved_or_failed_material_and_undo_keeps_note(self):
        p=self.page;self.patch('refs','work-n',{'title':'별도 자료 원본','html':'<div>자료 본문</div>','space':'work'})
        self.material('work-n');p.evaluate("window.__failWritesFor='refs'");self.more();p.locator('.pop [data-ddel]').click()
        expect(p.locator('.toast')).to_contain_text('삭제하지 못했어요');expect(p.locator('article.doc[data-doc-collection="refs"]')).to_be_visible()
        p.evaluate('window.__failWritesFor=null');p.locator('[data-db]').fill('지우기 전 작성 중인 자료')
        self.more();p.locator('.pop [data-ddel]').click();expect(p.locator('.toast')).to_contain_text('먼저 저장')
        expect(p.locator('article.doc[data-doc-collection="refs"]')).to_be_visible();self.wait_saved()
        self.more();p.locator('.pop [data-ddel]').click();p.wait_for_function("!__store.refs.some(x=>x.id==='work-n')")
        self.assertEqual(self.stored('notes','work-n')['html'],'<div>중요한 결정</div>')
        p.locator('.toast button').click();p.wait_for_function("__store.refs.some(x=>x.id==='work-n')")
        self.assertIn('지우기 전 작성',self.stored('refs','work-n')['html'])

    def test_project_delete_and_undo_include_original_material_assignment(self):
        p=self.page;self.patch('refs','work-r',{'pid':'work-p'})
        p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="work-p"]').click()
        p.locator('[data-more="proj"]').click();p.locator('[data-pdel]').click();p.locator('#sheet [data-sx="1"]').click()
        p.wait_for_function("!__store.projects.some(x=>x.id==='work-p')");self.assertEqual(self.stored('refs','work-r')['pid'],'')
        self.assertEqual(self.stored('refs','work-r')['html'],'<div>팀 연락처</div>')
        p.locator('.toast button').click();p.wait_for_function("__store.projects.some(x=>x.id==='work-p')")
        self.assertEqual(self.stored('refs','work-r')['pid'],'work-p')


if __name__=='__main__':unittest.main()

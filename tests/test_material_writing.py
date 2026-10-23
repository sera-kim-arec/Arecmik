"""Materials use the article editor without moving existing refs documents."""
import unittest
from pathlib import Path
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors
import test_save_safety as saving


class MaterialWritingTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    patch=editors.BlockEditorTests.patch
    stored=saving.SaveSafetyTests.stored
    drafts=saving.SaveSafetyTests.drafts
    wait_saved=saving.SaveSafetyTests.wait_saved
    wait_conflict=saving.SaveSafetyTests.wait_conflict

    def library(self):
        p=self.page
        if p.locator('[data-closedoc]').count():p.locator('nav [data-tab="rec"]').click()
        p.locator('[data-archive-filter="ref"]').click()

    def material(self, ident='work-r'):
        self.library();self.page.locator('[data-archive-open="ref"][data-id="'+ident+'"]').click()
        expect(self.page.locator('[data-rdoc-body].nb-editor')).to_be_visible()
        return self.page.locator('[data-rdoc-body]')

    def test_default_material_writing_uses_article_blocks_folder_and_autosave(self):
        p=self.page;self.patch('notes','folder',{'isFolder':True,'title':'가이드','space':'work'})
        self.library();p.locator('[data-archive-folder="folder"]').click()
        p.locator('.layout-write-group>[data-newdoc]').click()
        expect(p.locator('[data-dpurpose]')).to_have_value('resource');expect(p.locator('[data-dfold]')).to_have_value('folder')
        p.locator('.dt').fill('업무에 쓰는 긴 가이드');ed=p.locator('[data-db]');ed.fill('')
        p.keyboard.type('> ');p.keyboard.insert_text('필요할 때 펼칠 내용');p.keyboard.press('Enter');p.keyboard.insert_text('긴 설명도 글처럼 작성해요')
        expect(ed.locator('.nb-toggle-body')).to_contain_text('긴 설명도 글처럼')
        self.wait_saved();saved=p.evaluate("__store.notes.find(x=>x.title==='업무에 쓰는 긴 가이드')")
        self.assertEqual((saved['archivePurpose'],saved['fid']),('resource','folder'));self.assertIn('nb-toggle',saved['html'])
        p.locator('[data-closedoc]').click();expect(p.locator('.archive-library')).to_be_visible()
        expect(p.locator('.archive-list')).to_contain_text('업무에 쓰는 긴 가이드')
        self.assertFalse(p.evaluate("__store.refs.some(x=>x.title==='업무에 쓰는 긴 가이드')"))

    def test_existing_ref_autosaves_original_without_copying_relationships(self):
        p=self.page;self.patch('refs','work-r',{'fav':True,'custom':'원본','connections':[{'c':'moms','id':'work-m','sourceId':'work-r'}]})
        self.patch('moms','work-m',{'connections':[{'c':'refs','id':'work-r','sourceId':'work-m'}]})
        ed=self.material();p.locator('[data-rdoc-title]').fill('길게 고친 자료');ed.fill('자료도 문단을 나눠 길게 작성할 수 있어요')
        self.wait_saved();saved=self.stored('refs','work-r')
        self.assertIn('길게 작성',saved['html']);self.assertEqual(saved['title'],'길게 고친 자료')
        self.assertTrue(saved['fav']);self.assertEqual(saved['custom'],'원본');self.assertEqual(saved['connections'],[{'c':'moms','id':'work-m','sourceId':'work-r'}])
        self.assertEqual(p.evaluate('__store.notes.length'),len(ui.SEED['notes']))
        self.assertEqual(p.evaluate('__store.refs.length'),len(ui.SEED['refs']))
        expect(p.locator('article.doc .connection-open')).to_contain_text('업무 회의 회고')
        p.locator('[data-closedoc]').click();expect(p.locator('.archive-list')).to_contain_text('길게 고친 자료')

    def test_existing_ref_shares_toggle_editing_and_keyboard_undo(self):
        p=self.page;ed=self.material();ed.fill('');p.keyboard.type('> ');p.keyboard.insert_text('토글 제목');p.keyboard.press('Enter');p.keyboard.insert_text('보존할 자료 설명')
        ed.locator('.nb-toggle-title').click();p.keyboard.press('Home');p.keyboard.press('Backspace')
        expect(ed.locator('.nb-toggle')).to_have_count(0);expect(ed).to_contain_text('보존할 자료 설명')
        p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-body')).to_contain_text('보존할 자료 설명')
        self.wait_saved();self.assertIn('nb-toggle',self.stored('refs','work-r')['html'])

    def test_related_record_and_back_restore_material_page_and_unsaved_text(self):
        p=self.page;self.patch('refs','work-r',{'connections':[{'c':'moms','id':'work-m','sourceId':'work-r'}]})
        ed=self.material();ed.fill('자료에서 작성하던 본문')
        p.locator('article.doc .connection-open').filter(has_text='업무 회의 회고').click()
        expect(p.locator('#record-body')).to_contain_text('업무 회의 회고')
        p.go_back();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        expect(p.locator('[data-rdoc-body]')).to_contain_text('자료에서 작성하던 본문')
        source=p.locator('article.doc .connections-panel').get_attribute('data-connection-source')
        self.assertEqual(p.evaluate('s=>JSON.parse(decodeURIComponent(s)).c',source),'refs')

    def test_remote_body_conflict_keeps_both_versions_and_original_collection(self):
        p=self.page;ed=self.material();ed.fill('PC에서 쓴 자료')
        self.patch('refs','work-r',{'html':'<div>휴대폰에서 쓴 자료</div>'})
        self.wait_conflict();expect(ed).to_contain_text('PC에서 쓴 자료')
        self.assertIn('휴대폰에서',self.stored('refs','work-r')['html'])
        p.locator('#save-status [data-local-recovery]').click()
        expect(p.locator('.recovery-item')).to_contain_text('PC에서');expect(p.locator('.recovery-item')).to_contain_text('휴대폰에서')
        self.assertEqual(self.drafts()['refs:work-r']['c'],'refs')

    def test_failed_autosave_recovers_on_reopen_and_retries_once(self):
        p=self.page;ed=self.material();p.evaluate("window.__failWritesFor='refs'");ed.fill('저장 실패 후에도 이어 쓸 자료')
        expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집')
        p.reload();p.locator('nav [data-tab="rec"]').click();ed=self.material()
        expect(ed).to_contain_text('저장 실패 후에도 이어 쓸 자료');p.locator('#save-status [data-retry-edits]').click();self.wait_saved()
        self.assertIn('저장 실패 후에도',self.stored('refs','work-r')['html'])
        self.assertEqual(p.evaluate('__store.refs.length'),len(ui.SEED['refs']))

    def test_unrelated_remote_fields_and_conflicting_folder_changes_are_guarded(self):
        p=self.page;self.patch('notes','a',{'isFolder':True,'space':'work','title':'A'});self.patch('notes','b',{'isFolder':True,'space':'work','title':'B'})
        ed=self.material();ed.fill('본문만 고친 자료');self.patch('refs','work-r',{'title':'다른 기기 제목','fid':'a','fav':True})
        self.wait_saved();saved=self.stored('refs','work-r');self.assertEqual(saved['title'],'다른 기기 제목');self.assertEqual(saved['fid'],'a');self.assertTrue(saved['fav'])
        ed=self.material();p.locator('[data-rdoc-folder]').select_option('b');self.patch('refs','work-r',{'fid':''})
        self.wait_conflict();self.assertEqual(self.stored('refs','work-r')['fid'],'')
        self.assertEqual(self.drafts()['refs:work-r']['patch']['fid'],'b')

    def test_id_collision_keeps_ref_editor_connections_and_note_separate(self):
        p=self.page;self.patch('refs','work-n',{'title':'같은 ID의 자료','html':'<div>자료의 본문</div>','space':'work'})
        ed=self.material('work-n');expect(ed).to_contain_text('자료의 본문')
        source=p.locator('article.doc .connections-panel').get_attribute('data-connection-source')
        self.assertEqual(p.evaluate('s=>JSON.parse(decodeURIComponent(s)).c',source),'refs')
        ed.fill('자료만 고친 내용');self.wait_saved()
        self.assertEqual(self.stored('notes','work-n')['html'],'<div>중요한 결정</div>')
        self.assertIn('자료만 고친',self.stored('refs','work-n')['html'])
        p.locator('[data-closedoc]').click();p.locator('[data-archive-filter=""]').click()
        p.locator('[data-archive-open="doc"][data-id="work-n"]').click();expect(p.locator('[data-db]')).to_contain_text('중요한 결정')
        p.go_back();p.go_forward();expect(p.locator('[data-db]')).to_contain_text('중요한 결정')

    def test_prior_quick_form_draft_has_a_clear_continue_path(self):
        p=self.page;self.library();ui.resource_quick(p);p.locator('#r-t').fill('새 자료 임시 제목');p.locator('#r-b').fill('새 자료 임시 내용');p.locator('#sheet [data-sx]').click()
        ed=self.material();p.locator('.resource-settings').click();p.locator('#r-b').fill('이전 작성창에 남긴 내용');p.locator('#sheet [data-sx]').click()
        p.locator('[data-closedoc]').click();ed=self.material()
        expect(p.locator('.resource-draft-notice')).to_contain_text('저장 전 작성 내용')
        p.locator('.resource-draft-notice button').click();expect(p.locator('#r-b')).to_contain_text('이전 작성창에 남긴 내용')
        p.locator('[data-rsave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on')
        expect(p.locator('[data-rdoc-body]')).to_contain_text('이전 작성창에 남긴 내용')
        expect(p.locator('.resource-draft-notice')).to_have_count(0)

    def test_opening_settings_finishes_pending_body_save_before_form_edit(self):
        p=self.page;ed=self.material();ed.fill('넓은 화면에서 방금 고친 내용')
        p.locator('.resource-settings').click();expect(p.locator('#r-b')).to_contain_text('방금 고친 내용')
        p.locator('#r-b').fill('설정 창에서도 이어 고친 내용');p.locator('[data-rsave]').click()
        expect(p.locator('#scrim')).not_to_have_class('scrim on')
        self.assertIn('설정 창에서도',self.stored('refs','work-r')['html'])
        expect(p.locator('[data-rdoc-body]')).to_contain_text('설정 창에서도')

    def test_article_create_failure_and_repeated_click_keep_list_and_single_original(self):
        p=self.page;self.library();before=p.evaluate('__store.notes.length')
        p.evaluate('window.__failWrites=true');p.locator('.layout-write-group>[data-newdoc]').click()
        expect(p.locator('.toast')).to_contain_text('글을 만들지 못했어요');expect(p.locator('.archive-library')).to_be_visible()
        self.assertEqual(p.evaluate('__store.notes.length'),before)
        p.evaluate('window.__failWrites=false;window.__writeDelayMs=200')
        p.locator('.layout-write-group>[data-newdoc]').evaluate('b=>{b.click();b.click()}')
        expect(p.locator('[data-db]')).to_be_visible();self.assertEqual(p.evaluate('__store.notes.length'),before+1)

    def test_plain_lists_and_full_editor_fit_phone_and_desktop(self):
        p=self.page;out=Path('/workspace/arecmik-material-writing-release');out.mkdir(exist_ok=True)
        for width in [320,390,1365]:
            p.set_viewport_size({'width':width,'height':950});self.library()
            self.assertEqual(p.locator('.archive-row').first.evaluate("e=>getComputedStyle(e,'::before').content"),'none')
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
            p.screenshot(path=str(out/f'list-{width}.png'),full_page=True)
            p.locator('[data-archive-open="ref"][data-id="work-r"]').click()
            expect(p.locator('[data-rdoc-body]')).to_be_visible();self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)
            for selector in ['.resource-settings','article.doc .archive-favorite','[data-rdoc-purpose]','[data-rdoc-folder]']:
                self.assertGreaterEqual(p.locator(selector).bounding_box()['height'],44)
            p.screenshot(path=str(out/f'editor-{width}.png'),full_page=True)
            p.locator('[data-closedoc]').click()


if __name__=='__main__':unittest.main()

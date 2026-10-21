"""Deleting organizational containers must preserve records and payments."""
import unittest

from playwright.sync_api import expect
import test_archive as ui


class ContainerTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown
    life = ui.ArchiveTests.life

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          const ref=(c,id)=>m.doc(m.collection({},c),id);
          const folders=[
            {id:'parent',title:'일상',space:'life',fid:''},
            {id:'folder',title:'여행',space:'life',fid:'parent'},
            {id:'child',title:'사진',space:'life',fid:'folder'},
            {id:'work-folder',title:'업무',space:'work',fid:''}
          ];
          for(const {id,...data} of folders)await m.setDoc(ref('notes',id),{...data,isFolder:true});
          await m.updateDoc(ref('notes','life-n'),{fid:'folder'});
          await m.updateDoc(ref('notes','life-linked'),{fid:'child'});
          await m.updateDoc(ref('projects','life-p'),{tbl:{on:true,fields:[]}});
          await m.setDoc(ref('ents','vendor'),{pid:'life-p',title:'가구',v:{},items:[]});
          await m.updateDoc(ref('todos','life-t'),{eid:'vendor',title:'가구 예약'});
          await m.updateDoc(ref('exps','life-e'),{eid:'vendor',c:'가구',t:'가구 계약금'});
        }""")

    def project(self):
        self.life()
        self.page.locator("nav [data-tab='proj']").click()
        self.page.locator('[data-open="life-p"]').click()
        ui.project_details(self.page)

    def folder_manager(self):
        self.life()
        ui.record_source(self.page, 'doc')
        self.page.locator('[data-folder-manage]').click()

    def confirm_delete(self):
        self.page.locator('#sheet [data-sx="1"]').click()

    def test_mobile_folder_delete_moves_children_and_undo_restores_links(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.folder_manager()
        expect(self.page.locator('#folder-manager')).not_to_contain_text('업무')
        before = self.page.evaluate('window.__store.notes.length')
        self.page.locator('[data-folder-delete="folder"]').click()
        expect(self.page.locator('#sheet')).to_contain_text('기록은 남아요')
        self.confirm_delete()
        expect(self.page.locator('#folder-manager [data-folder-delete="folder"]')).to_have_count(0)
        self.assertEqual(self.page.evaluate('window.__store.notes.length'), before - 1)
        for record in ['life-n', 'child']:
            self.assertEqual(self.page.evaluate('(id)=>window.__store.notes.find(n=>n.id===id).fid', record), 'parent')
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='life-linked').fid"), 'child')
        self.assertTrue(self.page.evaluate("window.__store.notes.some(n=>n.id==='work-folder')"))
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
        self.page.locator('.toast button').click()
        expect(self.page.locator('#folder-manager [data-folder-delete="folder"]')).to_be_visible()
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='life-n').fid"), 'folder')
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='child').fid"), 'folder')

    def test_folder_cancel_or_failed_delete_changes_nothing(self):
        self.folder_manager()
        before = self.page.evaluate('window.__store.notes')
        self.page.locator('[data-folder-delete="folder"]').click()
        self.page.locator('#sheet [data-sx="0"]').click()
        expect(self.page.locator('#folder-manager')).to_be_visible()
        self.assertEqual(self.page.evaluate('window.__store.notes'), before)
        self.page.evaluate("window.__failWritesFor='trash'")
        self.page.locator('[data-folder-delete="folder"]').click()
        self.confirm_delete()
        expect(self.page.locator('.toast')).to_contain_text('삭제하지 못했어요')
        self.assertEqual(self.page.evaluate('window.__store.notes'), before)
        self.assertEqual(self.page.evaluate('window.__store.trash.length'), 0)

    def test_item_delete_keeps_tasks_and_payments_and_restores_from_trash(self):
        self.project()
        expect(self.page.locator('[data-trdel="vendor"]')).to_be_visible()
        self.page.locator('[data-trdel="vendor"]').click()
        expect(self.page.locator('#sheet')).to_contain_text('할 일과 지출은 남고')
        self.confirm_delete()
        expect(self.page.locator('[data-hrow="vendor"]')).to_have_count(0)
        self.assertEqual(self.page.evaluate('window.__store.todos.length'), len(ui.SEED['todos']))
        self.assertEqual(self.page.evaluate('window.__store.exps.length'), len(ui.SEED['exps']))
        task = self.page.evaluate("window.__store.todos.find(t=>t.id==='life-t')")
        expense = self.page.evaluate("window.__store.exps.find(e=>e.id==='life-e')")
        self.assertEqual(task['eid'], '')
        self.assertEqual(expense['eid'], '')
        self.assertEqual(expense['tid'], 'life-t')
        self.assertEqual(expense['a'], ui.SEED['exps'][0]['a'])
        self.assertEqual(expense['c'], '')
        expect(self.page.locator('.pcost .pcg-n')).not_to_contain_text(['가구'])
        self.page.locator('[data-menu]').click()
        self.page.locator('[data-trash]').click()
        self.page.locator('[data-rest="ents_vendor"]').click()
        self.page.wait_for_function("window.__store.ents.some(e=>e.id==='vendor')")
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='life-t').eid"), 'vendor')
        self.assertEqual(self.page.evaluate("window.__store.exps.find(e=>e.id==='life-e').c"), '가구')

    def test_item_failure_is_atomic_and_deleted_name_does_not_reattach(self):
        self.project()
        self.page.evaluate("window.__failWritesFor='todos'")
        self.page.locator('[data-trdel="vendor"]').click()
        self.confirm_delete()
        expect(self.page.locator('.toast')).to_contain_text('삭제하지 못했어요')
        self.assertEqual(self.page.evaluate('window.__store.ents.length'), 1)
        self.assertEqual(self.page.evaluate('window.__store.trash.length'), 0)
        self.assertEqual(self.page.evaluate("window.__store.todos.find(t=>t.id==='life-t').eid"), 'vendor')
        self.page.evaluate('window.__failWritesFor=null')
        self.page.locator('[data-trdel="vendor"]').click()
        self.confirm_delete()
        self.page.wait_for_function('window.__store.ents.length===0')
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await m.setDoc(m.doc(m.collection({},'ents'),'new-vendor'),{pid:'life-p',title:'가구',v:{},items:[]});
        }""")
        expect(self.page.locator('[data-hrow="new-vendor"]')).to_be_visible()
        self.page.locator('[data-hrow="new-vendor"] b').first.click()
        expect(self.page.locator('.hrf [data-drag="life-t"]')).to_have_count(0)
        expect(self.page.locator('.hrf .hrp-r')).to_have_count(0)

    def test_undo_does_not_overwrite_later_folder_assignment(self):
        self.folder_manager()
        self.page.locator('[data-folder-delete="folder"]').click()
        self.confirm_delete()
        self.page.wait_for_function("!window.__store.notes.some(n=>n.id==='folder')")
        self.page.evaluate("""async () => {
          const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await m.updateDoc(m.doc(m.collection({},'notes'),'life-n'),{fid:'child'});
        }""")
        self.page.locator('.toast button').click()
        self.page.wait_for_function("window.__store.notes.some(n=>n.id==='folder')")
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='life-n').fid"), 'child')

    def test_cancel_renaming_cost_category_preserves_name(self):
        self.project()
        self.page.locator('.pcost [data-pcgr]').click()
        expect(self.page.locator('#atx')).to_have_value('가구')
        self.page.locator('#sheet [data-sx="0"]').click()
        self.assertEqual(self.page.evaluate("window.__store.exps.find(e=>e.id==='life-e').c"), '가구')
        expect(self.page.locator('.pcost [data-pcgr]')).to_have_text('가구')
        self.page.locator('[data-pcgs]').select_option('__new')
        self.page.locator('#sheet [data-sx="0"]').click()
        expect(self.page.locator('[data-pcgs] option')).not_to_contain_text(['false'])

    def test_existing_false_category_displays_safely_and_amount_is_preserved(self):
        self.project()
        for bad_value in ['false', False, None]:
            self.page.evaluate("""async value => {
              const m=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
              await m.updateDoc(m.doc(m.collection({},'exps'),'life-e'),{c:value,eid:'',tid:'',t:'계약금'});
            }""", bad_value)
            self.page.locator('[data-zoom="near"]').click()
            expect(self.page.locator('.pcost .pcg-n')).to_have_count(0)
            expect(self.page.locator('[data-pcgs] option')).not_to_contain_text(['false'])
            self.assertEqual(self.page.evaluate("window.__store.exps.find(e=>e.id==='life-e').a"), ui.SEED['exps'][0]['a'])
            self.page.locator('.pcost [data-xedit] .ttx').dblclick()
            expect(self.page.locator('#x-c')).to_have_value('')
            self.page.locator('#sheet [data-sx="0"]').click()


if __name__ == '__main__':
    unittest.main()

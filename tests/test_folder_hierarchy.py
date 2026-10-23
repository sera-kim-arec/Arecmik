"""Nested folders remain visibly nested through sidebar and phone navigation."""
import unittest
from pathlib import Path

from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class FolderHierarchyTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown
    patch = editors.BlockEditorTests.patch

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        # Deliberately store children before their parent, with two equal names.
        for ident, title, parent in [
            ('hier-grand', '계약서', 'hier-child'),
            ('hier-other', 'B 운영', ''),
            ('hier-other-child', '가이드', 'hier-other'),
            ('hier-child', '가이드', 'hier-root'),
            ('hier-root', 'A 업무', ''),
        ]:
            self.patch('notes', ident, {'isFolder': True, 'title': title,
                       'fid': parent, 'space': 'work', 'created': 1})
        for ident, title, parent in [
            ('hier-root-doc', '업무 안내', 'hier-root'),
            ('hier-child-doc', '채용 가이드', 'hier-child'),
            ('hier-grand-doc', '계약서 작성 양식', 'hier-grand'),
            ('hier-other-doc', '별도 운영 자료', 'hier-other'),
        ]:
            self.patch('refs', ident, {'title': title,
                       'html': '<div>' + title + ' 본문</div>',
                       'fid': parent, 'space': 'work', 'created': ui.STAMP})
        self.patch('notes', 'work-n', {'fid': 'hier-grand'})
        self.page.locator('[data-archive-filter="ref"]').click()

    def sidebar(self, ident):
        return self.page.locator('.archive-folders [data-archive-folder="' + ident + '"]')

    def toggle(self, ident):
        return self.page.locator('[data-archive-folder-toggle="' + ident + '"]')

    def expand(self, ident):
        button = self.toggle(ident)
        if button.get_attribute('aria-expanded') != 'true':
            button.click()

    def child(self, ident):
        return self.page.locator('.archive-child-folders [data-archive-folder-open="' + ident + '"]')

    def current(self, label):
        expect(self.page.locator('.archive-breadcrumb [aria-current]')).to_have_text(label)

    def test_sidebar_labels_indentation_and_disclosures_show_parent_child_relationships(self):
        p = self.page
        p.set_viewport_size({'width': 1365, 'height': 950})
        self.expand('hier-root')
        self.expand('hier-child')
        root, child, grand = [self.sidebar(ident) for ident in
                              ['hier-root', 'hier-child', 'hier-grand']]
        for button, title in [(root, 'A 업무'), (child, '가이드'), (grand, '계약서')]:
            expect(button.locator('span').first).to_have_text(title)
            self.assertNotIn('/', button.inner_text())
        positions = [row.locator('span').first.bounding_box()['x'] for row in [root, child, grand]]
        self.assertLess(positions[0], positions[1])
        self.assertLess(positions[1], positions[2])
        self.assertTrue(self.toggle('hier-root').get_attribute('aria-controls'))
        expect(self.toggle('hier-root')).to_have_attribute('aria-expanded', 'true')
        output = Path('/workspace/arecmik-folder-hierarchy-release')
        output.mkdir(exist_ok=True)
        p.screenshot(path=str(output / 'library-tree-1365.png'), full_page=True)

    def test_collapsing_parent_keeps_selected_descendant_and_its_results(self):
        p = self.page
        self.expand('hier-root')
        self.expand('hier-child')
        self.sidebar('hier-grand').click()
        self.current('계약서')
        expect(p.locator('.archive-list')).to_contain_text('계약서 작성 양식')
        expect(p.locator('.archive-list')).not_to_contain_text('별도 운영 자료')
        self.toggle('hier-root').click()
        expect(self.toggle('hier-root')).to_have_attribute('aria-expanded', 'false')
        expect(self.sidebar('hier-grand')).to_be_hidden()
        self.current('계약서')
        expect(p.locator('.archive-list')).to_contain_text('계약서 작성 양식')
        self.toggle('hier-root').click()
        expect(self.sidebar('hier-grand')).to_have_attribute('aria-pressed', 'true')

    def test_breadcrumb_and_direct_children_navigate_hierarchy_and_back_keeps_parent(self):
        p = self.page
        self.child('hier-root').click()
        self.current('A 업무')
        expect(self.child('hier-child')).to_be_visible()
        expect(self.child('hier-grand')).to_have_count(0)
        # Parent scope still includes material in all descendant folders.
        expect(p.locator('.archive-list')).to_contain_text('계약서 작성 양식')
        expect(p.locator('.archive-list')).not_to_contain_text('업무 회의록')
        self.child('hier-child').click()
        self.current('가이드')
        expect(self.child('hier-grand')).to_be_visible()
        self.child('hier-grand').click()
        self.current('계약서')
        expect(p.locator('.archive-breadcrumb [data-archive-folder-open="hier-root"]')).to_have_text('A 업무')
        expect(p.locator('.archive-breadcrumb [data-archive-folder-open="hier-child"]')).to_have_text('가이드')
        p.go_back()
        self.current('가이드')
        expect(self.child('hier-grand')).to_be_visible()
        p.locator('.archive-breadcrumb [data-archive-folder-open="hier-root"]').click()
        self.current('A 업무')
        expect(self.child('hier-child')).to_be_visible()

    def test_phone_selector_groups_descendants_and_folder_navigation_fits(self):
        p = self.page
        for width in [320, 390]:
            p.set_viewport_size({'width': width, 'height': 950})
            p.locator('[data-archive-filter="ref"]').click()
            select = p.locator('[data-archive-folder-select]')
            values = select.locator('option').evaluate_all('els=>els.map(e=>e.value)')
            self.assertEqual([v for v in values if v.startswith('hier-')],
                             ['hier-root', 'hier-child', 'hier-grand', 'hier-other', 'hier-other-child'])
            select.select_option('hier-child')
            self.current('가이드')
            self.child('hier-grand').click()
            self.current('계약서')
            self.assertEqual(select.input_value(), 'hier-grand')
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'), width)
            expect(p.locator('.archive-list')).to_contain_text('계약서 작성 양식')
            p.locator('.archive-breadcrumb [data-archive-folder-open="hier-child"]').click()
            self.current('가이드')
            child = self.child('hier-grand')
            self.assertGreaterEqual(child.bounding_box()['height'], 44)
            self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'), width)
            if width == 390:
                output = Path('/workspace/arecmik-folder-hierarchy-release')
                output.mkdir(exist_ok=True)
                p.screenshot(path=str(output / 'library-children-390.png'), full_page=True)

    def test_new_subfolder_keeps_its_parent_and_original_documents(self):
        p = self.page
        self.child('hier-root').click()
        self.child('hier-child').click()
        before = p.evaluate('JSON.stringify(__store.refs)')
        p.locator('.archive-folder-heading [data-newf]').click()
        expect(p.locator('#folder-parent')).to_have_value('hier-child')
        p.locator('#folder-title').fill('온보딩')
        p.locator('[data-folder-create]').click()
        expect(p.locator('#scrim')).not_to_have_class('scrim on')
        self.current('온보딩')
        created = p.evaluate("__store.notes.find(n=>n.isFolder&&n.title==='온보딩')")
        self.assertEqual(created['fid'], 'hier-child')
        self.assertEqual(p.evaluate('JSON.stringify(__store.refs)'), before)
        p.locator('.archive-breadcrumb [data-archive-folder-open="hier-child"]').click()
        expect(self.child(created['id'])).to_be_visible()


if __name__ == '__main__':
    unittest.main()

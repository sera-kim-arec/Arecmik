"""Favorites preserve existing pins and original content; no account is accessed."""
import unittest

from playwright.sync_api import expect
import test_archive as ui


class FavoriteTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown
    search = ui.ArchiveTests.search

    def patch(self, c, ident, data):
        self.page.evaluate("""async ([c,id,data])=>{
          const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          await f.setDoc(f.doc(f.collection({},c),id),data,{merge:true});
        }""", [c, ident, data])

    def test_legacy_pins_survive_without_home_or_project_duplicates(self):
        self.patch('moms','work-m',{'pinned':True,'pid':'work-p'})
        self.patch('refs','work-r',{'fav':True})
        p=self.page;p.reload()
        p.locator('nav [data-tab="home"]').click()
        expect(p.locator('main')).not_to_contain_text('고정한 것')
        expect(p.locator('[data-memo="memo_work"]')).to_be_visible()
        p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="work-p"]').click()
        expect(p.locator('[data-pmemo]')).to_have_text('업무 프로젝트 메모')
        expect(p.locator('.pcore')).not_to_contain_text('업무 회의 회고')
        p.locator('nav [data-tab="rec"]').click();p.locator('[data-archive-favorites]').click()
        expect(p.locator('.archive-list .archive-row')).to_have_count(2)
        expect(p.locator('.archive-list')).to_contain_text('업무 회의 회고')
        expect(p.locator('.archive-list')).to_contain_text('업무 자료')
        self.assertEqual(p.evaluate('window.__store.moms.length'),len(ui.SEED['moms']))

    def test_failed_favorite_and_double_click_preserve_content_and_state(self):
        p=self.page;star=p.locator('[data-archive-favorite="doc"][data-id="work-n"]')
        p.evaluate("window.__failWritesFor='notes'");star.click()
        expect(p.locator('.toast')).to_contain_text('변경하지 못했어요')
        expect(star).to_have_attribute('aria-pressed','false')
        self.assertEqual(p.evaluate("window.__store.notes.find(n=>n.id==='work-n').html"),'<div>중요한 결정</div>')
        p.evaluate('window.__failWritesFor=null;window.__writeDelayMs=350')
        star.evaluate('b=>{b.click();b.click()}')
        expect(star).to_have_attribute('aria-pressed','true')
        p.reload();p.locator('[data-archive-favorites]').click()
        expect(p.locator('.archive-list')).to_contain_text('업무 회의록')
        p.locator('[data-archive-favorite="doc"][data-id="work-n"]').click()
        expect(p.locator('.archive-empty')).to_contain_text('즐겨찾기가 없어요')
        p.locator('[data-archive-reset]').click()
        expect(p.locator('.archive-list')).to_contain_text('업무 회의록')

    def test_monthly_diary_favorites_remain_specific_to_one_day(self):
        html="<div class='h2 dayh'>10/14 (수)</div><div>첫째 날 기록</div><div class='h2 dayh'>10/15 (목)</div><div>둘째 날 기록</div>"
        self.patch('notes','work-month',{'space':'work','log':True,'mon':'2026-10','html':html,'updated':1792022400000,'favoriteDays':{'2026-10-15':True}})
        p=self.page;p.locator('[data-archive-favorite="log"][data-id="2026-10-14"]').click()
        expect(p.locator('[data-archive-favorite="log"][data-id="2026-10-14"]')).to_have_attribute('aria-pressed','true')
        p.locator('[data-archive-favorites]').click()
        expect(p.locator('.archive-list .archive-row')).to_have_count(2)
        p.locator('[data-archive-favorite="log"][data-id="2026-10-14"]').click()
        expect(p.locator('.archive-list .archive-row')).to_have_count(1)
        self.assertEqual(p.evaluate("window.__store.notes.find(n=>n.id==='work-month').favoriteDays"),{'2026-10-14':False,'2026-10-15':True})
        self.assertEqual(p.evaluate("window.__store.notes.find(n=>n.id==='work-month').html"),html)

    def test_filters_space_and_back_keep_favorites_scope(self):
        self.patch('moms','work-m',{'pinned':True,'pid':'work-p'})
        self.patch('moms','life-m',{'pinned':True})
        p=self.page;p.set_viewport_size({'width':390,'height':844})
        p.locator('[data-archive-favorites]').click();p.locator('[data-archive-project]').select_option('work-p')
        p.locator('[data-archive-open="mom"][data-id="work-m"]').click();p.go_back()
        expect(p.locator('[data-archive-favorites]')).to_have_attribute('aria-pressed','true')
        expect(p.locator('[data-archive-project]')).to_have_value('work-p')
        p.locator('[data-sp="life"]').click();p.locator('[data-archive-favorites]').click()
        expect(p.locator('.archive-list')).to_contain_text('바닷가 산책')
        expect(p.locator('.archive-list')).not_to_contain_text('업무 회의 회고')
        p.locator('[data-sp="work"]').click()
        expect(p.locator('.archive-list')).to_contain_text('업무 회의 회고')
        self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),390)
        box=p.locator('[data-archive-favorite="mom"][data-id="work-m"]').bounding_box()
        self.assertGreaterEqual(min(box['width'],box['height']),44)

    def test_favorited_undated_task_is_available_even_before_completion(self):
        p=self.page;self.search('보고서 제출')
        p.locator('#sqr [data-archive-favorite="todo"][data-id="work-t"]').click()
        expect(p.locator('#sqr [data-archive-favorite="todo"]')).to_have_attribute('aria-pressed','true')
        p.locator('#sqi').press('Escape');p.locator('[data-archive-favorites]').click()
        expect(p.locator('.archive-list')).to_contain_text('보고서 제출')
        self.assertFalse(p.evaluate("window.__store.todos.find(t=>t.id==='work-t').done"))

    def test_repeat_favorites_belong_to_the_original_occurrence(self):
        self.patch('todos','work-t',{'kind':'event','date':'2026-10-19','rep':'d'})
        p=self.page;self.search('보고서 제출')
        p.locator('#sqr [data-archive-favorite="todo"][data-id="work-t"]').click()
        expect(p.locator('#sqr [data-archive-favorite="todo"]')).to_have_attribute('aria-pressed','true')
        p.locator('#sqi').press('Escape');p.locator('nav [data-tab="home"]').click()
        p.locator('[data-pick="2026-10-19"]').first.click();p.locator('.dside [data-ck="work-t"]').click()
        p.wait_for_function("window.__store.todos.some(t=>t.date==='2026-10-20')")
        following=p.evaluate("window.__store.todos.find(t=>t.date==='2026-10-20')")
        self.assertNotIn('fav',following)
        # Native repeats can copy optional fields; the original source ID must
        # prevent a copied star from selecting the next occurrence.
        self.patch('todos',following['id'],{'fav':True,'favSourceId':'work-t'})
        if p.locator('#srch.on').count():p.locator('#sqi').press('Escape')
        p.locator('nav [data-tab="rec"]').click();p.locator('[data-archive-favorites]').click()
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_count(1)
        expect(p.locator('.archive-list [data-archive-open="todo"]')).to_have_attribute('data-id','work-t')

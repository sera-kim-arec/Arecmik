"""Actual writing/deleting and storage round trips on every rich-text surface.
Firebase is mocked; no user records are opened or modified.
"""
import json
import re
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors

SURFACES=('home_memo','home_journal','journal','article','project_core','project_history','record','task','reference','expense')

class EditorSurfaceTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    patch=editors.BlockEditorTests.patch
    choose=editors.BlockEditorTests.choose

    def open_surface(self):
        p=self.page;s=self.surface;sp=self.space
        if s in ('home_memo','home_journal'):
            p.locator('nav [data-tab="home"]').click();selector='[data-memo]' if s=='home_memo' else '[data-log]';ui.reveal(p,selector)
        elif s=='journal':
            p.locator('nav [data-tab="rec"]').click();ui.record_source(p,'log');selector='[data-log]'
        elif s in ('project_core','project_history'):
            p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="'+sp+'-p"]').click();ui.project_details(p);selector='[data-pmemo]' if s=='project_core' else '[data-mt="'+sp+'-m"]'
        else:
            query={'article':('업무 회의록' if sp=='work' else '숙소 후보','doc'),'record':('업무 회의 회고' if sp=='work' else '바닷가 산책','mom'),'task':('보고서 제출' if sp=='work' else '숙소 예약','todo'),'reference':('업무 자료' if sp=='work' else '여행 자료','ref'),'expense':('숙박 결제','expense')}[s]
            if s=='record':query=(p.evaluate("id=>__store.moms.find(m=>m.id===id).t",sp+'-m').split('\n')[0],'mom')
            self.search(query[0]);p.locator('#sqr [data-sgo="'+query[1]+'"]').first.click()
            selector={'article':'[data-db]','record':'#record-body','task':'#e-n','reference':'[data-db]','expense':'#x-m'}[s]
        ed=p.locator(selector).first;expect(ed).to_be_visible();expect(ed).to_have_class(re.compile(r'\bnb-editor\b'))
        return ed

    def save(self):
        button={'record':'[data-record-save]','task':'[data-esave]','expense':'[data-xsave]'}.get(self.surface)
        if button:
            self.page.locator(button).click();expect(self.page.locator('#scrim')).not_to_have_class('scrim on')
        else:
            # Navigation invokes the app's actual pending-autosave flush.
            self.page.locator('nav [data-tab="rec"]').click()

    def exercise(self,surface,space,width):
        self.surface=surface;self.space=space;p=self.page;p.set_viewport_size({'width':width,'height':900})
        if space=='life':p.locator('[data-sp="life"]').click()
        if surface=='project_history':self.patch('moms',space+'-m',{'pid':space+'-p'})
        if surface=='project_core':self.patch('projects',space+'-p',{'mods':{'memo':True}})
        ed=self.open_surface();marker='편집점검_'+surface+'_'+space+'_'+str(width)
        before=p.evaluate('JSON.stringify(__store)')
        # Type paragraphs with the keyboard, erase the middle line, and merge.
        ed.click();p.keyboard.press('Control+a');p.keyboard.press('Backspace');expect(ed).to_have_text('')
        p.keyboard.insert_text(marker);p.keyboard.press('Enter');p.keyboard.insert_text('지울 줄');p.keyboard.press('Enter');p.keyboard.insert_text('남길 줄')
        middle=ed.locator(':scope > div').nth(1);middle.click();p.keyboard.press('Home');p.keyboard.press('Shift+End');p.keyboard.press('Backspace');p.keyboard.press('Backspace')
        expect(ed.locator(':scope > div')).to_have_text([marker,'남길 줄'])
        p.keyboard.press('Delete');expect(ed.locator(':scope > div')).to_have_text([marker+'남길 줄'])
        # Replace all, create a nested block, and delete its trailing empty line.
        p.keyboard.press('Control+a');p.keyboard.press('Delete');expect(ed).to_have_text('')
        p.keyboard.type('> ');p.keyboard.insert_text(marker);p.keyboard.press('Enter');p.keyboard.insert_text('보존할 본문');p.keyboard.press('Enter');p.keyboard.press('Backspace')
        expect(ed.locator('.nb-toggle-body > div')).to_have_text(['보존할 본문'])
        p.wait_for_timeout(550)
        p.keyboard.press('Control+a');p.keyboard.press('Backspace');expect(ed).to_have_text('');expect(ed.locator('.nb-toggle')).to_have_count(0)
        p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-title')).to_have_text(marker);expect(ed.locator('.nb-toggle-body')).to_have_text('보존할 본문')
        p.keyboard.press('Control+Shift+z');expect(ed).to_have_text('');p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-body')).to_have_text('보존할 본문')
        ed.locator('.nb-toggle-title').evaluate("el=>{el.focus();const r=document.createRange();r.selectNodeContents(el);r.collapse(false);getSelection().removeAllRanges();getSelection().addRange(r)}");p.keyboard.insert_text(' 저장확인')
        self.save();p.wait_for_function("marker=>JSON.stringify(__store).includes(marker+' 저장확인')",arg=marker)
        p.reload();ed=self.open_surface();expect(ed.locator('.nb-toggle-title')).to_have_text(marker+' 저장확인');expect(ed.locator('.nb-toggle-body')).to_have_text('보존할 본문')
        # Empty existing memo bodies must stay empty after a real save/reopen.
        ed.click();p.keyboard.press('Control+a');p.keyboard.press('Backspace');expect(ed).to_have_text('')
        if surface=='record':
            # Records require body text: an empty save must retain the old record.
            p.locator('[data-record-save]').click();expect(p.locator('#scrim')).to_have_class('scrim on');expect(ed).to_have_attribute('aria-invalid','true')
            p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-body')).to_have_text('보존할 본문')
        else:
            self.save();p.wait_for_function("marker=>!JSON.stringify(__store).includes(marker)",arg=marker)
            p.reload();ed=self.open_surface();expect(ed).to_have_text('');expect(ed.locator('.nb-toggle')).to_have_count(0)
        # Other-space records must not change while editing this surface.
        old=json.loads(before);after=p.evaluate('__store')
        for collection in ('notes','moms','projects','todos','refs','exps'):
            for row in old.get(collection,[]):
                if row.get('space',row.get('sp')) in ('work','life') and row.get('space',row.get('sp'))!=space:
                    self.assertIn(row,after[collection],(surface,space,width,collection,row['id']))
        self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),width)

    def clear_one_journal_day(self,space):
        p=self.page
        if space=='life':p.locator('[data-sp="life"]').click()
        ident='qa-month-'+space
        self.patch('notes',ident,{'title':'삭제 보존 검사','log':True,'mon':'2026-10','space':space,'html':'<div class="h2 dayh">10/15 (목)</div><div>지울 날짜의 글</div><div class="h2 dayh">10/16 (금)</div><div>다른 날의 소중한 기록</div>'})
        p.locator('nav [data-tab="rec"]').click();ui.record_source(p,'log');p.locator('[data-elog="2026-10-15"]').click()
        ed=p.locator('[data-log="2026-10-15"]');ed.click();p.keyboard.press('Control+a');p.keyboard.press('Backspace');p.locator('nav [data-tab="home"]').click()
        p.wait_for_function("id=>!__store.notes.find(n=>n.id===id).html.includes('지울 날짜의 글')",arg=ident)
        html=p.evaluate("id=>__store.notes.find(n=>n.id===id).html",ident);self.assertIn('다른 날의 소중한 기록',html)
        p.reload();p.locator('nav [data-tab="rec"]').click();ui.record_source(p,'log')
        expect(p.locator('[data-elog="2026-10-16"]')).to_have_text('다른 날의 소중한 기록')

    def test_clear_journal_day_preserves_other_days_work(self):self.clear_one_journal_day('work')
    def test_clear_journal_day_preserves_other_days_life(self):self.clear_one_journal_day('life')


def make_test(surface,space,width):
    def test(self):self.exercise(surface,space,width)
    test.__name__='test_'+surface+'_'+space+'_'+str(width)
    return test

for surface in SURFACES:
    for space in ('work','life'):
        if surface=='expense' and space=='work':continue
        for width in (1365,390):setattr(EditorSurfaceTests,'test_'+surface+'_'+space+'_'+str(width),make_test(surface,space,width))

"""Shared block writing must preserve legacy documents, nesting and autosave."""
import unittest
from pathlib import Path
from playwright.sync_api import expect
import test_archive as ui
from test_memo_images import PNG


class BlockEditorTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown
    search = ui.ArchiveTests.search

    def patch(self, collection, ident, fields):
        self.page.evaluate("""async ([c,id,v])=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.setDoc(f.doc(f.collection({},c),id),v,{merge:true})}""",[collection,ident,fields])

    def note(self):
        self.search('업무 회의록');self.page.locator('#sqr [data-sgo="doc"]').click()
        expect(self.page.locator('[data-db].nb-editor')).to_be_visible()
        return self.page.locator('[data-db]')

    def choose(self, label):
        self.page.locator('.nb-menu [data-block-command]').filter(has_text=label).first.click()

    def test_toggle_body_stays_nested_formats_and_survives_reload(self):
        p=self.page;ed=self.note();ed.fill('');ed.press('/');self.choose('토글')
        p.keyboard.insert_text('이번 주 확정할 것');p.keyboard.press('Enter')
        p.keyboard.type('- ');p.keyboard.insert_text('최종 조건 확인')
        expect(ed.locator('.nb-toggle-body .li')).to_have_text('최종 조건 확인')
        p.keyboard.press('Enter');p.keyboard.press('Enter');p.keyboard.press('Enter')
        p.keyboard.insert_text('토글 밖의 다음 문단')
        expect(ed.locator(':scope > div').last).to_have_text('토글 밖의 다음 문단')
        ed.locator('.nb-toggle-arrow').click();expect(ed.locator('.nb-toggle-body')).to_be_hidden()
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('data-expanded=\"false\"')")
        saved=p.evaluate("__store.notes.find(n=>n.id==='work-n').html")
        self.assertNotIn('nb-toggle-arrow',saved);self.assertNotIn('ProseMirror',saved)
        p.reload();ed=self.note();expect(ed.locator('.nb-toggle-body')).to_be_hidden()
        ed.locator('.nb-toggle-arrow').click();expect(ed.locator('.nb-toggle-body .li')).to_have_text('최종 조건 확인')
        expect(ed).to_contain_text('토글 밖의 다음 문단')

    def test_nested_toggle_photo_remains_inside_parent_and_undo_redo_works(self):
        p=self.page;ed=self.note();ed.fill('');p.keyboard.type('> ');p.keyboard.insert_text('큰 토글');p.keyboard.press('Enter')
        p.keyboard.type('> ');p.keyboard.insert_text('작은 토글');p.keyboard.press('Enter');p.keyboard.insert_text('안쪽 내용')
        expect(ed.locator('.nb-toggle .nb-toggle')).to_have_count(1)
        with p.expect_file_chooser() as picker:
            p.keyboard.press('Enter');p.keyboard.press('/');self.choose('사진')
        picker.value.set_files({'name':'photo.png','mimeType':'image/png','buffer':PNG})
        expect(ed.locator('.nb-toggle .nb-toggle img[data-img]')).to_have_count(1)
        ed.locator('.nb-toggle-arrow').first.click();expect(ed.locator('img[data-img]')).to_be_hidden()
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('data-img')")
        p.reload();ed=self.note();expect(ed.locator('img[data-img]')).to_be_hidden()
        ed.locator('.nb-toggle-arrow').first.click();expect(ed.locator('img[data-img]')).to_be_visible()
        ed.locator('.nb-toggle-title').last.click();p.keyboard.press('End');p.keyboard.insert_text(' 추가')
        p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-title').last).to_have_text('작은 토글')
        p.keyboard.press('Control+Shift+z');expect(ed.locator('.nb-toggle-title').last).to_have_text('작은 토글 추가')

    def test_legacy_toggle_and_inline_formatting_are_not_rewritten_on_open(self):
        html='<div class="tgl open"><strong>기존 제목</strong></div><div class="tgc"><em>기존 본문</em></div><div class="tgc todo on">확인한 항목</div><div class="h2 dayh">10/22 (목)</div><div>다음 문단</div>'
        self.patch('notes','work-n',{'html':html});before=self.page.evaluate('JSON.stringify(__store)')
        ed=self.note();expect(ed.locator('.nb-toggle-title strong')).to_have_text('기존 제목')
        expect(ed.locator('.nb-toggle-body em')).to_have_text('기존 본문')
        expect(ed.locator('.nb-toggle-body .todo.on')).to_have_text('확인한 항목')
        self.page.wait_for_timeout(700);self.assertEqual(self.page.evaluate('JSON.stringify(__store)'),before)
        ed.locator('.nb-toggle-title').click();self.page.keyboard.press('End');self.page.keyboard.insert_text(' 보완')
        self.page.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('보완')")
        self.page.reload();ed=self.note();expect(ed.locator('.nb-toggle-body em')).to_have_text('기존 본문')
        expect(ed.locator('.dayh')).to_have_text('10/22 (목)')

    def test_slash_conversion_preserves_formatted_text_and_block_move_is_reversible(self):
        p=self.page;ed=self.note();ed.fill('');p.keyboard.press('Control+b');p.keyboard.insert_text('중요한 내용');p.keyboard.press('Control+b');p.keyboard.type(' /h2');p.keyboard.press('Enter')
        expect(ed.locator('.h2 strong')).to_have_text('중요한 내용')
        p.keyboard.press('End');p.keyboard.press('Enter');p.keyboard.insert_text('아래 문단')
        p.keyboard.press('Alt+ArrowUp')
        expect(ed.locator(':scope > div').first).to_have_text('아래 문단')
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div').last).to_have_text('아래 문단')
        expect(ed.locator('.h2 strong')).to_have_text('중요한 내용')

    def test_backspace_unwraps_toggle_without_losing_nested_content(self):
        p=self.page;ed=self.note();ed.fill('');p.keyboard.type('> ');p.keyboard.insert_text('제목');p.keyboard.press('Enter');p.keyboard.insert_text('보존할 본문')
        ed.locator('.nb-toggle-title').click();p.keyboard.press('Home');p.keyboard.press('Backspace')
        expect(ed.locator('.nb-toggle')).to_have_count(0);expect(ed).to_contain_text('제목');expect(ed).to_contain_text('보존할 본문')
        p.keyboard.press('Control+z');expect(ed.locator('.nb-toggle-body')).to_contain_text('보존할 본문')

    def test_all_surfaces_share_editor_and_failed_autosave_keeps_structure(self):
        p=self.page;p.locator('nav [data-tab="home"]').click();ui.reveal(p,'[data-memo]')
        for selector in ['[data-memo]','[data-log]']:
            expect(p.locator(selector+'.nb-editor').first).to_be_attached()
        p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="work-p"]').click();ui.project_details(p)
        expect(p.locator('[data-pmemo].nb-editor')).to_be_attached()
        self.search('보고서 제출');p.locator('#sqr [data-sgo="todo"]').click();expect(p.locator('#e-n.nb-editor')).to_be_visible();p.locator('#sheet [data-sx="0"]').click();p.keyboard.press('Escape')
        p.locator('nav [data-tab="rec"]').click();ui.record_new(p);expect(p.locator('#record-body.nb-editor')).to_be_visible();p.locator('#sheet [data-sx="0"]').click()
        ed=self.note();p.evaluate('window.__failWrites=true');ed.fill('');p.keyboard.type('> ');p.keyboard.insert_text('실패해도 남을 제목');p.keyboard.press('Enter');p.keyboard.insert_text('실패해도 남을 본문')
        expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집')
        p.reload();p.locator('[data-local-recovery]').click();expect(p.locator('.recovery-preview')).to_contain_text('실패해도 남을 본문');p.locator('[data-recover-edit]').click();expect(p.locator('[data-db] .nb-toggle-body')).to_contain_text('실패해도 남을 본문')

    def test_mobile_menu_and_toggle_fit_and_composition_does_not_run_commands(self):
        p=self.page;p.set_viewport_size({'width':360,'height':800});ed=self.note();ed.fill('');p.keyboard.press('/')
        expect(p.locator('.nb-menu')).to_be_visible();self.assertLessEqual(p.locator('.nb-menu').bounding_box()['x']+p.locator('.nb-menu').bounding_box()['width'],360)
        self.choose('토글');p.keyboard.insert_text('휴대폰에서 접을 제목');p.keyboard.press('Enter');p.keyboard.insert_text('가나다 한글 입력')
        ed.evaluate("e=>{e.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true}));e.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}));}")
        expect(ed.locator('.nb-toggle-body')).to_have_text('가나다 한글 입력');self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),360)
        Path('/workspace/arecmik-editor-review').mkdir(exist_ok=True)
        p.screenshot(path='/workspace/arecmik-editor-review/mobile-toggle.png',full_page=True)

    def test_link_shortcut_and_escape_close_editor_menu_before_the_sheet(self):
        p=self.page;self.search('보고서 제출');p.locator('#sqr [data-sgo="todo"]').click();ed=p.locator('#e-n');ed.fill('')
        p.keyboard.press('/');expect(p.locator('.nb-menu')).to_be_visible();p.keyboard.press('Escape')
        expect(p.locator('.nb-menu')).to_have_count(0);expect(ed).to_be_visible();p.keyboard.press('Control+k');expect(p.locator('.nb-link-dialog')).to_be_visible();p.keyboard.press('Escape');expect(p.locator('.nb-menu')).to_have_count(0)
        ed.fill('선택한 문구');p.keyboard.press('Control+a');p.keyboard.press('Control+k')
        expect(p.locator('.nb-link-dialog')).to_be_visible();expect(p.locator('#srch')).not_to_have_class('srov on')
        p.locator('#nb-link-url').fill('https://example.com/guide');p.locator('.nb-link-dialog [type=submit]').click()
        expect(ed.locator('a')).to_have_text('선택한 문구');expect(ed.locator('a')).to_have_attribute('href','https://example.com/guide')
        p.locator('[data-esave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');self.search('보고서 제출');p.locator('#sqr [data-sgo="todo"]').click()
        expect(p.locator('#e-n a')).to_have_text('선택한 문구')

    def test_drag_moves_whole_toggle_with_its_body_and_can_be_undone(self):
        html='<div>위 문단</div><div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">이동할 토글</div><div class="nb-toggle-body"><div>함께 이동할 본문</div></div></div><div>아래 문단</div>'
        self.patch('notes','work-n',{'html':html});p=self.page;ed=self.note();ed.locator('.nb-toggle-title').click()
        handle=p.locator('[data-block-menu]');target=ed.locator(':scope > div').first
        handle.drag_to(target,target_position={'x':20,'y':1})
        expect(ed.locator(':scope > div').first).to_have_class('nb-toggle')
        expect(ed.locator('.nb-toggle-body')).to_have_text('함께 이동할 본문')
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div').first).to_have_text('위 문단')
        expect(ed.locator('.nb-toggle-body')).to_have_text('함께 이동할 본문')

    def test_rich_paste_preserves_nesting_and_readonly_toggle_is_keyboard_accessible(self):
        html='<div class="h2">메모 제목</div><div class="nb-toggle" data-expanded="false"><div class="nb-toggle-title">자세히 보기</div><div class="nb-toggle-body"><div><strong>중요한 본문</strong></div></div></div>'
        p=self.page;ed=self.note();ed.fill('')
        ed.evaluate("""(ed,html)=>{const cd=new DataTransfer();cd.setData('text/html',html);cd.setData('text/plain',html.replace(/<[^>]+>/g,''));ed.dispatchEvent(new ClipboardEvent('paste',{clipboardData:cd,bubbles:true,cancelable:true}));}""",html)
        expect(ed.locator('.nb-toggle-body')).to_be_hidden();expect(ed.locator('strong')).to_have_text('중요한 본문')
        # A previous day's journal is read-only until opened. Disclosure must not trigger editing.
        self.patch('notes','work-month',{'log':True,'mon':'2026-10','space':'work','html':'<div class="h2 dayh">10/14 (수)</div><div>다른 날 기록</div><div class="h2 dayh">10/15 (목)</div>'+html})
        p.locator('nav [data-tab="rec"]').click();p.locator('[data-archive-filter="log"]').click()
        p.locator('[data-archive-open="log"][data-id="2026-10-14"]').click()
        title=p.locator('.rt:not([contenteditable]) .nb-toggle-title').first
        expect(title).to_have_attribute('aria-expanded','false');title.focus();p.keyboard.press('Enter')
        expect(title).to_have_attribute('aria-expanded','true')
        expect(p.locator('.rt:not([contenteditable]) .nb-toggle-body').first).to_be_visible()

    def test_mobile_document_uses_width_and_slash_menu_survives_caret_scrolling(self):
        p=self.page;p.set_viewport_size({'width':390,'height':700})
        self.patch('notes','work-n',{'html':''.join('<div>길게 기록한 문단 '+str(i)+'</div>' for i in range(25))+'<div><br></div>'})
        ed=self.note();self.assertGreater(p.locator('article.doc').bounding_box()['width'],340)
        ed.locator(':scope > div').last.click();p.keyboard.press('/')
        expect(p.locator('.nb-menu')).to_be_visible()
        p.evaluate('scrollBy(0,-30)');expect(p.locator('.nb-menu')).to_be_visible()
        p.locator('.nb-menu').evaluate('m=>m.scrollTop=120');expect(p.locator('.nb-menu')).to_be_visible()
        self.choose('토글');expect(ed.locator('.nb-toggle-title')).to_be_visible()

    def test_unavailable_photo_is_kept_without_autosaving_a_deletion(self):
        html='<div>기존 사진을 지우지 않기</div><div class="img" data-sz="s"><img data-img="missing-photo" alt="기억할 사진"></div>'
        self.patch('notes','work-n',{'html':html});before=self.page.evaluate('JSON.stringify(__store)');ed=self.note()
        expect(ed.locator('img[data-img="missing-photo"]')).to_have_attribute('data-missing','true')
        self.page.wait_for_timeout(700);self.assertEqual(self.page.evaluate('JSON.stringify(__store)'),before)
        ed.locator(':scope > div').first.click();self.page.keyboard.press('End');self.page.keyboard.insert_text(' 보완')
        self.page.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('보완')")
        saved=self.page.evaluate("__store.notes.find(n=>n.id==='work-n').html")
        self.assertIn('data-img="missing-photo"',saved);self.assertIn('data-sz="s"',saved);self.assertNotIn('data-missing',saved)

    def test_existing_arrow_shortcuts_and_typed_links_still_save_in_new_editor(self):
        p=self.page;ed=self.note();ed.fill('');p.keyboard.type('A -> B https://example.com/guide ')
        expect(ed).to_contain_text('A → B');expect(ed.locator('a')).to_have_attribute('href','https://example.com/guide')
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('href=')")
        p.reload();ed=self.note();expect(ed).to_contain_text('A → B');expect(ed.locator('a')).to_have_text('https://example.com/guide')

    def test_plus_inserts_between_blocks_and_drag_can_nest_then_outdent(self):
        html='<div>첫 문단</div><div>두 번째 문단</div><div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">모아둘 내용</div><div class="nb-toggle-body"><div>기존 안쪽 문단</div></div></div>'
        self.patch('notes','work-n',{'html':html});p=self.page;ed=self.note()
        ed.locator(':scope > div').first.click();p.locator('[data-block-add]').click();self.choose('본문');p.keyboard.insert_text('사이에 넣은 문단')
        expect(ed.locator(':scope > div').nth(1)).to_have_text('사이에 넣은 문단')
        p.locator('[data-block-menu]').drag_to(ed.locator('.nb-toggle-body > div').first,target_position={'x':30,'y':23})
        expect(ed.locator('.nb-toggle-body > div').last).to_have_text('사이에 넣은 문단')
        p.keyboard.press('Shift+Tab');expect(ed.locator(':scope > div').last).to_have_text('사이에 넣은 문단')
        expect(ed.locator('.nb-toggle-body')).to_have_text('기존 안쪽 문단')
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('사이에 넣은 문단')")
        p.reload();ed=self.note();expect(ed.locator(':scope > div').last).to_have_text('사이에 넣은 문단')

    def test_enter_in_populated_toggle_title_creates_new_body_line_without_merging_text(self):
        html='<div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">상담 내용</div><div class="nb-toggle-body"><div><strong>기존 견적 100만원</strong></div></div></div>'
        self.patch('notes','work-n',{'html':html});p=self.page;ed=self.note()
        ed.locator('.nb-toggle-title').click();p.keyboard.press('End');p.keyboard.press('Enter');p.keyboard.insert_text('새로 확인할 내용')
        expect(ed.locator('.nb-toggle-body > div')).to_have_text(['새로 확인할 내용','기존 견적 100만원'])
        expect(ed.locator('.nb-toggle-body strong')).to_have_text('기존 견적 100만원')

    def test_toggle_disclosure_does_not_focus_editor_or_move_another_paragraph_caret(self):
        html='<div class="nb-toggle" data-expanded="false"><div class="nb-toggle-title">확인만 할 제목</div><div class="nb-toggle-body"><div>보존할 본문</div></div></div><div>계속 작성할 문단</div>'
        self.patch('notes','work-n',{'html':html});p=self.page;ed=self.note()
        p.locator('.dt').focus();ed.locator('.nb-toggle-arrow').click()
        expect(p.locator('.dt')).to_be_focused();expect(ed.locator('.nb-toggle-body')).to_be_visible()
        ed.locator(':scope > div').last.click();p.keyboard.press('End');ed.locator('.nb-toggle-arrow').click();p.keyboard.insert_text(' 이어서')
        expect(ed.locator(':scope > div').last).to_have_text('계속 작성할 문단 이어서')
        expect(ed.locator('.nb-toggle-title')).to_have_text('확인만 할 제목')

    def test_nested_legacy_toggles_remain_independent_without_writing_on_open(self):
        html='<div class="tgl open">큰 제목</div><div class="tgc"><div class="tgl open">작은 제목</div><div class="tgc"><strong>오래된 내용</strong></div></div>'
        self.patch('notes','work-n',{'html':html});before=self.page.evaluate('JSON.stringify(__store)');ed=self.note()
        expect(ed.locator('.nb-toggle .nb-toggle')).to_have_count(1)
        expect(ed.locator('.nb-toggle-body strong')).to_have_text('오래된 내용')
        self.assertEqual(self.page.evaluate('JSON.stringify(__store)'),before)

    def test_enter_in_middle_of_title_moves_formatted_tail_into_its_own_body_line(self):
        html='<div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">제목<strong>옮길 내용</strong></div><div class="nb-toggle-body"><div>기존 본문</div></div></div>'
        self.patch('notes','work-n',{'html':html});p=self.page;ed=self.note()
        title=ed.locator('.nb-toggle-title');title.click();p.keyboard.press('Home');p.keyboard.press('ArrowRight');p.keyboard.press('ArrowRight');p.keyboard.press('Enter')
        expect(title).to_have_text('제목');expect(ed.locator('.nb-toggle-body > div')).to_have_text(['옮길 내용','기존 본문'])
        expect(ed.locator('.nb-toggle-body strong')).to_have_text('옮길 내용')
        p.keyboard.press('Control+z');expect(title).to_have_text('제목옮길 내용');expect(ed.locator('.nb-toggle-body')).to_have_text('기존 본문')


class AndroidBlockEditorTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown = ui.ArchiveTests.tearDown
    search = ui.ArchiveTests.search
    note = BlockEditorTests.note
    choose = BlockEditorTests.choose

    def setUp(self):
        # Uses Android browser detection plus real Chromium editing events; no physical IME claim.
        original=self.browser.new_context
        self.browser.new_context=lambda **kw:original(user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',has_touch=True,is_mobile=True,viewport={'width':390,'height':844},**kw)
        try: ui.ArchiveTests.setUp(self)
        finally:self.browser.new_context=original

    def test_title_enter_and_body_enter_do_not_create_accidental_nested_toggles(self):
        p=self.page;ed=self.note();ed.fill('');p.keyboard.type('> ');p.keyboard.insert_text('휴대폰 제목');p.keyboard.press('Enter');p.keyboard.insert_text('첫 번째 본문')
        expect(ed.locator('.nb-toggle')).to_have_count(1)
        expect(ed.locator('.nb-toggle-body > div')).to_have_text(['첫 번째 본문'])
        p.keyboard.press('Enter');p.keyboard.insert_text('두 번째 본문')
        expect(ed.locator('.nb-toggle-body > div')).to_have_text(['첫 번째 본문','두 번째 본문'])
        p.keyboard.press('Enter');p.keyboard.press('Enter');p.keyboard.insert_text('토글 밖의 글')
        expect(ed.locator(':scope > div').last).to_have_text('토글 밖의 글')

    def test_explicit_paragraph_intent_after_composition_keeps_one_toggle_and_korean_text(self):
        p=self.page;ed=self.note();ed.fill('');p.keyboard.type('> ');p.keyboard.insert_text('한글 제목')
        ed.evaluate("""ed=>{ed.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));ed.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:229,isComposing:true,bubbles:true}));ed.dispatchEvent(new InputEvent('beforeinput',{inputType:'insertCompositionText',data:'목',isComposing:true,cancelable:true,bubbles:true}));ed.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'목'}));ed.dispatchEvent(new InputEvent('beforeinput',{inputType:'insertParagraph',isComposing:false,cancelable:true,bubbles:true}));}""")
        p.keyboard.insert_text('이어 쓰는 한글 본문')
        expect(ed.locator('.nb-toggle')).to_have_count(1);expect(ed.locator('.nb-toggle-title')).to_have_text('한글 제목')
        expect(ed.locator('.nb-toggle-body > div')).to_have_text(['이어 쓰는 한글 본문'])
        p.keyboard.press('Control+End');ed.locator('.nb-toggle-body > div').last.tap();p.locator('[data-block-menu]').tap()
        self.choose('아래에 문단 추가');p.keyboard.insert_text('메뉴로 더한 문단')
        expect(ed.locator('.nb-toggle-body > div').last).to_have_text('메뉴로 더한 문단')

    def test_slash_menu_remains_usable_when_android_keyboard_resizes_viewport(self):
        p=self.page;ed=self.note();ed.fill('');p.keyboard.press('/');expect(p.locator('.nb-menu')).to_be_visible()
        p.set_viewport_size({'width':390,'height':480});expect(p.locator('.nb-menu')).to_be_visible()
        p.wait_for_function("(()=>{const r=document.querySelector('.nb-menu')?.getBoundingClientRect();return r&&r.top>=0&&r.bottom<=innerHeight})()")
        box=p.locator('.nb-menu').bounding_box();self.assertGreaterEqual(box['y'],0);self.assertLessEqual(box['y']+box['height'],480)
        self.choose('토글');p.keyboard.insert_text('키보드가 떠 있어도 작성');p.keyboard.press('Enter');p.keyboard.insert_text('본문')
        expect(ed.locator('.nb-toggle-title')).to_have_text('키보드가 떠 있어도 작성');expect(ed.locator('.nb-toggle-body')).to_have_text('본문')

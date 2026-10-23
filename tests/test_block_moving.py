"""Use actual pointer paths, including the gutter and browser touch events."""
import unittest
import re
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors


class BlockMovingTests(unittest.TestCase):
    setUpClass = classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass = classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp = ui.ArchiveTests.setUp
    tearDown = ui.ArchiveTests.tearDown
    search = ui.ArchiveTests.search
    note = editors.BlockEditorTests.note
    patch = editors.BlockEditorTests.patch
    choose = editors.BlockEditorTests.choose

    def seed(self, html='<div>첫 문단</div><div>두 번째 문단</div><div>세 번째 문단</div>'):
        self.patch('notes','work-n',{'html':html})
        return self.note()

    def move(self, handle, x, y, pause=160):
        p=self.page;b=handle.bounding_box();p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down()
        p.wait_for_timeout(pause);p.mouse.move(x,y,steps=16);p.mouse.up()

    def test_mouse_can_move_from_the_gutter_with_a_pause_before_dragging(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').last.click()
        handle=p.locator('[data-block-menu]');expect(handle).to_be_visible();b=handle.bounding_box();first=ed.locator(':scope > div').first.bounding_box()
        self.move(handle,b['x']+b['width']/2,first['y']+2)
        expect(ed.locator(':scope > div')).to_have_text(['세 번째 문단','첫 문단','두 번째 문단'])
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div')).to_have_text(['첫 문단','두 번째 문단','세 번째 문단'])

    def test_hover_can_select_another_block_without_moving_the_text_caret(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').first.click();p.keyboard.press('End')
        ed.locator(':scope > div').last.hover();handle=p.locator('[data-block-menu]');expect(handle).to_be_visible()
        first=ed.locator(':scope > div').first.bounding_box();b=handle.bounding_box()
        self.assertGreater(b['y'],first['y']+25)
        self.move(handle,b['x']+b['width']/2,first['y']+2)
        expect(ed.locator(':scope > div').first).to_have_text('세 번째 문단')

    def test_drag_shows_a_destination_and_cancel_keeps_the_original_without_saving(self):
        p=self.page;ed=self.seed();ed.locator(':scope > div').last.click();before=p.evaluate('JSON.stringify(__store)')
        handle=p.locator('[data-block-menu]');expect(handle).to_be_visible();b=handle.bounding_box();first=ed.locator(':scope > div').first.bounding_box()
        p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(b['x']+b['width']/2,first['y']+1,steps=12)
        expect(p.locator('.nb-drop-indicator')).to_be_visible();p.keyboard.press('Escape');p.mouse.up()
        expect(p.locator('.nb-drop-indicator')).to_have_count(0);expect(ed.locator(':scope > div')).to_have_text(['첫 문단','두 번째 문단','세 번째 문단'])
        self.assertEqual(p.evaluate('JSON.stringify(__store)'),before)

    def test_hover_without_click_or_focus_shows_controls_without_saving(self):
        p=self.page;ed=self.seed();p.locator('[data-dt]').focus();before=p.evaluate('JSON.stringify(__store)')
        focused=p.locator('[data-dt]')
        ed.locator(':scope > div').last.hover();expect(p.locator('[data-block-menu]')).to_be_visible()
        expect(focused).to_be_focused();self.assertEqual(p.evaluate('JSON.stringify(__store)'),before)

    def test_selected_paragraphs_move_as_a_group_and_undo_together(self):
        p=self.page;ed=self.seed('<div>첫째</div><div>둘째</div><div>셋째</div><div>넷째</div>')
        ed.evaluate("""ed=>{ed.focus();const r=document.createRange();r.setStart(ed.children[1],0);r.setEnd(ed.children[2],1);getSelection().removeAllRanges();getSelection().addRange(r)}""")
        expect(ed.locator('.nb-selected-block')).to_have_count(2)
        ed.locator(':scope > div').nth(1).hover()
        handle=p.locator('[data-block-menu]');first=ed.locator(':scope > div').first.bounding_box();b=handle.bounding_box()
        self.move(handle,b['x']+b['width']/2,first['y']+1)
        expect(ed.locator(':scope > div')).to_have_text(['둘째','셋째','첫째','넷째'])
        p.keyboard.press('Control+z');expect(ed.locator(':scope > div')).to_have_text(['첫째','둘째','셋째','넷째'])

    def test_pointer_can_put_a_paragraph_inside_a_toggle_and_lift_it_out(self):
        p=self.page;ed=self.seed('<div>맨 위</div><div class="nb-toggle" data-expanded="false"><div class="nb-toggle-title">모아둘 내용</div><div class="nb-toggle-body"><div>기존 내용</div></div></div><div>옮기는 문단</div>')
        ed.locator(':scope > div').last.hover();handle=p.locator('[data-block-menu]');title=ed.locator('.nb-toggle-title').bounding_box()
        self.move(handle,title['x']+80,title['y']+title['height']/2)
        expect(ed.locator('.nb-toggle-body')).to_be_visible();expect(ed.locator('.nb-toggle-body > div')).to_have_text(['기존 내용','옮기는 문단'])
        ed.locator('.nb-toggle-body > div').last.hover();first=ed.locator(':scope > div').first.bounding_box()
        self.move(handle,first['x']-20,first['y']+1)
        expect(ed.locator(':scope > div').first).to_have_text('옮기는 문단');expect(ed.locator('.nb-toggle-body')).to_have_text('기존 내용')

    def test_drag_autoscrolls_long_document_and_cancel_stops_without_changing_text(self):
        p=self.page;ed=self.seed(''.join('<div>문단 %s</div>'%i for i in range(60)))
        ed.locator(':scope > div').first.hover();handle=p.locator('[data-block-menu]');b=handle.bounding_box();before=ed.inner_text()
        p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down()
        p.mouse.move(b['x']+b['width']/2,p.evaluate('innerHeight-8'),steps=20)
        p.wait_for_function("document.scrollingElement.scrollTop>200")
        p.keyboard.press('Escape');p.mouse.up();expect(p.locator('.nb-drop-indicator')).to_have_count(0)
        self.assertEqual(ed.inner_text(),before)

    def test_schedule_memo_autoscrolls_its_inner_editor_and_cancels_safely(self):
        p=self.page;self.patch('todos','work-t',{'noteH':''.join('<div>일정 메모 %s</div>'%i for i in range(60))})
        self.search('보고서 제출');p.locator('#sqr [data-sgo="todo"]').click();ed=p.locator('#e-n')
        ed.locator(':scope > div').first.hover();handle=p.locator('[data-block-menu]');b=handle.bounding_box();rect=ed.bounding_box();before=ed.inner_text()
        p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(b['x']+b['width']/2,rect['y']+rect['height']-8,steps=20)
        p.wait_for_function("document.querySelector('#e-n').scrollTop>150")
        p.keyboard.press('Escape');p.mouse.up();expect(p.locator('.nb-drop-indicator')).to_have_count(0)
        self.assertEqual(ed.inner_text(),before)

    def test_nested_paragraphs_reorder_in_the_handle_gutter_in_both_directions(self):
        p=self.page;ed=self.seed('<div>바깥</div><div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">큰 토글</div><div class="nb-toggle-body"><div>안쪽 첫째</div><div>안쪽 둘째</div><div>안쪽 셋째</div></div></div>')
        rows=ed.locator('.nb-toggle-body > div');rows.last.hover();handle=p.locator('[data-block-menu]');b=handle.bounding_box();first=rows.first.bounding_box()
        p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2,steps=24);p.mouse.down();p.mouse.move(b['x']+b['width']/2,first['y']-1,steps=24)
        expect(p.locator('.nb-drop-indicator')).to_be_visible();p.mouse.up()
        expect(rows).to_have_text(['안쪽 셋째','안쪽 첫째','안쪽 둘째']);expect(ed.locator(':scope > div')).to_have_count(2)
        rows.first.hover();b=handle.bounding_box();last=rows.last.bounding_box();self.move(handle,b['x']+b['width']/2,last['y']+last['height']+1)
        expect(rows).to_have_text(['안쪽 첫째','안쪽 둘째','안쪽 셋째'])
        p.keyboard.press('Control+z');expect(rows).to_have_text(['안쪽 셋째','안쪽 첫째','안쪽 둘째'])
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.indexOf('안쪽 셋째')<__store.notes.find(n=>n.id==='work-n').html.indexOf('안쪽 첫째')")
        p.reload();ed=self.note();expect(ed.locator('.nb-toggle-body > div')).to_have_text(['안쪽 셋째','안쪽 첫째','안쪽 둘째'])

    def test_root_paragraph_can_move_down_in_home_reminder_and_survive_reload(self):
        p=self.page;self.patch('logs','memo_work',{'html':'<div>맨 위</div><div>가운데</div><div>맨 아래</div>'})
        p.locator('nav [data-tab="home"]').click();ui.reveal(p,'[data-memo]');ed=p.locator('[data-memo]');rows=ed.locator(':scope > div')
        rows.first.hover();handle=p.locator('[data-block-menu]');b=handle.bounding_box();last=rows.last.bounding_box();self.move(handle,b['x']+b['width']/2,last['y']+last['height']-1)
        expect(rows).to_have_text(['가운데','맨 아래','맨 위'])
        p.wait_for_function("__store.logs.find(n=>n.id==='memo_work').html.startsWith('<div>가운데</div>')")
        p.reload();ui.reveal(p,'[data-memo]');expect(p.locator('[data-memo] > div')).to_have_text(['가운데','맨 아래','맨 위'])

    def test_project_memo_controls_stay_available_after_hover_scroll_and_reorder(self):
        p=self.page;self.patch('projects','work-p',{'memoH':'<div>첫 메모</div><div>둘째 메모</div><div>셋째 메모</div>'})
        p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="work-p"]').click();ui.project_details(p)
        ed=p.locator('[data-pmemo]');ed.locator(':scope > div').last.hover()
        # Scroll events queued by bringing the hovered block into view must not
        # remove controls for an unfocused editor.
        p.evaluate("window.dispatchEvent(new Event('scroll'))")
        handle=p.locator('[data-block-menu]');expect(handle).to_be_visible();handle.click();self.choose('위로 이동')
        expect(ed.locator(':scope > div')).to_have_text(['첫 메모','셋째 메모','둘째 메모'])
        p.keyboard.press('Alt+ArrowUp');expect(ed.locator(':scope > div')).to_have_text(['셋째 메모','첫 메모','둘째 메모'])
        p.wait_for_function("__store.projects.find(n=>n.id==='work-p').memoH.startsWith('<div>셋째 메모</div>')")
        p.reload();p.locator('[data-open="work-p"]').click();ui.project_details(p)
        expect(p.locator('[data-pmemo] > div')).to_have_text(['셋째 메모','첫 메모','둘째 메모'])


class TouchBlockMovingTests(BlockMovingTests):
    def setUp(self):
        original=self.browser.new_context
        self.browser.new_context=lambda **kw:original(user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',has_touch=True,is_mobile=True,viewport={'width':390,'height':844},**kw)
        try:ui.ArchiveTests.setUp(self)
        finally:self.browser.new_context=original

    # Desktop-specific mouse coverage remains in BlockMovingTests.
    test_mouse_can_move_from_the_gutter_with_a_pause_before_dragging = None
    test_hover_can_select_another_block_without_moving_the_text_caret = None
    test_drag_shows_a_destination_and_cancel_keeps_the_original_without_saving = None

    test_hover_without_click_or_focus_shows_controls_without_saving = None
    test_selected_paragraphs_move_as_a_group_and_undo_together = None
    test_pointer_can_put_a_paragraph_inside_a_toggle_and_lift_it_out = None
    test_drag_autoscrolls_long_document_and_cancel_stops_without_changing_text = None

    test_schedule_memo_autoscrolls_its_inner_editor_and_cancels_safely = None

    test_nested_paragraphs_reorder_in_the_handle_gutter_in_both_directions = None
    test_root_paragraph_can_move_down_in_home_reminder_and_survive_reload = None

    test_project_memo_controls_stay_available_after_hover_scroll_and_reorder = None

    def test_browser_touch_drag_reorders_whole_toggle_and_survives_reload(self):
        p=self.page;ed=self.seed('<div>첫 문단</div><div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">옮길 토글</div><div class="nb-toggle-body"><div>토글 안의 내용</div></div></div><div>마지막 문단</div>')
        p.evaluate("""()=>{window.__moveEvents=[];for(const type of ['pointerdown','pointerup','pointercancel','lostpointercapture'])document.addEventListener(type,e=>__moveEvents.push({type,target:e.target.outerHTML?.slice(0,180),x:e.clientX,y:e.clientY}),true)}""")
        ed.locator('.nb-toggle-title').tap();handle=p.locator('[data-block-menu]');expect(handle).to_be_visible();b=handle.bounding_box();first=ed.locator(':scope > div').first.bounding_box()
        cdp=self.context.new_cdp_session(p);x=b['x']+b['width']/2;y=b['y']+b['height']/2
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        p.wait_for_timeout(160)
        for step in range(1,13):cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y+(first['y']+1-y)*step/12}]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        if not ed.locator(':scope > div').first.evaluate("el=>el.classList.contains('nb-toggle')"):
            print('Touch move diagnostics:',p.evaluate('window.__moveEvents'), 'html:',ed.inner_html(),flush=True)
        expect(ed.locator(':scope > div').first).to_have_class(re.compile(r'\bnb-toggle\b'));expect(ed.locator('.nb-toggle-body')).to_have_text('토글 안의 내용')
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.startsWith('<div class=\"nb-toggle\"')")
        p.reload();ed=self.note();expect(ed.locator(':scope > div').first).to_have_class('nb-toggle');expect(ed.locator('.nb-toggle-body')).to_have_text('토글 안의 내용')

    def test_browser_touch_can_reorder_nested_paragraphs_from_the_gutter(self):
        p=self.page;ed=self.seed('<div class="nb-toggle" data-expanded="true"><div class="nb-toggle-title">토글</div><div class="nb-toggle-body"><div>첫째</div><div>둘째</div><div>셋째</div></div></div>')
        rows=ed.locator('.nb-toggle-body > div');rows.last.tap();handle=p.locator('[data-block-menu]');b=handle.bounding_box();first=rows.first.bounding_box()
        cdp=self.context.new_cdp_session(p);x=b['x']+b['width']/2;y=b['y']+b['height']/2
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        for step in range(1,17):cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y+(first['y']+1-y)*step/16}]})
        expect(p.locator('.nb-drop-indicator')).to_be_visible();cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        expect(rows).to_have_text(['셋째','첫째','둘째']);expect(ed.locator(':scope > div')).to_have_count(1)
        p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.indexOf('셋째')<__store.notes.find(n=>n.id==='work-n').html.indexOf('첫째')")
        p.reload();ed=self.note();expect(ed.locator('.nb-toggle-body > div')).to_have_text(['셋째','첫째','둘째'])

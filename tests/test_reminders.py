"""Actual browser timers, permissions, cross-tab deduplication and original editors."""
import datetime
import unittest
from playwright.sync_api import expect
import test_archive as ui

NOTIFICATIONS="""
window.__notifications=[];window.__permission='default';window.__permissionAnswer='granted';window.__permissionRequests=0;
class FakeNotification {
 static get permission(){return window.__permission;}
 static async requestPermission(){window.__permissionRequests++;return window.__permission=window.__permissionAnswer;}
 constructor(title,options){this.title=title;this.options=options;window.__notifications.push(this);}
 close(){this.closed=true;}
}
window.Notification=FakeNotification;
"""


class ReminderTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    tearDown=ui.ArchiveTests.tearDown

    def setUp(self):
        ui.ArchiveTests.setUp(self)
        self.context.add_init_script(NOTIFICATIONS)
        self.page.clock.install(time=datetime.datetime(2026,10,22,4,59,50,tzinfo=datetime.timezone.utc))
        self.page.reload();expect(self.page.locator('.archive')).to_be_visible()

    def patch(self, ident, fields):
        self.page.evaluate("""async ([id,data])=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.setDoc(f.doc(f.collection({},'todos'),id),data,{merge:true});}""",[ident,fields])

    def event(self, ident='alarm', **fields):
        self.patch(ident,dict(title='곧 시작할 회의',date='2026-10-22',time='14:15',kind='event',space='work',done=False,**fields))

    def settings(self):
        self.page.locator('[data-menu]').click();self.page.locator('[data-reminders-open]').click()
        expect(self.page.locator('#reminder-status')).to_be_visible()

    def enable(self):
        self.settings();self.page.locator('[data-reminder-on]').click()
        expect(self.page.locator('#reminder-status')).to_contain_text('받고 있어요')
        self.page.locator('#sheet [data-sx="0"]').click()

    def test_default_fifteen_minute_notification_opens_original_and_does_not_repeat(self):
        self.event();self.enable()
        self.assertEqual(self.page.evaluate('window.__permissionRequests'),1)
        self.page.clock.fast_forward(15000)
        self.page.wait_for_function('window.__notifications.length===1')
        alarm=self.page.evaluate('({title:__notifications[0].title,body:__notifications[0].options.body})')
        self.assertEqual(alarm['title'],'곧 시작할 회의');self.assertIn('14:15',alarm['body'])
        self.page.evaluate('__notifications[0].onclick()')
        expect(self.page.locator('#e-t')).to_have_value('곧 시작할 회의')
        expect(self.page.locator('.mc.sel')).to_have_attribute('data-pick','2026-10-22')
        self.page.clock.fast_forward(60000)
        self.assertEqual(self.page.evaluate('window.__notifications.length'),1)

    def test_no_permission_prompt_on_load_and_denial_gives_next_step(self):
        self.event();self.page.clock.fast_forward(15000)
        self.assertEqual(self.page.evaluate('window.__permissionRequests'),0)
        self.assertEqual(self.page.evaluate('window.__notifications.length'),0)
        self.page.evaluate("window.__permissionAnswer='denied'")
        self.settings();self.page.locator('[data-reminder-on]').click()
        expect(self.page.locator('#reminder-status')).to_contain_text('사이트 설정')
        self.page.locator('[data-reminder-on]').click()
        self.assertEqual(self.page.evaluate('window.__permissionRequests'),1)

    def test_completed_deleted_and_disabled_events_do_not_alert(self):
        self.event('completed');self.event('deleted');self.event('muted',reminder='off');self.enable()
        self.patch('completed',{'done':True})
        self.page.evaluate("async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.deleteDoc(f.doc(f.collection({},'todos'),'deleted'));}")
        self.page.clock.fast_forward(15000)
        self.assertEqual(self.page.evaluate('window.__notifications.length'),0)

    def test_moved_event_waits_for_new_time_and_visible_alert_closes_on_completion(self):
        self.event();self.enable();self.patch('alarm',{'time':'14:30'})
        self.page.clock.fast_forward(15000);self.assertEqual(self.page.evaluate('window.__notifications.length'),0)
        self.page.clock.fast_forward(15*60000);self.page.wait_for_function('window.__notifications.length===1')
        self.patch('alarm',{'done':True});self.page.wait_for_function('__notifications[0].closed===true')

    def test_two_open_tabs_display_one_notification_for_same_occurrence(self):
        self.event();self.enable()
        other=self.context.new_page();other.clock.install(time=datetime.datetime(2026,10,22,4,59,50,tzinfo=datetime.timezone.utc));other.goto(self.origin)
        expect(other.locator('#app')).to_be_visible()
        self.page.clock.fast_forward(15000);self.page.wait_for_function('window.__notifications.length===1')
        other.clock.fast_forward(15000)
        self.assertEqual(other.evaluate('window.__notifications.length'),0);other.close()

    def test_schedule_reminder_choice_persists_and_draft_is_restored(self):
        self.event();self.page.locator('[data-archive-filter="todo"]').click()
        self.page.locator('[data-archive-open="todo"][data-id="alarm"]').click()
        ui.reveal(self.page,'#e-reminder')
        self.page.locator('#e-reminder').select_option('30');self.page.locator('#e-reminder').dispatch_event('input')
        self.page.locator('#sheet [data-sx="0"]').click()
        self.page.locator('[data-archive-open="todo"][data-id="alarm"]').click()
        expect(self.page.locator('#e-reminder')).to_have_value('30')
        self.page.locator('[data-esave]').click()
        self.page.wait_for_function("__store.todos.find(t=>t.id==='alarm').reminder==='30'")
        self.page.reload();self.page.locator('[data-archive-filter="todo"]').click()
        self.page.locator('[data-archive-open="todo"][data-id="alarm"]').click()
        expect(self.page.locator('#e-reminder')).to_have_value('30')
        self.page.locator('#e-d').fill('');self.page.locator('#e-d').dispatch_event('input')
        expect(self.page.locator('#e-reminder')).to_be_disabled()

    def test_all_day_date_only_tasks_and_invalid_values_have_expected_times(self):
        result=self.page.evaluate("""async()=>{const {reminderAt}=await import('./reminders-ui.js');const base={date:'2026-10-22',kind:'event'};return [reminderAt(base),reminderAt({...base,kind:'todo'}),reminderAt({...base,done:true}),reminderAt({...base,date:'2026-02-30'}),reminderAt({...base,time:'00:05'}),reminderAt({...base,time:'14:00',reminder:'off'})]}""")
        zone=datetime.timezone(datetime.timedelta(hours=9))
        self.assertEqual(result[0],int(datetime.datetime(2026,10,22,9,tzinfo=zone).timestamp()*1000))
        self.assertEqual(result[1:4],[0,0,0]);self.assertEqual(result[5],0)
        self.assertEqual(result[4],int(datetime.datetime(2026,10,21,23,50,tzinfo=zone).timestamp()*1000))

    def test_turning_off_pc_alerts_does_not_change_calendar_data(self):
        self.event();before=self.page.evaluate('JSON.stringify(__store)');self.enable()
        self.settings();self.page.locator('[data-reminder-off]').click()
        self.page.clock.fast_forward(15000);self.assertEqual(self.page.evaluate('window.__notifications.length'),0)
        self.assertEqual(self.page.evaluate('JSON.stringify(__store)'),before)

    def test_all_day_event_alerts_at_nine_and_ordinary_task_does_not(self):
        self.page.clock.set_system_time(datetime.datetime(2026,10,21,23,59,50,tzinfo=datetime.timezone.utc))
        self.page.reload();expect(self.page.locator('.archive')).to_be_visible()
        self.patch('morning-event',{'title':'시간 없는 일정','date':'2026-10-22','kind':'event','space':'life','done':False})
        self.patch('morning-task',{'title':'날짜만 정한 할 일','date':'2026-10-22','space':'work','done':False})
        self.enable();self.page.clock.fast_forward(15000)
        self.page.wait_for_function('window.__notifications.length===1')
        self.assertEqual(self.page.evaluate('__notifications[0].title'),'시간 없는 일정')
        self.assertIn('LIFE',self.page.evaluate('__notifications[0].options.body'))

    def test_preview_never_requests_real_permissions_or_changes_actual_settings(self):
        self.page.evaluate("localStorage.setItem('notification-sentinel','untouched')")
        before=self.page.evaluate('JSON.stringify({...localStorage})')
        self.page.goto(self.origin+'/preview.html')
        expect(self.page.locator('.preview-note')).to_be_visible()
        self.page.locator('[data-menu]').click();self.page.locator('[data-reminders-open]').click()
        expect(self.page.locator('#sheet')).to_contain_text('미리보기에서는 알림 권한을 요청하거나 예약하지 않아요')
        self.page.clock.fast_forward(30000)
        self.assertEqual(self.page.evaluate('__permissionRequests'),0)
        self.assertEqual(self.page.evaluate('JSON.stringify({...localStorage})'),before)

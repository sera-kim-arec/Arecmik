"""Real UI writes with remote changes, transaction retries and interrupted saves.
All Firebase operations use the test adapter, never the user's account.
"""
import json
import unittest
from playwright.sync_api import expect
import test_archive as ui
import test_block_editor as editors
import test_journal_editing_integrity as journals


class SaveSafetyTests(unittest.TestCase):
    setUpClass=classmethod(ui.ArchiveTests.setUpClass.__func__)
    tearDownClass=classmethod(ui.ArchiveTests.tearDownClass.__func__)
    setUp=ui.ArchiveTests.setUp
    tearDown=ui.ArchiveTests.tearDown
    search=ui.ArchiveTests.search
    patch=editors.BlockEditorTests.patch
    note=editors.BlockEditorTests.note
    seed=journals.JournalEditingIntegrityTests.seed

    def stored(self,c,id):
        return self.page.evaluate('([c,id])=>__store[c].find(x=>x.id===id)',[c,id])

    def drafts(self):
        return self.page.evaluate("JSON.parse(localStorage.getItem('arecmik:edits:ui-test')||'{}')")

    def wait_saved(self):
        self.page.wait_for_function("Object.keys(JSON.parse(localStorage.getItem('arecmik:edits:ui-test')||'{}')).length===0")

    def wait_conflict(self):
        expect(self.page.locator('#save-status')).to_contain_text('다른 기기의 수정과 겹쳐')
        self.assertTrue(any(d['state']=='conflict' for d in self.drafts().values()))

    def test_remote_body_is_preserved_and_both_contents_are_visible(self):
        p=self.page;ed=self.note();ed.fill('PC에서 작성한 내용')
        self.patch('notes','work-n',{'html':'<div>휴대폰에서 작성한 내용</div>'})
        self.wait_conflict();self.assertIn('휴대폰에서',self.stored('notes','work-n')['html']);expect(ed).to_contain_text('PC에서')
        p.locator('#save-status [data-local-recovery]').click();expect(p.locator('.recovery-item')).to_contain_text('PC에서 작성한 내용');expect(p.locator('.recovery-item')).to_contain_text('휴대폰에서 작성한 내용')
        p.locator('[data-recover-edit]').click();expect(p.locator('[data-db]')).to_contain_text('PC에서 작성한 내용');self.assertIn('휴대폰에서',self.stored('notes','work-n')['html']);self.wait_saved()

    def test_base_is_captured_before_first_keystroke(self):
        ed=self.note();ed.focus();self.patch('notes','work-n',{'html':'<div>먼저 도착한 휴대폰 수정</div>'});ed.fill('아직 예전 화면에서 적은 글');self.wait_conflict();self.assertIn('먼저 도착한',self.stored('notes','work-n')['html'])

    def test_unrelated_remote_fields_are_preserved(self):
        ed=self.note();ed.fill('본문만 수정');self.patch('notes','work-n',{'title':'휴대폰에서 바꾼 제목','fav':True,'pid':'work-p'});self.wait_saved();n=self.stored('notes','work-n');self.assertEqual(n['title'],'휴대폰에서 바꾼 제목');self.assertTrue(n['fav']);self.assertEqual(n['pid'],'work-p');self.assertIn('본문만 수정',n['html'])

    def test_remote_change_after_transaction_read_is_checked_again(self):
        p=self.page;ed=self.note();p.evaluate('window.__writeDelayMs=450');ed.fill('PC 전송 중 편집');p.locator('nav [data-tab="home"]').click()
        # This bypasses the adapter's delayed write on purpose: another client
        # commits after this transaction's read and before its commit.
        p.evaluate("__store.notes.find(n=>n.id==='work-n').html='<div>전송 중 도착한 다른 기기 수정</div>'")
        self.wait_conflict();self.assertIn('다른 기기 수정',self.stored('notes','work-n')['html'])

    def test_explicit_conflict_choice_checks_the_displayed_server_again(self):
        p=self.page;ed=self.note();ed.fill('내가 고른 내용');self.patch('notes','work-n',{'html':'<div>첫 서버 수정</div>'});self.wait_conflict();p.locator('#save-status [data-local-recovery]').click()
        self.patch('notes','work-n',{'html':'<div>비교 화면 뒤에 도착한 새 수정</div>'});p.locator('[data-use-edit]').click();self.wait_conflict();self.assertIn('비교 화면 뒤에',self.stored('notes','work-n')['html'])
        p.locator('#sheet [data-sx]').click();p.locator('#save-status [data-local-recovery]').click();p.locator('[data-use-edit]').click();self.wait_saved();self.assertIn('내가 고른 내용',self.stored('notes','work-n')['html'])

    def test_online_retries_failed_save_without_typing(self):
        p=self.page;ed=self.note();p.evaluate("window.__failWrites=true;window.__writeErrorCode='unavailable'");ed.fill('연결 회복 후 저장할 내용');expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집');expect(p.locator('[data-retry-edits]')).to_be_visible()
        p.evaluate("window.__failWrites=false;window.dispatchEvent(new Event('online'));window.dispatchEvent(new Event('online'))");self.wait_saved();self.assertIn('연결 회복 후',self.stored('notes','work-n')['html'])
        self.assertEqual(p.evaluate("(__writes||[]).filter(w=>w.collection==='notes'&&w.id==='work-n').length"),1)

    def test_manual_retry_keeps_an_intentional_empty_body(self):
        p=self.page;ed=self.note();p.evaluate('window.__failWrites=true');ed.fill('');expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집');p.evaluate('window.__failWrites=false');p.locator('[data-retry-edits]').click();self.wait_saved();self.assertNotIn('중요한 결정',self.stored('notes','work-n')['html'])

    def test_retry_detects_a_new_remote_edit(self):
        p=self.page;ed=self.note();p.evaluate("window.__failWrites=true;window.__writeErrorCode='unavailable'");ed.fill('끊겼을 때 내 편집');expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집');p.evaluate('window.__failWrites=false');self.patch('notes','work-n',{'html':'<div>그 사이 다른 기기 편집</div>'});p.evaluate("window.dispatchEvent(new Event('online'))");self.wait_conflict();self.assertIn('그 사이',self.stored('notes','work-n')['html'])

    def test_newer_input_during_save_is_sent_without_false_conflict(self):
        p=self.page;ed=self.note();p.evaluate('window.__writeDelayMs=400');ed.fill('첫 편집');p.wait_for_timeout(650);ed.fill('첫 편집 다음에 이어 쓴 최종 내용');self.wait_saved();self.assertIn('최종 내용',self.stored('notes','work-n')['html']);expect(p.locator('#save-status')).to_contain_text('서버에 저장됨')

    def test_reload_retains_original_base_for_retry(self):
        p=self.page;ed=self.note();p.evaluate('window.__failWrites=true');ed.fill('다시 열어도 남을 내 편집');expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집');p.reload();ed=self.note();expect(ed).to_contain_text('다시 열어도');self.patch('notes','work-n',{'html':'<div>다시 열기 전후 서버 편집</div>'});p.locator('[data-retry-edits]').click();self.wait_conflict();self.assertIn('서버 편집',self.stored('notes','work-n')['html'])

    def test_legacy_draft_without_base_cannot_silently_overwrite(self):
        p=self.page;p.evaluate("localStorage.setItem('arecmik:edits:ui-test',JSON.stringify({'notes:work-n':{key:'notes:work-n',uid:'ui-test',c:'notes',id:'work-n',patch:{html:'<div>옛 임시 내용</div>'},space:'work',version:'old'}}))");p.reload();ed=self.note();expect(ed).to_contain_text('옛 임시 내용');p.locator('[data-retry-edits]').click();self.wait_conflict();self.assertEqual(self.stored('notes','work-n')['html'],'<div>중요한 결정</div>')

    def test_deleted_original_is_not_recreated_by_retry(self):
        p=self.page;ed=self.note();ed.fill('삭제된 글에서 이어쓴 내용');p.evaluate("async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.deleteDoc(f.doc(f.collection({},'notes'),'work-n'))}");self.wait_conflict();self.assertIsNone(self.stored('notes','work-n'));p.locator('#save-status [data-local-recovery]').click();expect(p.locator('[data-use-edit]')).to_have_count(0);expect(p.locator('[data-recover-edit]')).to_be_visible()

    def test_journal_other_day_is_merged_from_fresh_server(self):
        ed=self.seed();ed.fill('첫 날 PC 편집');self.patch('notes','month-a',{'html':'<div class="h2 dayh">10/15 (목)</div><div>첫 날 원문</div><div class="h2 dayh">10/16 (금)</div><div>둘째 날 휴대폰 편집</div>'});self.wait_saved();h=self.stored('notes','month-a')['html'];self.assertIn('첫 날 PC 편집',h);self.assertIn('둘째 날 휴대폰 편집',h)

    def test_journal_same_day_conflict_is_atomic_across_copies(self):
        ed=self.seed(True);ed.fill('첫 날 PC 편집');self.patch('notes','month-b',{'html':'<div class="h2 dayh">10/15 (목)</div><div>휴대폰에서 같은 날 편집</div>'});self.wait_conflict();self.assertIn('첫 날 원문',self.stored('notes','month-a')['html']);self.assertIn('옛 날짜 원문',self.stored('notes','legacy-day')['html']);self.assertIn('휴대폰에서',self.stored('notes','month-b')['html'])

    def test_new_month_uses_same_id_and_preserves_another_new_day(self):
        p=self.page;p.locator('nav [data-tab="home"]').click();ui.reveal(p,'[data-log]');ed=p.locator('[data-log]').first;k=ed.get_attribute('data-log');other=k[:-2]+'01';ed.fill('오늘 처음 쓴 일지');self.patch('notes','journal-work-'+k[:7],{'space':'work','log':True,'mon':k[:7],'html':'<div class="h2 dayh">'+str(int(other[5:7]))+'/1 (목)</div><div>다른 기기가 먼저 만든 월 일지</div>'});self.wait_saved();h=self.stored('notes','journal-work-'+k[:7])['html'];self.assertIn('오늘 처음 쓴',h);self.assertIn('다른 기기가 먼저',h);self.assertEqual(len([n for n in p.evaluate('__store.notes') if n.get('mon')==k[:7] and n.get('space')=='work']),1)

    def open_form(self,c):
        query,kind,selector={'todos':('보고서 제출','todo','#e-n'),'moms':('업무 회의 회고','mom','#record-body'),'refs':('업무 자료','ref','#r-b'),'exps':('숙박 결제','expense','#x-m')}[c]
        if c=='moms':query=self.page.evaluate("()=>{const m=__store.moms.find(m=>m.id==='work-m');const el=document.createElement('div');el.innerHTML=m.h||'';return (el.textContent||m.t).trim().split('\\n')[0]}")
        if c=='exps':p=self.page;p.locator('[data-sp="life"]').click()
        self.search(query);self.page.locator('#sqr [data-sgo="'+kind+'"]').click();return self.page.locator(selector)

    def test_all_explicit_forms_protect_conflicts(self):
        for c,id,field,save in [('todos','work-t','noteH','esave'),('moms','work-m','h','record-save'),('refs','work-r','html','rsave'),('exps','life-e','memoH','xsave')]:
            with self.subTest(collection=c):
                p=self.page;ed=self.open_form(c);ed.fill('PC 양식 편집 '+c);self.patch(c,id,{field:'<div>휴대폰 양식 편집 '+c+'</div>'});p.locator('[data-'+save+']').click();expect(p.locator('.save-conflict')).to_be_visible();expect(ed).to_contain_text('PC 양식');self.assertIn('휴대폰 양식',self.stored(c,id)[field]);p.locator('#sheet [data-sx="0"]').click()
                if p.locator('#srch.on').count():p.keyboard.press('Escape')
                if c=='exps':p.locator('[data-sp="work"]').click()

    def test_form_only_updates_fields_the_user_changed(self):
        p=self.page;self.open_form('todos').fill('본문만 바꾼 할 일');self.patch('todos','work-t',{'title':'휴대폰에서 바꾼 제목','date':'2026-11-01','done':True});p.locator('[data-esave]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');row=self.stored('todos','work-t');self.assertEqual(row['title'],'휴대폰에서 바꾼 제목');self.assertEqual(row['date'],'2026-11-01');self.assertTrue(row['done']);self.assertIn('본문만 바꾼',row['noteH'])

    def test_form_draft_after_reload_retains_conflict_base(self):
        p=self.page;self.open_form('refs').fill('닫기 전 내 자료');p.locator('#sheet [data-sx]').click();self.patch('refs','work-r',{'html':'<div>닫힌 사이 휴대폰 자료</div>'});p.reload();ed=self.open_form('refs');expect(ed).to_contain_text('닫기 전');p.locator('[data-rsave]').click();expect(p.locator('.save-conflict')).to_be_visible();self.assertIn('휴대폰 자료',self.stored('refs','work-r')['html'])

    def test_form_conflict_choice_rechecks_server_and_can_save_a_copy(self):
        p=self.page;ed=self.open_form('moms');ed.fill('내가 남긴 회고');self.patch('moms','work-m',{'h':'<div>휴대폰 회고</div>'});p.locator('[data-record-save]').click();expect(p.locator('.save-conflict')).to_be_visible();self.patch('moms','work-m',{'h':'<div>또 새로 바뀐 회고</div>'});p.locator('[data-sheet-use-local]').click();expect(p.locator('.save-conflict')).to_contain_text('또 새로 바뀐 회고');p.locator('[data-sheet-save-copy]').click();expect(p.locator('#scrim')).not_to_have_class('scrim on');expect(p.locator('[data-db]')).to_contain_text('내가 남긴 회고');self.assertIn('또 새로 바뀐',self.stored('moms','work-m')['h'])

    def test_transient_failure_retries_with_backoff_without_online_event(self):
        p=self.page;ed=self.note();p.evaluate("window.__failWrites=true;window.__writeErrorCode='unavailable'");ed.fill('잠깐 실패한 뒤 자동 재시도');expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집');p.evaluate('window.__failWrites=false');p.wait_for_function("__store.notes.find(n=>n.id==='work-n').html.includes('자동 재시도')",timeout=8000);self.wait_saved()

    def test_saving_one_field_does_not_rebase_another_unsaved_field(self):
        p=self.page;ed=self.note();p.evaluate('window.__writeDelayMs=450');p.locator('[data-dt]').fill('PC에서 고친 제목');p.wait_for_timeout(650)
        p.evaluate("__store.notes.find(n=>n.id==='work-n').html='<div>제목 저장 중 도착한 원격 본문</div>'");ed.fill('옛 본문에서 이어쓴 PC 내용');self.wait_conflict();self.assertIn('원격 본문',self.stored('notes','work-n')['html'])

    def test_deleted_form_can_keep_body_and_metadata_in_a_new_note(self):
        p=self.page;ed=self.open_form('todos');ed.fill('삭제 전에 작성한 메모');p.locator('#e-d').fill('2026-11-02');p.evaluate("async()=>{const f=await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');await f.deleteDoc(f.doc(f.collection({},'todos'),'work-t'))}");p.locator('[data-esave]').click();expect(p.locator('.save-conflict')).to_contain_text('삭제된 항목');p.locator('[data-sheet-save-copy]').click();expect(p.locator('[data-db]')).to_contain_text('삭제 전에 작성한 메모');expect(p.locator('[data-db]')).to_contain_text('2026-11-02');self.assertIsNone(self.stored('todos','work-t'))

    def check_auto_surface(self,surface):
        p=self.page
        if surface=='memo':
            self.patch('logs','memo_work',{'html':'<div>처음 잊지 말 것</div>'});p.locator('nav [data-tab="home"]').click();selector='[data-memo]';c='logs';id='memo_work';field='html'
        else:
            self.patch('projects','work-p',{'mods':{'memo':True}});self.patch('moms','work-m',{'pid':'work-p','h':'<div>처음 진행 기록</div>'});p.locator('nav [data-tab="proj"]').click();p.locator('[data-open="work-p"]').click();selector='[data-pmemo]' if surface=='core' else '[data-mt="work-m"]';c='projects' if surface=='core' else 'moms';id='work-p' if surface=='core' else 'work-m';field='memoH' if surface=='core' else 'h'
        ui.reveal(p,selector);p.locator(selector).fill('PC에서 작성한 '+surface);self.patch(c,id,{field:'<div>휴대폰에서 작성한 '+surface+'</div>'});self.wait_conflict();self.assertIn('휴대폰에서',self.stored(c,id)[field]);self.assertIn('PC에서',json.dumps(self.drafts(),ensure_ascii=False))

    def test_home_memo_protects_remote_edits(self):self.check_auto_surface('memo')
    def test_project_core_protects_remote_edits(self):self.check_auto_surface('core')
    def test_project_history_protects_remote_edits(self):self.check_auto_surface('history')

    def test_record_draft_after_reload_keeps_its_original_base(self):
        p=self.page;self.open_form('moms').fill('닫기 전 남긴 회고');p.locator('#sheet [data-sx]').click();self.patch('moms','work-m',{'h':'<div>닫힌 사이 다른 기기 회고</div>'});p.reload();ed=self.open_form('moms');expect(ed).to_contain_text('닫기 전 남긴 회고');p.locator('[data-record-save]').click();expect(p.locator('.save-conflict')).to_be_visible();self.assertIn('다른 기기 회고',self.stored('moms','work-m')['h'])

    def test_account_switch_does_not_retry_another_users_edits(self):
        p=self.page;auth="export const getAuth=()=>({}); export const GoogleAuthProvider=class {}; export const signInWithPopup=async()=>{}; export const signInWithCredential=async()=>{}; export const signOut=async()=>{}; export const onAuthStateChanged=(auth,cb)=>{window.__authChanged=cb;setTimeout(()=>cb({uid:'ui-test'}),0);};"
        p.route('**/firebase-auth.js',lambda route:route.fulfill(status=200,body=auth,content_type='application/javascript',headers={'Access-Control-Allow-Origin':'*'}));p.reload();ed=self.note();p.evaluate("window.__failWrites=true;window.__writeErrorCode='unavailable'");ed.fill('첫 계정의 미전송 내용');expect(p.locator('#save-status')).to_contain_text('저장되지 않은 편집');p.evaluate("window.__failWrites=false;window.__authChanged({uid:'second-user'});window.dispatchEvent(new Event('online'))");p.wait_for_timeout(700);self.assertEqual(self.stored('notes','work-n')['html'],'<div>중요한 결정</div>');self.assertTrue(self.drafts());self.assertEqual(p.evaluate("localStorage.getItem('arecmik:edits:second-user')"),None)

if __name__=='__main__':unittest.main()

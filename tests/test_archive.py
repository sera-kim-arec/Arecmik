"""Run with: python3 -m unittest discover -s tests -v

Requires Python Playwright and Chromium. Firebase is replaced with an in-memory
adapter; these tests never authenticate or read/write a real Firebase project.
"""
import functools
import http.server
import json
from pathlib import Path
import threading
import unittest
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
STAMP = 1792022400000  # 2026-10-15
SEED = {
    "projects": [
        {"id": "work-p", "name": "업무 프로젝트", "space": "work", "status": "active", "created": STAMP, "memoH": "<div>업무 프로젝트 메모</div>"},
        {"id": "life-p", "name": "여행 준비", "space": "life", "status": "active", "created": STAMP, "mods": {"cost": True}},
    ],
    "moms": [
        {"id": "work-m", "t": "업무 회의 회고", "space": "work", "d": "2026-10-15", "at": STAMP},
        {"id": "life-m", "t": "바닷가 산책", "space": "life", "d": "2026-10-14", "at": STAMP},
    ],
    "notes": [
        {"id": "work-n", "title": "업무 회의록", "html": "<div>중요한 결정</div>", "space": "work", "created": STAMP},
        {"id": "life-n", "title": "숙소 후보", "html": "<div>조용한 바닷가</div>", "space": "life", "created": STAMP},
        {"id": "life-linked", "title": "여행 예약 정보", "html": "<div>예약번호 1234</div>", "space": "life", "pid": "life-p", "created": STAMP},
        {"id": "life-log", "log": True, "mon": "2026-10", "space": "life", "html": "<div class='h2 dayh'>10/14 (수)</div><div>즐거웠던 하루</div>", "updated": STAMP},
    ],
    "todos": [
        {"id": "life-t", "title": "숙소 예약", "space": "life", "projectId": "life-p", "done": True, "doneDate": "2026-10-14", "created": STAMP},
        {"id": "work-t", "title": "보고서 제출", "space": "work", "done": False, "noteH": "<div>검토 의견</div>", "created": STAMP},
    ],
    "exps": [
        {"id": "life-e", "t": "숙박 결제", "a": 150000, "sp": "life", "pid": "life-p", "tid": "life-t", "memo": "오션뷰 예약금", "d": "2026-10-14"},
        {"id": "work-e", "t": "업무 도서", "a": 20000, "pid": "work-p", "sp": "work", "d": "2026-10-15"},
    ],
    "refs": [
        {"id": "legacy-r", "title": "기존 자료", "html": "<div>대표번호</div>", "created": STAMP},
        {"id": "life-r", "title": "여행 자료", "html": "<div>여행 지도</div>", "space": "life", "created": STAMP},
        {"id": "work-r", "title": "업무 자료", "html": "<div>팀 연락처</div>", "space": "work", "created": STAMP},
    ],
    "logs": [], "trash": [], "ents": [], "fbk": [],
}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(timezone_id="Asia/Seoul", service_workers="block")
        self.context.add_init_script("window.__store = JSON.parse(sessionStorage.getItem('mock-db') || " + json.dumps(json.dumps(SEED)) + ");")
        self.external = []
        firestore = (ROOT / "tests/firebase_mock.js").read_text()

        def route(request):
            url = urlsplit(request.request.url)
            if url.hostname == "127.0.0.1":
                request.continue_()
            elif url.hostname == "www.gstatic.com":
                name = Path(url.path).name
                modules = {
                    "firebase-app.js": "export const initializeApp = () => ({});",
                    "firebase-auth.js": "export const getAuth=()=>({}); export const GoogleAuthProvider=class {}; export const signInWithPopup=async()=>{}; export const signInWithCredential=async()=>{}; export const signOut=async()=>{}; export const onAuthStateChanged=(auth,cb)=>setTimeout(()=>cb({uid:'ui-test'}),0);",
                    "firebase-firestore.js": firestore,
                }
                self.assertIn(name, modules)
                request.fulfill(status=200, body=modules[name], content_type="application/javascript", headers={"Access-Control-Allow-Origin": "*"})
            else:
                self.external.append(request.request.url)
                request.abort()

        self.context.route("**/*", route)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.origin)
        expect(self.page.locator("#app")).to_be_visible()
        self.page.locator("nav [data-tab='rec']").click()
        expect(self.page.locator(".archive-intro")).to_be_visible()

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.external, [])
        self.context.close()

    def life(self):
        self.page.locator("[data-sp='life']").click()
        expect(self.page.locator(".archive-intro h2")).to_have_text("나의 일상 보관함")

    def search(self, query):
        if not self.page.locator('#srch.on').count():
            self.page.locator("[data-search]").click()
        self.page.locator("#sqi").fill(query)

    def test_spaces_search_and_legacy_references(self):
        expect(self.page.locator(".archive")).to_contain_text("업무 회의 회고")
        expect(self.page.locator(".archive")).not_to_contain_text("바닷가 산책")
        expect(self.page.locator(".archive")).to_contain_text("기존 자료")
        self.life()
        expect(self.page.locator(".archive")).to_contain_text("바닷가 산책")
        expect(self.page.locator(".archive")).to_contain_text("즐거웠던 하루")
        expect(self.page.locator(".archive")).not_to_contain_text("기존 자료")
        self.search("업무")
        expect(self.page.locator("#sqr [data-sgo]")).to_have_count(0)
        self.page.locator("#sqi").fill("산책")
        expect(self.page.locator("#sqr [data-sgo='mom']")).to_have_count(1)
        self.page.locator("#sqi").fill("오션뷰")
        self.page.locator("#sqr [data-sgo='expense']").click()
        expect(self.page.locator("#x-t")).to_have_value("숙박 결제")
        expect(self.page.locator("#x-tid")).to_have_value("life-t")

    def test_capture_project_context_and_search_without_duplication(self):
        self.life()
        self.page.locator("[data-record-new]").click()
        self.page.locator("#record-body").fill("오늘의 여행 회고\n기억하고 싶은 풍경")
        self.page.locator("#record-project").select_option("life-p")
        self.page.locator("[data-record-save]").click()
        expect(self.page.locator("#scrim")).not_to_have_class("scrim on")
        expect(self.page.locator(".archive")).to_contain_text("오늘의 여행 회고")
        rows = self.page.evaluate("window.__store.moms")
        saved = [r for r in rows if "오늘의 여행 회고" in r["t"]]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["space"], "life")
        self.assertEqual(saved[0]["pid"], "life-p")
        self.page.locator("nav [data-tab='proj']").click()
        self.page.locator("[data-open='life-p']").click()
        expect(self.page.locator(".pmemo:not(.pcore)")).to_contain_text("오늘의 여행 회고")
        self.page.locator(".project-connections [data-conn-record]").click()
        expect(self.page.locator("#record-project")).to_have_value("life-p")
        self.page.locator("#sheet [data-sx='0']").click()
        self.search("풍경")
        self.page.locator("#sqi").press("Enter")
        expect(self.page.locator("#record-body")).to_contain_text("풍경")

    def test_link_existing_and_create_project_document(self):
        self.life()
        self.page.locator("nav [data-tab='proj']").click()
        self.page.locator("[data-open='life-p']").click()
        self.page.locator("[data-record-link]").click()
        expect(self.page.locator("#record-existing option")).to_have_count(1)
        self.page.locator("[data-record-attach]").click()
        expect(self.page.locator(".project-records")).to_contain_text("숙소 후보")
        self.assertEqual(self.page.evaluate("window.__store.notes.length"), len(SEED["notes"]))
        self.assertEqual(self.page.evaluate("window.__store.notes.find(n=>n.id==='life-n').pid"), "life-p")
        self.page.locator(".project-records [data-newdoc]").click()
        expect(self.page.locator("[data-dpj]")).to_have_value("life-p")
        expect(self.page.locator(".record-project-link")).to_contain_text("여행 준비")
        self.page.locator(".dt").fill("새 여행 기록")
        self.page.locator("[data-db]").fill("여행에서 배운 점")
        expect(self.page.locator("[data-db]")).to_contain_text("여행에서 배운 점")
        self.page.locator(".record-project-link button").click()
        expect(self.page.locator(".project-records")).to_be_visible()

    def test_filters_mobile_and_write_failure_preserve_text(self):
        self.life()
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.locator("[data-archive-filter='expense']").click()
        expect(self.page.locator(".archive [data-archive-open]")).to_have_count(1)
        self.page.locator("[data-archive-month]").select_option("2026-10")
        self.page.locator("[data-archive-project]").select_option("life-p")
        expect(self.page.locator(".archive")).to_contain_text("숙박 결제")
        self.page.locator("[data-archive-reset]").click()
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)
        self.page.screenshot(path="/tmp/arecmik-life-archive.png", full_page=True)
        self.page.locator("[data-record-new]").click()
        self.page.locator("#record-body").fill("저장 실패해도 남아야 할 기록")
        self.page.evaluate("window.__failWrites=true")
        self.page.locator("[data-record-save]").click()
        expect(self.page.locator("#record-body")).to_contain_text("저장 실패해도 남아야 할 기록")
        expect(self.page.locator("[data-record-save]")).to_be_enabled()
        self.page.evaluate("window.__failWrites=false")
        self.page.locator("[data-record-save]").click()
        expect(self.page.locator(".archive")).to_contain_text("저장 실패해도 남아야 할 기록")

    def test_reference_creation_and_moving_legacy_between_spaces(self):
        self.page.locator("[data-rt='ref']").click()
        self.page.locator("[data-oref='legacy-r'] span").click()
        expect(self.page.locator("#r-space")).to_have_value("work")
        self.page.locator("#r-space").select_option("life")
        self.page.locator("[data-rsave]").click()
        expect(self.page.locator("[data-oref='legacy-r']")).to_have_count(0)
        self.page.locator("[data-sp='life']").click()
        expect(self.page.locator("[data-oref='legacy-r']")).to_be_visible()
        self.page.locator("[data-newref]").click()
        expect(self.page.locator("#r-space")).to_have_value("life")
        self.page.locator("#r-t").fill("나의 독서 목록")
        self.page.locator("#r-b").fill("읽고 싶은 책")
        self.page.locator("[data-rsave]").click()
        expect(self.page.locator(".rw")).to_contain_text("나의 독서 목록")
        saved = self.page.evaluate("window.__store.refs.filter(r=>r.title==='나의 독서 목록')")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["space"], "life")
        self.assertEqual(self.page.evaluate("window.__store.refs.find(r=>r.id==='legacy-r').space"), "life")
        self.page.locator("[data-sp='work']").click()
        expect(self.page.locator(".rw")).not_to_contain_text("나의 독서 목록")

    def test_record_search_all_sources_editing_and_home_capture(self):
        self.search("검토 의견")
        self.page.locator("#sqr [data-sgo='todo']").click()
        expect(self.page.locator("#e-t")).to_have_value("보고서 제출")
        self.page.locator("#sheet [data-sx='0']").click()
        self.search("업무 프로젝트 메모")
        self.page.locator("#sqr [data-sgo='pmemo']").click()
        expect(self.page.locator("[data-pmemo='work-p']")).to_be_visible()
        self.page.locator("nav [data-tab='rec']").click()
        self.life()
        self.page.locator("#rq").fill("산책")
        self.page.locator(".rw [data-archive-open='mom']").click()
        self.page.locator("#record-day").fill("2026-09-20")
        self.page.locator("#record-project").select_option("life-p")
        self.page.locator("#record-body").fill("가을 바닷가 산책")
        self.page.locator("[data-record-save]").click()
        saved = self.page.evaluate("window.__store.moms.find(m=>m.id==='life-m')")
        self.assertEqual(saved["d"], "2026-09-20")
        self.assertEqual(saved["pid"], "life-p")
        self.assertEqual(saved["t"], "가을 바닷가 산책")
        self.assertEqual(self.page.evaluate("window.__store.moms.length"), len(SEED["moms"]))
        self.page.locator("nav [data-tab='home']").click()
        self.page.locator(".hhead [data-record-new]").click()
        expect(self.page.locator("#sheet h3")).to_contain_text("LIFE")
        expect(self.page.locator("#record-project option[value='work-p']")).to_have_count(0)

    def test_record_content_is_escaped_and_archive_paginates(self):
        self.life()
        self.page.locator("[data-record-new]").click()
        self.page.locator("#record-body").fill('<img src=x onerror="window.__injected=true">')
        self.page.locator("[data-record-save]").click()
        expect(self.page.locator(".archive")).to_contain_text('<img src=x onerror="window.__injected=true">')
        self.assertFalse(self.page.evaluate("!!window.__injected"))
        # Exercise the actual snapshot subscription while adding older fixture rows.
        self.page.evaluate("""async () => {
          const {addDoc, collection} = await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
          for (let i=0; i<45; i++) await addDoc(collection({}, 'moms'), {
            t:'과거 기록 '+i, space:'life', d:'2026-01-01', at:i
          });
        }""")
        expect(self.page.locator(".archive [data-archive-open]")).to_have_count(40)
        self.page.locator("[data-archive-more]").click()
        expect(self.page.locator(".archive [data-archive-open]")).to_have_count(53)
        expect(self.page.locator("[data-archive-more]")).to_have_count(0)


if __name__ == "__main__":
    unittest.main()

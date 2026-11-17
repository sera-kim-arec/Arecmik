# Arecmik

개인 업무·생활 기록 웹앱. 주소: https://sera-kim-arec.github.io/Arecmik/

다른 채팅에서 이어서 작업할 때는 [제품 방향과 사용자 선호](docs/product-direction.md)와 [작업 맥락](AGENTS.md)을 먼저 참고하세요.

## 구성
- `index.html` — 앱 전체(바닐라 JS 한 파일). WORK(캘린더·할일·코멘트·메모·루틴·복기·카테고리·프로젝트·노트) / LIFE(일기·스크랩·컬렉션)
- `sw.js`, `manifest.json`, `*-lemon.png` — 설치형 앱(PWA)
- `widget*.html|js|css`, `widget-preview-*.png`, `icon-192.png` — 안드로이드 위젯 연결 화면
- `android/`, `android-release.json`, `downloads/` — 안드로이드 앱 소스와 배포 APK
- `scripts/push/` — 알림 발송(GitHub Actions `push-reminders.yml`)
- `scripts/drive-export/` — 앱 기록을 구글 드라이브 `Kurly_개인업무/업무 히스토리/앱 기록 (자동)`으로 매일 내보내는 Apps Script

## 저장
Firebase Firestore `users/{uid}/arecmik2/{컬렉션__id}` 문서마다 필드 `j`에 JSON 문자열.

## 보안
GitHub 시크릿(FIREBASE_SA, WEB_PUSH_PRIVATE_KEY)과 외부 API 키는 코드·대화에 적지 않습니다. 키는 앱 설정에만 둡니다.

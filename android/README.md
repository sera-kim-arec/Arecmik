# Arecmik 안드로이드 앱 · 월 달력 위젯

Android 8(API 26) 이상에서 기존 웹앱을 앱 창으로 사용하고, 홈 화면의 월 달력에서 일정·할 일을 완료 체크하는 개인 설치용 앱입니다. v1.1.1(versionCode 3)은 기존 위젯 APK와 패키지·서명 키가 같아 삭제 없이 업데이트합니다. `../widget.html`의 설치 안내에서 APK를 받을 수 있습니다.

## 개발·검증

JDK 17, Android SDK 플랫폼 35, 빌드 도구 35.0.0을 사용합니다. `local.properties`의 `sdk.dir` 또는 `ANDROID_HOME`으로 SDK를 지정하고 실행합니다.

```sh
./gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleRelease
```

Gradle Wrapper는 8.13이며 배포 파일 SHA-256을 검증합니다. Android Gradle Plugin은 8.9.2입니다. Robolectric 4.14.1의 Android 35 환경에서 실제 RemoteViews 레이아웃 생성, 날짜·공간 변경, 목록 생성과 완료 변경의 기기 저장을 검증합니다. 순수 Java 테스트는 월 경계·기간 일정·Firestore 데이터 변환·반복 회차·암호화 무결성을 검사합니다. 브라우저 연결 화면 테스트는 저장소 루트에서 `python3 -m unittest discover -s tests -v`로 실행합니다.

클라우드의 제한된 파일시스템에서는 Robolectric의 공식 오프라인 런타임 경로를 `-Drobolectric.dependency.dir=/workspace/android-tools`로 지정합니다. 런타임 JAR는 Maven Central의 SHA-512와 대조한 파일을 사용합니다. TLS 검증을 끄지 않으며, 필요한 경우 시스템 인증서 저장소를 지정합니다.

## 설치 파일 서명

릴리스 빌드 후 `JAVA_HOME`과 `ANDROID_HOME`을 설정하고 실행합니다.

```sh
python3 scripts/sign-apk.py
```

서명 키와 비밀번호는 기본적으로 **저장소 밖**의 `../arecmik-signing`에 만들며 `ARECMIK_SIGNING_DIR`로 바꿀 수 있습니다. 이 디렉터리는 비공개로 보관하고 백업해야 같은 앱을 업데이트할 수 있습니다. 저장소·웹 페이지·APK 배포 디렉터리에 복사하지 마세요. 서명된 APK와 SHA-256만 `../downloads/`에 배포합니다. 플레이스토어 계정이나 등록비는 필요 없습니다.

## 앱 화면

`AppActivity`는 기존 GitHub Pages 앱을 WebView 안에 표시합니다. 기존 앱의 ‘⚙ → 위젯 설정’에서 연결·위젯 추가·수동 동기화를 엽니다. 외부 링크는 브라우저로 보내며, 사진은 Android 문서 선택기, JSON 백업은 문서 저장 선택기를 사용합니다. 저장소 전체 접근 권한은 요청하지 않습니다. 뒤로 가기는 열린 입력창·검색부터 닫고, 마지막에는 화면을 보존한 채 앱을 백그라운드로 이동합니다. 웹 화면의 첫 로드에는 인터넷 연결이 필요합니다.

날짜는 17sp, 목록 제목은 16sp, 보조 글씨는 13sp입니다. 각 날짜의 작은 점은 해당 WORK/LIFE에 일정이 있다는 표시이고 제목은 선택한 날의 목록에서 표시합니다. 권장 위젯 크기는 4×5 이상이며 280×480dp에서 기본 글꼴 배치와 320×540dp에서 글꼴 1.3배를 검사합니다.

## 계정 연결

Google 로그인을 WebView에 넣지 않습니다. Android 앱이 일회용 P-256 키와 10분 기한의 난수를 만들고, 기존 GitHub Pages의 `widget-connect.html`을 기본 브라우저에서 엽니다. 사용자가 같은 Google 계정으로 로그인하고 명시적으로 연결을 누르면 Firebase 세션을 ECDH·SHA-256·AES-GCM으로 암호화하여 이 휴대폰 앱으로 전달합니다. 앱 연결 모드에서는 버튼 클릭으로 `signInWithPopup`을 실행하여 Google OAuth 자격도 함께 암호화합니다. 네이티브는 Firebase refresh 응답의 UID를 검증한 뒤 OAuth 자격을 별도 암호화 레코드에 최대 10분간 보관합니다. 기존 1.0.0 위젯 전용 연결 흐름도 호환됩니다.

연결 주소에는 공개 키와 난수만 있고, 응답 주소에는 암호문만 있습니다. Android는 세션 난수·기한·Firebase 프로젝트·서버에서 확인한 UID를 대조하고, 일회용 키를 소모합니다. 장기 연결 정보와 남아 있는 연결 키는 Android Keystore의 AES-GCM 키로 암호화합니다. 앱 백업을 비활성화했고, 평문 토큰을 주소·로그·APK에 넣지 않습니다. 브라우저 연결 페이지는 토큰을 별도 웹 저장소에 기록하지 않습니다. 앱 내부 로그인은 Firebase SDK의 정상 인증 영속 저장소를 사용합니다. 앱은 정확한 GitHub Pages origin과 `/Arecmik/`, `/Arecmik/index.html`에만 Android `WebMessagePort`를 연결합니다. 파일·content URL 접근, 혼합 콘텐츠, 서드파티 쿠키, JavaScript Java 인터페이스는 사용하지 않습니다. iframe이 만든 채널은 거부합니다. 웹은 전달받은 Google OAuth 자격을 공식 Firebase `signInWithCredential`로 교환하고 예상 UID를 확인한 뒤 완료를 응답하며, 네이티브는 일회용 자격을 지웁니다. Firebase 내부 저장소 형식을 조작하거나 WebView에서 Google OAuth를 실행하지 않습니다. 로그아웃·기기 연결 해제는 앱과 위젯에 함께 적용합니다.

Firebase 공개 클라이언트 설정은 인증 비밀키가 아닙니다.

Native 앱은 기존 Firebase ID 토큰과 보안 규칙을 사용하는 HTTPS REST API로 사용자 자신의 `users/<uid>/todos`에만 접근합니다. 관리자 키, 공개 ICS 피드, 별도 서버·Cloud Functions·Firebase 요금제 변경은 사용하지 않습니다. 실제 Google 계정 로그인·보안 규칙·기기별 홈 화면과 절전 동작은 설치 후 확인해야 합니다.

## 동기화와 데이터 보존

- 전체 일정 스냅샷을 앱 비공개 저장소에 보관하므로 월 이동·날짜 선택·WORK/LIFE 전환에는 추가 조회가 없습니다. 자동 동기화는 약 1시간 간격이며 Android의 작업·절전 정책으로 지연될 수 있습니다. ↻는 동기화 작업을 요청합니다.
- 완료 체크는 기기에 먼저 기록하고 전송 대기 목록에 보관합니다. 인터넷이 연결되면 JobScheduler 작업이 서버에 반영합니다. 원본 삭제 시 재생성하지 않으며, 서버의 최신 문서 버전을 조건으로 완료 필드만 변경합니다.
- 반복 완료는 다음 회차 생성과 원본 완료를 Firestore 단일 커밋으로 처리합니다. 재시도에 고정된 새 문서 ID를 쓰고, 이미 처리한 원본은 다음 회차를 다시 만들지 않습니다. 매일·평일·주·월·년·사용자 반복과 ICU 음력 연간 반복을 지원합니다.
- 연결 해제는 이 기기의 캐시·대기 변경·연결 정보를 삭제하며 원본 기록은 삭제하지 않습니다. 대기 변경이 있으면 다른 계정으로 조용히 바꾸지 않습니다.
- 앱 자체의 Firestore 읽기 예산을 보수적으로 하루 20,000회로 제한합니다. 상한에 도달하면 기기 데이터를 유지하고 다음 날 재개합니다. **기존 Firebase 무료 한도는 웹앱과 함께 적용**되며 이 앱은 유료 요금제를 활성화하지 않습니다.

테스트는 실제 사용자 데이터를 읽거나 변경하지 않습니다. 실제 계정 연결과 휴대폰 홈 화면 동작은 설치 후 확인합니다.

## 레몬 아이콘과 앱 업데이트

기존 `icon-512.png`와 `icon-maskable.png` 원본을 Android 아이콘 리소스에 그대로 사용합니다. 로그인 화면·계정 설정·설치 안내에도 같은 레몬을 표시합니다.

웹 설정의 ‘APK 설치 · 업데이트’는 `downloads/Arecmik-latest.apk`를 직접 다운로드합니다. 네이티브 앱의 같은 버튼은 공개 `android-release.json`에서 새 버전을 확인하고, APK를 앱 비공개 캐시에 받은 뒤 SHA-256, 패키지 이름, 설치된 앱과 같은 서명 인증서, 증가하는 버전 번호를 검사합니다. 검사에 통과한 파일만 읽기 전용 ContentProvider로 Android 설치기에 전달합니다. 최초에는 ‘이 출처의 앱 설치’를 허용해야 하며, 마지막 설치는 사용자가 확인합니다. 최신 버전이면 다시 설치하지 않습니다. 다른 호스트로의 리디렉션, 외부 APK URL, 다른 서명 또는 같은·낮은 버전의 설치 파일은 거부합니다.

`sign-apk.py`는 Gradle 버전에서 파일명을 계산하고, 버전별 APK·최신 APK·체크섬·업데이트 메타데이터를 함께 생성합니다. 새 버전 배포 시 이 파일들을 함께 반영해야 합니다.

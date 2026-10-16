# Arecmik 안드로이드 월 달력 위젯

Android 8(API 26) 이상에서 월 달력을 보고, 날짜를 선택해 일정·할 일을 확인하고 완료 체크하는 개인 설치용 앱입니다. `../widget.html`의 설치 안내에서 APK를 받을 수 있습니다.

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

## 계정 연결

Google 로그인을 WebView에 넣지 않습니다. Android 앱이 일회용 P-256 키와 10분 기한의 난수를 만들고, 기존 GitHub Pages의 `widget-connect.html`을 기본 브라우저에서 엽니다. 사용자가 같은 Google 계정으로 로그인하고 명시적으로 연결을 누르면 Firebase 세션을 ECDH·SHA-256·AES-GCM으로 암호화하여 이 휴대폰 앱으로 전달합니다.

연결 주소에는 공개 키와 난수만 있고, 응답 주소에는 암호문만 있습니다. Android는 세션 난수·기한·Firebase 프로젝트·서버에서 확인한 UID를 대조하고, 일회용 키를 소모합니다. 장기 연결 정보와 남아 있는 연결 키는 Android Keystore의 AES-GCM 키로 암호화합니다. 앱 백업을 비활성화했고, 평문 토큰을 주소·로그·웹 저장소·APK에 넣지 않습니다. Firebase 공개 클라이언트 설정은 인증 비밀키가 아닙니다.

Native 앱은 기존 Firebase ID 토큰과 보안 규칙을 사용하는 HTTPS REST API로 사용자 자신의 `users/<uid>/todos`에만 접근합니다. 관리자 키, 공개 ICS 피드, 별도 서버·Cloud Functions·Firebase 요금제 변경은 사용하지 않습니다. 실제 Google 계정 로그인·보안 규칙·기기별 홈 화면과 절전 동작은 설치 후 확인해야 합니다.

## 동기화와 데이터 보존

- 전체 일정 스냅샷을 앱 비공개 저장소에 보관하므로 월 이동·날짜 선택·WORK/LIFE 전환에는 추가 조회가 없습니다. 자동 동기화는 약 1시간 간격이며 Android의 작업·절전 정책으로 지연될 수 있습니다. ↻는 동기화 작업을 요청합니다.
- 완료 체크는 기기에 먼저 기록하고 전송 대기 목록에 보관합니다. 인터넷이 연결되면 JobScheduler 작업이 서버에 반영합니다. 원본 삭제 시 재생성하지 않으며, 서버의 최신 문서 버전을 조건으로 완료 필드만 변경합니다.
- 반복 완료는 다음 회차 생성과 원본 완료를 Firestore 단일 커밋으로 처리합니다. 재시도에 고정된 새 문서 ID를 쓰고, 이미 처리한 원본은 다음 회차를 다시 만들지 않습니다. 매일·평일·주·월·년·사용자 반복과 ICU 음력 연간 반복을 지원합니다.
- 연결 해제는 이 기기의 캐시·대기 변경·연결 정보를 삭제하며 원본 기록은 삭제하지 않습니다. 대기 변경이 있으면 다른 계정으로 조용히 바꾸지 않습니다.
- 앱 자체의 Firestore 읽기 예산을 보수적으로 하루 20,000회로 제한합니다. 상한에 도달하면 기기 데이터를 유지하고 다음 날 재개합니다. **기존 Firebase 무료 한도는 웹앱과 함께 적용**되며 이 앱은 유료 요금제를 활성화하지 않습니다.

테스트는 실제 사용자 데이터를 읽거나 변경하지 않습니다. 실제 계정 연결과 휴대폰 홈 화면 동작은 설치 후 확인합니다.

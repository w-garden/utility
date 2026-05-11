# notion-to-youtube 셋업 가이드

Notion 페이지에 흩어진 YouTube URL을 주별 재생목록으로 자동 생성하는 CLI 도구의 인증/자격증명 셋업 가이드.

## 보안 전략

회사 PC 디스크에 OAuth 자격증명을 두지 않기 위해 **GitHub 비공개 Gist**에 저장하고, 회사 PC에는 **GitHub PAT만 macOS Keychain에 저장**하는 방식을 사용한다.

- OAuth client JSON → 개인 GitHub의 비공개 Gist
- OAuth refresh token → 같은 Gist에 자동 저장 (첫 인증 후)
- GitHub PAT → 회사 PC Keychain (`github-pat-gist`)
- Notion integration token → 회사 PC Keychain (`mcp-notion`) — 이미 설정됨

코드 실행 시점에 PAT으로 Gist를 읽어 메모리에서만 사용하고, 디스크에는 평문 자격증명이 남지 않는다.

> ⚠️ 코드가 회사 PC에서 실행되는 한, 실행 중에는 메모리에 자격증명이 올라온다. 완벽한 분리가 필요하면 개인 클라우드 서버에서 cron으로 돌려야 한다.

---

## 사전 준비

- 개인 Google 계정 (회사 계정 ❌)
- 개인 GitHub 계정
- macOS Keychain 사용 가능 환경

---

## Step 1. Google Cloud OAuth 클라이언트 생성

> 모든 작업을 **개인 Google 계정**으로 진행. 회사 계정으로 만들면 회사 정책에 묶임.

1. https://console.cloud.google.com/ → 개인 Gmail로 로그인
2. 상단 프로젝트 선택 → **새 프로젝트**
   - 이름: `notion-youtube-sync`
   - 만들기
3. 좌측 메뉴 → **API 및 서비스 → 라이브러리**
   - `YouTube Data API v3` 검색 → 클릭 → **사용**
4. 좌측 메뉴 → **API 및 서비스 → OAuth 동의 화면**
   - User Type: **외부** 선택 → 만들기
   - 앱 정보:
     - 앱 이름: `notion-youtube-sync`
     - 사용자 지원 이메일: 본인 개인 Gmail
     - 개발자 연락처 정보: 본인 개인 Gmail
   - 스코프: **저장 후 계속** (건너뛰기)
   - 테스트 사용자: **+ ADD USERS** → 본인 개인 Gmail 추가 → 저장 후 계속
5. 좌측 메뉴 → **API 및 서비스 → 사용자 인증 정보**
   - **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID**
   - 애플리케이션 유형: **데스크톱 앱**
   - 이름: `notion-youtube-cli`
   - 만들기 → 팝업에서 **JSON 다운로드**

---

## Step 2. GitHub 비공개 Gist에 업로드

1. https://gist.github.com/ 접속 (개인 GitHub 계정)
2. 파일명: `youtube_oauth.json`
3. 다운로드받은 JSON 내용 통째로 붙여넣기
4. 우측 하단 **"Create secret gist"** 클릭 (Public ❌, **Secret ✅**)
5. 생성된 URL에서 **Gist ID** 복사
   - 예: `https://gist.github.com/yourname/abc123def456` → `abc123def456`

---

## Step 3. 로컬 파일 즉시 삭제

Gist에 업로드한 직후 다운로드 파일을 삭제한다.

```bash
rm ~/Downloads/client_secret_*.json
```

---

## Step 4. GitHub PAT 발급

1. https://github.com/settings/personal-access-tokens/new
2. **Fine-grained token** 선택
3. 설정:
   - Token name: `notion-youtube-cli`
   - Expiration: 1 year (또는 원하는 기간)
   - Resource owner: 본인
   - Repository access: **Public Repositories (read-only)** 그대로
   - Permissions:
     - **Account permissions → Gists**: **Read and write**
       - (refresh token을 같은 Gist에 다시 저장하기 위해 write 필요)
4. **Generate token** → `github_pat_...` 토큰 복사

---

## Step 5. PAT을 macOS Keychain에 저장

```bash
security add-generic-password -U \
  -s "github-pat-gist" \
  -a "$USER" \
  -w "여기에_PAT_붙여넣기"
```

확인:

```bash
security find-generic-password -s "github-pat-gist" -a "$USER" -w | head -c 12
# github_pat_ 로 시작하면 OK
```

---

## Step 6. Gist ID 기록

Step 2에서 복사한 Gist ID를 코드 실행 시 환경변수 또는 설정 파일로 전달한다. 추후 코드 작성 시 처리.

---

## 인증 흐름 (코드 실행 시)

1. `security`로 `github-pat-gist` 토큰 읽기
2. PAT으로 Gist API 호출 → `youtube_oauth.json` 내용 가져오기
3. **첫 실행**: Google OAuth flow → 브라우저 열림 → 동의 → refresh token 받음 → Gist에 `youtube_refresh_token.json` 파일로 저장 (PATCH)
4. **이후 실행**: Gist에서 refresh token 가져와 access token 발급 → API 호출

---

## 체크리스트

작업 진행하면서 체크.

- [ ] Step 1. Google Cloud OAuth 클라이언트 JSON 다운로드 완료
- [ ] Step 2. GitHub 비공개 Gist 생성 + Gist ID 기록
- [ ] Step 3. 로컬 JSON 파일 삭제
- [ ] Step 4. GitHub Fine-grained PAT 발급 (Gists: Read and write)
- [ ] Step 5. Keychain에 PAT 저장 (`github-pat-gist`)
- [ ] Step 6. Gist ID를 안전한 곳에 메모

전부 완료되면 다음 단계(코드 작성)로 진행.

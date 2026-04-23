# QT Notion Daily Sync

매일 [생명의 삶(두란노)](https://www.duranno.com/qt/) QT 성경 본문을 자동으로 Notion에 저장하는 스크립트입니다.

## 결과물

Notion QT 데이터베이스에 아래와 같이 자동 생성됩니다.

- **날짜**: 오늘 날짜
- **제목**: 그날 QT 제목 (예: 위대하고 존귀하신 창조주 하나님)
- **본문**: 성경 범위 (예: 시편 104 : 1~9)
- **페이지 내용**: 성경 본문 + 묵상/기도/적용 섹션

---

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/w-garden/utility.git
cd utility
```

### 2. Python 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. Notion 통합 토큰 발급

1. [notion.so/my-integrations](https://www.notion.so/my-integrations) 접속
2. **+ 새 통합** 클릭 → 이름 입력 → 저장
3. `ntn_` 또는 `secret_` 으로 시작하는 토큰 복사

### 4. Notion 데이터베이스 준비

Notion에 아래 속성을 가진 데이터베이스를 만드세요.

| 속성명 | 타입 |
|--------|------|
| 제목 | 제목 (title) |
| 날짜 | 날짜 (date) |
| 본문 | 텍스트 (rich_text) |
| 오늘의 하이라이트 | 텍스트 (rich_text) |
| 즐겨찾기 | 체크박스 |

데이터베이스 페이지 우측 상단 `...` → **연결(Connections)** → 생성한 통합 추가

### 5. DATABASE_ID 확인

Notion 데이터베이스 URL에서 ID를 확인합니다.

```
https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       이 부분이 DATABASE_ID
```

### 6. 환경변수 설정

프로젝트 폴더에 `.env` 파일을 생성합니다.

```
NOTION_TOKEN=ntn_여기에_토큰_입력
```

`qt_to_notion.py` 파일에서 `DATABASE_ID`를 본인 것으로 변경합니다.

```python
DATABASE_ID = "여기에_데이터베이스_ID_입력"
```

---

## 로컬 실행

```bash
python qt_to_notion.py
```

실행 시 역본을 선택합니다.

```
역본 선택 (w=우리말성경, k=개역개정, 기본값 w):
```

엔터를 치면 우리말성경으로 실행됩니다.

---

## GitHub Actions 자동화 (매일 오전 6시)

PC 없이 GitHub 서버에서 매일 자동 실행하도록 설정할 수 있습니다.

### 1. GitHub 저장소 생성 후 푸시

```bash
git init
git add scrape_qt.py qt_to_notion.py requirements.txt .gitignore .github/
git commit -m "init"
git remote add origin https://github.com/아이디/저장소명.git
git push -u origin main
```

### 2. GitHub Secret 등록

저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Name | Secret |
|------|--------|
| `NOTION_TOKEN` | 발급받은 Notion 토큰 |

### 3. 완료

이후 매일 오전 6시(한국시간)에 자동으로 실행됩니다.

Actions 탭 → `QT Daily Notion Sync` → **Run workflow** 버튼으로 수동 테스트도 가능합니다.

---

## 파일 구조

```
utility/
├── scrape_qt.py                    # 두란노 사이트 스크래퍼
├── qt_to_notion.py                 # Notion 저장 메인 스크립트
├── requirements.txt                # 패키지 목록
├── .env                            # 토큰 (Git 제외)
├── .gitignore
└── .github/
    └── workflows/
        └── qt_daily.yml            # GitHub Actions 스케줄
```

---

## 주의사항

- `.env` 파일은 절대 GitHub에 올리지 마세요. (`.gitignore`에 등록되어 있습니다)
- 두란노 사이트는 당일 QT만 제공하므로 당일 실행을 권장합니다.

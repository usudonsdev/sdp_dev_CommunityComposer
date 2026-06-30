# A担当: C1 UI処理部 Flask実装

このフォルダは、A担当範囲である **C1 UI処理部** だけをFlaskで実装する。

## 実装する範囲

- W1 ログイン画面
- W2 メイン画面
- W3 管理者用ログイン画面
- W4 コミュニティ作成・編集画面
- W5 コミュニティの詳細を表示する画面
- 画面側の最低限の入力チェック
- C2 認証処理部、C3 コミュニティ活動処理部へ処理を渡すための境界

## 実装しない範囲

- Google認証そのもの
- 管理者権限判定そのもの
- DB接続、DBテーブル定義
- F1ログイン情報、F2コミュニティ情報の永続化処理
- 参加申請、通知、勧誘、メンバー管理、検閲などの削除済み機能

## 起動

```powershell
cd implementation\a_ui_flask
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app wsgi run --debug
```

Google認証処理部が未接続の間に画面確認だけを行う場合は、次のURLで仮の `auth_token` をCookieに保存してから確認する。

```text
http://127.0.0.1:5000/auth/callback?auth_token=demo
```

その後、`http://127.0.0.1:5000/communities` を開く。

## C2/C3との接続

現段階では、C2/C3の仕様とDB仕様が未確定であるため、画面確認用の仮データを返す。

本接続時は以下の環境変数を設定する。

- `AUTH_GOOGLE_LOGIN_URL`
- `AUTH_ADMIN_GOOGLE_LOGIN_URL`
- `AUTH_SERVICE_BASE_URL`
- `AUTH_LOGIN_ENDPOINT`
- `AUTH_ADMIN_LOGIN_ENDPOINT`
- `AUTH_ADMIN_SECRET`
- `AUTH_MOCK_ENABLED`
- `AUTH_MOCK_USER_ID`
- `AUTH_MOCK_USER_EMAIL`
- `AUTH_MOCK_ADMIN_USER_ID`
- `AUTH_MOCK_ADMIN_EMAIL`
- `COMMUNITY_SERVICE_BASE_URL`
- `COMMUNITY_CREATOR_USER_ID`

未設定の場合、一覧・詳細は仮データで表示し、保存・削除は「C3未接続」と表示する。

## DB担当リポジトリとの接続

DB担当側のFlask APIは、コミュニティ情報を次の形式で返す。

- 一覧: `GET /communities` -> `{"communities": [...]}`
- 詳細: `GET /communities/<id>` -> `{"community": {...}}`
- 作成: `POST /communities` -> `{"community": {...}}`
- 更新: `PUT /communities/<id>` -> `{"community": {...}}`
- 削除: `DELETE /communities/<id>?auth_token=...`

C1側では、DB側の `id` を画面用の `community_id` として扱い、`image_path` を画面用の `image_url` として表示する。
作成時、DB側APIは `creator_user_id` を必要とするため、C2/DB結合前の確認では `COMMUNITY_CREATOR_USER_ID` に既存ユーザーIDを設定する。

例:

```powershell
$env:COMMUNITY_SERVICE_BASE_URL="http://127.0.0.1:5001"
$env:COMMUNITY_CREATOR_USER_ID="1"
flask --app wsgi run --debug
```

## 認証担当リポジトリとの接続

認証担当側のFlask APIは、現時点では次のエンドポイントを提供している。

- 一般ログイン: `POST /auth/login`
- 管理者ログイン: `POST /admin/auth/login`

C1側では、Google認証後の戻り先として次のURLを受け付ける。

- 一般ユーザー: `GET /auth/callback`
- 管理者: `GET /admin/auth/callback`

コールバックで `auth_token` と `email` を受け取った場合、C1は認証担当APIへ送信し、成功時に `auth_token` と `user_id` をCookieへ保存する。
保存した `user_id` は、コミュニティ作成時の `creator_user_id` としてC3/DB側へ渡す。

例:

```powershell
$env:AUTH_SERVICE_BASE_URL="http://127.0.0.1:5001"
$env:AUTH_GOOGLE_LOGIN_URL="<認証担当側の一般Google認証開始URL>"
$env:AUTH_ADMIN_GOOGLE_LOGIN_URL="<認証担当側の管理者Google認証開始URL>"
$env:AUTH_ADMIN_SECRET="admin-secret"
flask --app wsgi run --debug
```

認証担当側にGoogle認証開始用のURLがまだない場合は、画面確認用として従来どおり次のURLを使える。

```text
http://127.0.0.1:5000/auth/callback?auth_token=demo
```

## モック認証

Google認証サービスの登録が完了するまでは、C1側で認証成功扱いにするモック認証を使う。
初期設定では `AUTH_MOCK_ENABLED=1` として扱うため、ログイン画面のGoogleログインボタンを押すだけで仮の `auth_token` と `user_id` をCookieへ保存し、W2メイン画面へ遷移する。

- 一般ログイン: `/login/google` -> `/auth/callback?auth_token=mock-user-token&user_id=1`
- 管理者ログイン: `/admin/login/google` -> `/admin/auth/callback?auth_token=mock-admin-token&user_id=2`

栗本さんのC3コミュニティ活動処理部は、編集・削除権限の判定で `auth_token` からユーザーを参照する。
そのため `AUTH_SERVICE_BASE_URL` が未設定で `COMMUNITY_SERVICE_BASE_URL` が設定されている場合、モック認証でも `COMMUNITY_SERVICE_BASE_URL` 側の `/auth/login` を呼び、仮ユーザーと `auth_token` を登録する。
これにより、Google OAuth未登録の段階でも、モックログイン後に一覧・詳細・作成・編集・削除の結合確認を進められる。

本番のGoogle認証と接続する場合は、次のようにモック認証を無効にする。

```powershell
$env:AUTH_MOCK_ENABLED="0"
$env:AUTH_GOOGLE_LOGIN_URL="<認証担当側の一般Google認証開始URL>"
$env:AUTH_ADMIN_GOOGLE_LOGIN_URL="<認証担当側の管理者Google認証開始URL>"
flask --app wsgi run --debug
```

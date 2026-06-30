# 次のCodexへ貼る引き継ぎプロンプト

あなたは、大学のソフトウェア開発演習で作成している「芝浦工大生向けコミュニティ掲示板型Webアプリ」の実装を支援するエージェントです。

このフォルダ内のファイルを読み込んで、前回作業から自然に引き継いでください。

## まず読むファイル

1. `docs/要求仕様書_整合確認版.docx`
2. `docs/4班外部設計書_整合確認版.docx`
3. `docs/内部設計書_完成版_整合確認版.docx`
4. `implementation/a_ui_flask/README.md`
5. `implementation/a_ui_flask/consistency_check.md`
6. `implementation/a_ui_flask/app/c1_ui/routes.py`
7. `implementation/a_ui_flask/app/c1_ui/models.py`
8. `implementation/a_ui_flask/app/c1_ui/service_clients.py`

## 現在の決定事項

- 実装フレームワークはFlaskである。FastAPIではない。
- 私の担当はAである。
- A担当はC1 UI処理部である。
- C1 UI処理部は、W1〜W5の画面表示、画面遷移、入力受付、最低限の画面側バリデーションを担当する。
- C2認証処理部、C3コミュニティ活動処理部、DB処理はA担当外である。
- ただし、C1からC2/C3へ処理を渡すための境界は用意してよい。

## システム概要

本システムは、芝浦工大生向けのコミュニティ掲示板型Webアプリである。
ユーザはコミュニティ情報を閲覧し、コミュニティ設立希望者はコミュニティ名、カテゴリ、概要、コミュニティ内容、連絡先、画像などを掲載する。
参加連絡やメンバー間のやり取りは外部ツールで行う。
本システム内では参加申請、承認、メンバー管理、通知、勧誘、検閲は行わない。

## 認証方針

- 大学Googleアカウントを用いたGoogle認証を行う。
- アプリ側ではパスワードを入力・保持・処理しない。
- Google認証後、C2認証処理部が `@shibaura-it.ac.jp` のアカウントであることを確認する想定である。
- 認証成功後、C2が発行する `auth_token` をC1がCookieとして受け取り、W2以降の画面表示に用いる。
- 現在のFlask実装では `/auth/callback?auth_token=demo` を使うと、画面確認用の仮トークンを保存できる。

## 現在のFlask実装

実装場所は `implementation/a_ui_flask/` である。

主なルート:

- `GET /login` : W1 ログイン画面
- `GET /login/google` : 一般ユーザ用Google認証開始
- `GET /admin/login` : W3 管理者用ログイン画面
- `GET /admin/login/google` : 管理者用Google認証開始
- `GET /auth/callback` : C2から受け取った `auth_token` をCookieに保存
- `GET /communities` : W2 メイン画面
- `GET /communities/new` : W4 新規記入フォーム
- `POST /communities` : W4 新規記入内容保存要求
- `GET /communities/<community_id>` : W5 詳細画面
- `GET /communities/<community_id>/edit` : W4 編集フォーム
- `POST /communities/<community_id>` : W4 編集内容保存要求
- `POST /communities/<community_id>/delete` : W5 削除要求

現段階ではDB仕様が未定であるため、一覧・詳細は画面確認用の仮データを返す。
保存・削除はC3未接続メッセージを返す。

## UI方針

`ui_images/` にW1〜W5の画面イメージがある。
白基調で、青・赤・橙・黄をアクセントにしたデザインである。
FlaskのCSSもこのデザイン案に寄せている。

## 絶対に追加しない機能

以下は削除済み機能なので、コードにも画面にも追加しないこと。

- 参加申請
- 参加希望送信
- 承認
- 勧誘
- 通知
- プロフィール
- 検閲
- 自動削除
- 削除除外
- コミュニティメンバー管理

## 次にやってほしいこと

1. `implementation/a_ui_flask` を確認する。
2. Flaskの依存関係を入れて起動できるか確認する。
3. W1〜W5が設計書と矛盾しないか、ブラウザ表示で確認する。
4. 表示崩れや足りない画面項目があれば、C1 UI処理部の範囲内で修正する。
5. C2/C3/DBの本体実装は、担当外なので勝手に作らない。

## 起動手順

```powershell
cd implementation\a_ui_flask
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app wsgi run --debug
```

画面確認用:

```text
http://127.0.0.1:5000/auth/callback?auth_token=demo
http://127.0.0.1:5000/communities
```

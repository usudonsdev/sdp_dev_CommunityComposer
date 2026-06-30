# Codex引き継ぎフォルダ

このフォルダは、デスクトップ版Codexへ作業を引き継ぐためのまとめである。

## 中身

- `docs/`
  - `内部設計書_完成版_整合確認版.docx`
  - `要求仕様書_整合確認版.docx`
  - `4班外部設計書_整合確認版.docx`
- `implementation/a_ui_flask/`
  - A担当分のFlask実装
  - C1 UI処理部のみ
  - C2/C3/DB本体は未実装
- `ui_images/`
  - W1〜W5の最終画面イメージ
  - 案1ベースのメイン画面イメージ
- `handoff_prompt.md`
  - 次のCodexに貼るための引き継ぎプロンプト

## 現在の実装方針

- 実装フレームワークはFlaskである。
- A担当はC1 UI処理部である。
- Google認証そのもの、管理者権限判定、DB処理、C3コミュニティ活動処理部本体はA担当外である。
- C1は画面表示、入力受付、最低限の入力チェック、C2/C3へ渡す境界までを担当する。

## Flask実装の起動

```powershell
cd implementation\a_ui_flask
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app wsgi run --debug
```

C2認証処理部が未接続の間に画面確認をする場合は、以下で仮の `auth_token` を保存する。

```text
http://127.0.0.1:5000/auth/callback?auth_token=demo
```

その後、以下を開く。

```text
http://127.0.0.1:5000/communities
```

## 注意

- 旧FastAPI版は元ワークスペースに残っているが、現在の方針では使用しない。
- この引き継ぎフォルダ内にはFlask版だけを入れている。
- 削除済み機能である参加申請、通知、勧誘、プロフィール、メンバー管理、検閲などは実装しない。

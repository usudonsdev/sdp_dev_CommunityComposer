# 開発・デプロイ手順

本プロジェクトは Flask を用いて実装し、ローカル環境では Docker Compose を
標準の開発環境として利用する。これにより、チームメンバーごとの Python や
依存関係の差を減らす。

VM には `docs/vm_manual.md` の手順で Ubuntu Server を用意し、Docker を使って
同じ環境でデプロイする。

## 1. 開発方針

- チーム開発では Git を用いてソースコードを管理する。
- 実装前に `main` ブランチを最新化する。
- 作業は機能ごとのブランチで行う。
- コーディング規約は `docs/CodingStandards/coding_standard.md` に従う。
- 標準のローカル実行方法は Docker Compose とする。
- ローカルで起動確認とテストを行ってから共有ブランチへ反映する。

ブランチ名の例:

```bash
feature/community-list
feature/login
fix/validation-error
```

## 2. 想定するアプリケーション構成

Flask アプリケーションは、以下のような構成を基本とする。

```text
app/
  __init__.py
  routes/
  models/
  services/
  validators/
  templates/
  static/
tests/
Dockerfile
compose.yaml
requirements.txt
run.py
```

各ディレクトリの役割は以下のとおり。

| パス | 役割 |
| :--- | :--- |
| `app/routes/` | 画面表示やAPIのルーティング |
| `app/models/` | DBテーブルに対応するモデル |
| `app/services/` | コミュニティ作成・編集などの業務処理 |
| `app/validators/` | 入力値チェック |
| `app/templates/` | HTMLテンプレート |
| `app/static/` | CSS、JavaScript、画像 |
| `tests/` | テストコード |
| `Dockerfile` | Flask 実行用コンテナの定義 |
| `compose.yaml` | ローカル開発用コンテナの起動設定 |
| `requirements.txt` | Python の依存関係 |

## 3. ローカル環境構築

### 3.1 必要なもの

**チームメンバーは、原則として以下だけを用意すれば開発に着手できる。**

- Git
- Docker Desktop

Docker Desktop を起動してから、Docker が使えるか確認する。

```bash
docker --version
docker compose version
```

### 3.2 初回セットアップ

リポジトリを取得する。

```bash
git clone <repository-url>
cd sdp_dev_CommunityComposer
```

コンテナをビルドする。

```bash
docker compose build
```

## 4. ローカル起動

Flask アプリを起動する。

```bash
docker compose up
```

バックグラウンドで起動する場合:

```bash
docker compose up -d
```

起動後、ブラウザで以下にアクセスして確認する。

```text
http://127.0.0.1:8000
```

停止する場合:

```bash
docker compose down
```

## 5. 依存関係を追加する場合

新しいライブラリを使う場合は `requirements.txt` に追記し、コンテナを再ビルドする。

```bash
docker compose build
```

例:

```text
Flask-WTF
python-dotenv
```

各メンバーは `docker compose build` を実行すれば同じ依存関係を使える。

## 6. ローカルテスト

テストは Docker コンテナ内で `pytest` を実行する。

```bash
docker compose run --rm web python -m pytest
```

最低限、以下を確認してから共有ブランチへ反映する。

- アプリがローカルで起動すること
- ログイン画面、一覧画面、詳細画面など主要画面が表示できること
- コミュニティ情報の作成・編集・削除が想定通り動くこと
- 入力エラー時に適切なエラーメッセージが表示されること
- `python -m pytest` が失敗しないこと

## 7. Docker を使わない場合の補助手順

Docker が使えない環境では、Python の仮想環境を使って実行する。
ただし、チームの標準手順は Docker Compose とする。

Windows:

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
flask --app run.py run
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app run.py run
```

## 8. VM へのデプロイ準備

VM は `docs/vm_manual.md` に従って Ubuntu Server を用意する。

SSH 接続の例:

```bash
ssh username@172.21.33.X
```

`172.21.33.X` の `X` はチームの VM に割り当てられた番号に置き換える。

VM 側で Docker をインストールする。

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
```

`usermod` の反映には再ログインが必要になる。

## 9. VM へのデプロイ手順

### 9.1 ソースコードの取得

VM 上でリポジトリを取得する。

```bash
git clone <repository-url>
cd sdp_dev_CommunityComposer
```

すでに取得済みの場合:

```bash
git pull
```

### 9.2 コンテナのビルドと起動

```bash
docker compose build
docker compose up -d
```

ブラウザから以下にアクセスして確認する。

```text
http://172.21.33.X:8000
```

ログを確認する場合:

```bash
docker compose logs -f
```

停止する場合:

```bash
docker compose down
```

## 10. 本番用設定

秘密情報を扱う場合は、ソースコードに直接書かず、環境変数で管理する。
必要に応じて `.env` を作成し、Git にはコミットしない。

`.env` の例:

```text
FLASK_ENV=production
SECRET_KEY=change-me
DATABASE_URL=sqlite:///instance/app.sqlite3
```

本番に近い起動を行う場合は、`gunicorn` を利用する。

```bash
docker compose run --rm --service-ports web gunicorn -b 0.0.0.0:5000 run:app
```

ただし、初期段階では `docker compose up -d` で動作確認を優先する。

## 11. 運用時の注意

- VM を使わないときは `docs/vm_manual.md` に従ってシャットダウンする。
- デプロイ前に必ずローカルテストを実行する。
- VM 上で直接コードを編集した場合は、Git に反映漏れがないか確認する。
- DBファイルやアップロード画像など、実行時に生成されるファイルの扱いをチームで決めておく。
- パスワード、APIキー、トークンなどはリポジトリにコミットしない。
- `requirements.txt` を変更した場合は、全員が `docker compose build` を実行する。

## 12. 推奨する開発サイクル

1. `main` を最新化する。
2. 機能ごとのブランチを作成する。
3. Docker Compose でローカル起動する。
4. 実装する。
5. `docker compose run --rm web python -m pytest` と画面操作で確認する。
6. 変更内容を共有する。
7. VM に反映して動作確認する。

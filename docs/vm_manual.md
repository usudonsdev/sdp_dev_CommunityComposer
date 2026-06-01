
# VM の使い方（初期設定）

以下は Proxmox VE 上の VM（Ubuntu Server）の基本的な起動・インストール手順と利用上の注意です。

## 1. Web Console にアクセス

- 学内ネットワークから Proxmox の Web Console にアクセスしてください。
- 学外から接続する場合は VPN 経由で接続してください。

## 2. チームアカウントでログイン

- チームリーダーから Slack の DM で受け取った `username` と `password` を使ってログインします。
- Realm は「Proxmox VE authentication server」を選択してください。

## 3. VM を起動する

- 左側メニューの `Datacenter/fukuda/teamXX` にある対象の VM を選択します。
- `Console` タブの「Start Now」をクリックして VM を起動します。

## 4. Ubuntu Server をインストールする

インストールは画面の指示に従って進めてください。主な手順は以下のとおりです。

1. 「Try or Install Ubuntu Server」を選択します。
2. OS の言語を選択します。
3. キーボードレイアウトを選択します（日本語配列を使う場合は `Japanese` を選択）。
4. 構成は「Ubuntu Server」と「Search for third-party drivers」を選択します。
5. ネットワーク設定（例）:

```text
Subnet:        172.21.33.0/24
Address:       172.21.33.X   # X は VM の ID
Gateway:       172.21.33.1
Name servers:  202.18.120.6
Search domains: なし
```

- `ens18` -> `Edit IPv4` に進み、`IPv4 Method` を `Manual` に変更して上記の値を設定してください。
- Proxy は空欄のまま進めて問題ありません。
- インストールイメージの更新は任意ですが、手順 4-5 を間違えるとミラー更新に失敗するのでネットワーク設定を確認してください。

6. Storage configuration はデフォルトで問題ありません。
7. Ubuntu のユーザー名とパスワードを設定します。
8. 必要に応じて SSH サーバーをインストールしてください（デフォルトではインストールされません）。

インストールが完了したら「Reboot Now」を選択して再起動します。

## 5. 起動後のトラブルシュート

- VM が起動しない場合:
	- `Console` タブで Enter キー等を押してみる。
	- `Shutdown` プルダウンから `Stop` を選択して一旦停止し、再度起動する。

## 6. Ubuntu にログイン

- インストール時に設定した `username` と `password` でログインしてください。

## 7. SSH で接続する

- Proxmox の Web Console は使い勝手が悪いため、個人の PC から SSH クライアントで接続することを推奨します。

例:

```bash
ssh username@172.21.33.X
```

- SSH 越しに `root` 権限を扱いたい場合は `/etc/ssh/sshd_config` を適切に設定してください。

## 8. 利用上の注意

- VM を使わないときは必ずシャットダウンしてください。
- 性能やディスク容量が不足している場合は TA に相談してください（ある程度は調整可能です）。

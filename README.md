# NuxtImageBoard Docker
Docker-composeを用いてサイトを稼働させるセットアップ

### 注意
- 他のプロジェクトから一部機能を削除して切り抜いたものです
- セキュリティ面やバグ等不完全な点が多いため現段階での利用はおすすめしません

### デモ
- [こちらからどうぞ](https://nboard.domao.site)
- ID: demouser
- PW: demouser
- (開発中のため不安定です)

## 動作環境
- Docker Desktop for Windows
- docker-compose (Debian VPS)

## 要求ソフトウェア
- Python3.8
  - セットアップの実行に必要
- mysql-connector-python
  - Windowsの場合 pip3でインストール
  - Linuxの場合apt等でインストール

## セットアップ手順
 - リポジトリをクローン
   - git clone https://github.com/nuxt-image-board/docker
   - cd docker
 - 環境変数を用意
   - cp .env_example .env
     - .envをコピー
   - nano .env
     - .envを編集
       - サイト名等を変更
          - SITE_NAME等
       - 公開ドメイン等を変更
          - エンドポイント/に注意
       - SALTに使う文字列を変更
          - SALT_JWT等
       - データベースのパスを変更
          - DB_USER DB_PASS等
       - サイトで使用するポートの変更(任意)
          - PORT_API等
       - ボリュームパスを変更(任意)
          - VOLUME_API等
 - ビルドする
   - docker-compose build
     - イメージ生成時にgit cloneが走ります
 - 起動させる
   - docker-compose up
     - 数分待つ
       - DBの初期化に時間がかかるため
     - toymoneyコンテナが起動していない場合
       - DB起動後に再起動する
 - セットアップを行う
   - pip3 install -r requirements.txt
     - itsdangerousのバージョンに注意
   - データベース作成
     - python setup.py maindb:create
     - python setup.py subdb:create
   - 管理ユーザー作成
     - python setup.py subadmin:create
       - ユーザーID/ユーザー名/パスワードを入力
       - 表示されるAPIキーをコピー
     - python setup.py mainadmin:create
       - toyapi_key に 先程のAPIキーを入力
       - 表示されるAPIキーをコピー
   - 招待コード作成(任意)
     - python setup.py invite:create
       - 招待者のID/任意の文字列/作成数を入力
  - 環境変数を変更
    - TOYMONEY_TOKEN
      - subadminで作成したAPIキーを入力
    - API_SSR_TOKEN
      - mainadminで作成したAPIキーを入力
  - フォルダ作成
    - api_dataフォルダ内に下記フォルダ作成
      - temp
      - illusts
       - orig
       - large
       - small
       - thumb
  - インストール完了
  　- 招待コードでアカウント作成
    - または管理ユーザーでログイン

### デフォルトポート
- Web
  - http://localhost:3000
- API
  - http://localhost:5000
- ToyMoney
  - http://localhost:7000
- APIデータベース
  - http://localhost:3306
- ToyMoneyデータベース
  - http://localhost:3307
- Redis
  - http://localhost:6379
- Adminer
  - http://localhost:8080

### ノート
 - なぜDockerImageを使わないの?
   - Nuxt.jsの環境変数はビルド時のもので固定化されてしまうため
     - (今後対応予定)
 - 作成した管理ユーザーでログインできない?
   - セットアップで利用したitsdangerousのバージョンがAPI/TOYMONEYと異なる
 - RaspberryPi3Bで動きますか?
   - 初期は動作することを念頭に置いていましたが現段階では未検証です

# lgtm-cat-processor
S3にアップロードされた画像からLGTM画像を作成するLamnda関数

# デプロイ

デプロイ先の環境は、ステージングと本番の2つが存在します。

GitHub Actionsワークフロー内で自動的に実行されます。

実行タイミングは以下の通りです。

- ステージング
    - mainブランチへのPRのマージ時に実行
- 本番
    - セマンティックバージョニングに基づいたリリースタグ（例：v1.0.0）が追加された時に実行

# font
- Google Fonts を利用

LGTMテキストの追加に利用しています。

https://fonts.google.com/specimen/M+PLUS+Rounded+1c?preview.text_type=custom&sidebar.open=true&selection.family=Truculenta:wght@100#pairings


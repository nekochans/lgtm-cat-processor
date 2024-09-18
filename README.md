# lgtm-cat-processor
S3にアップロードされた画像からLGTM画像を作成するLamnda関数

# デプロイ

デプロイ先の環境は、ステージングと本番の2つが存在します。

デプロイには以下の2つの手順が必要になります。

1. DockerイメージをECRにpush
2. Lambda関数の更新

それぞれの詳細手順は下記の通りです。

## 1. DockerイメージをECRにpush

GitHub Actionsワークフロー内で自動的に実行されます。

実行タイミングは以下の通りです。

- ステージング
    - mainブランチへのPRのマージ時に実行
- 本番
    - セマンティックバージョニングに基づいたリリースタグ（例：v1.0.0）が追加された時に実行

## 2. Lambda関数の更新

以下のコマンドを実行して、Lambda関数を更新してください。

`image_uri`にはECRにpushされたイメージのURIを指定してください。


-  ステージング
```
# Lambda関数の更新
aws lambda update-function-code --function-name stg-lgtm-image-processor --image-uri { image_uri }

# Lambda関数の更新が完了するまで待機
aws lambda wait function-updated --function-name stg-lgtm-image-processor
```

- 本番
```
# Lambda関数の更新
aws lambda update-function-code --function-name prod-lgtm-image-processor --image-uri { image_uri }

# Lambda関数の更新が完了するまで待機
aws lambda wait function-updated --function-name prod-lgtm-image-processor
```

# font
- Google Fonts を利用

LGTMテキストの追加に利用しています。

https://fonts.google.com/specimen/M+PLUS+Rounded+1c?preview.text_type=custom&sidebar.open=true&selection.family=Truculenta:wght@100#pairings


# 点検アプリ 差分一式（体感速度改善）

作成日: 2026-09-10  
対象: 設備一覧・カレンダーの読み込み高速化（N+1 API 解消）

## 配置先

このフォルダの階層を、サーバー上の `project_root` に上書きコピーしてください。

```
project_root/
├── backend/
│   └── routers/
│       ├── inspection_items.py    ← 更新
│       └── inspection_results.py  ← 更新
└── frontend/
    ├── js/
    │   └── api.js                 ← 更新
    └── pages/
        ├── calendar.html          ← 更新
        └── equipments.html        ← 更新
```

## 変更内容（概要）

- 工程単位の一括取得 API を追加
  - `GET /inspection_items/by_process?process_id=`
  - `GET /inspection_results/by_process?process_id=&from=&to=`
- カレンダー／設備一覧が設備台数ぶん API を連打しないように変更
- カレンダーは表示月の結果だけ取得（全履歴を取らない）
- `api.js`: ポート 5500 のときだけ API を `:8000` へ。それ以外（画面+API同居）は同一オリジン

表示ロジック（〇△×、「本日は使用しない」など）は変更していません。

## 反映手順

1. 上記 5 ファイルをサーバーへ配置（上書き）
2. FastAPI（API :8000）を再起動  
   例: `restart-services.bat` を管理者実行、または `FastAPIService` を再起動
3. ブラウザをハードリロード（Ctrl+F5）

Frontend（:5500）の再起動は必須ではありません（静的ファイルの差し替えのみ）。

## 動作確認

1. カレンダーを開く → 開発者ツール Network で  
   `inspection_items/by_process` と `inspection_results/by_process` が各 1 回程度であること  
   （設備ごとの `inspection_items/?equipment_id=` / `inspection_results/?equipment_id=` 連打がないこと）
2. 設備一覧（日付付き）でも結果取得が 1 リクエストになっていること
3. 〇△×／スキップ表示が従来どおりであること

## 注意

- DB マイグレーション不要（既存テーブルのまま）
- 既存の `GET /inspection_results/?equipment_id=` 等は残しています

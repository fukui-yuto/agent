---
name: commit
description: ステージ済みの変更を分析して適切なgitコミットを作成する
---
現在のgitの状態を確認して、ステージ済みの変更に対して適切なコミットメッセージを作成し、コミットしてください。

手順:
1. `git diff --staged` でステージ済みの変更内容を確認する
2. 変更の種類（新機能・バグ修正・リファクタリング・ドキュメント等）を判断する
3. Conventional Commits形式でコミットメッセージを作成する（例: `feat: add user authentication`）
4. `git commit -m "..."` でコミットを実行する

ステージされた変更がない場合は、`git status` で確認してユーザーに伝えてください。

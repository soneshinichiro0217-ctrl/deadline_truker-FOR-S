# SHUKATSU TRACKER — 28卒 / SIer・IT志望

28卒向けの**就活締切・企業待遇ダッシュボード**。シングルページの静的サイト。データベースやAPIキーは不要です。

## 用意した機能

- 選考／インターンの締切と残り日数、企業名検索、カレンダー、応募ステータス、ICS出力、JSONバックアップ
- SIer・ITコンサルを初期表示の重点業界として、通信・メーカーIT・Web・SaaSへ切り替え
- OpenWork「待遇面の満足度」**3.0以上**、社員口コミの**平均年収600万円以上**を基本条件にする企業カード
- 残業時間（データのある企業）、平均年収、待遇満足度の**基準を変更できるフィルター**
- データのない企業を「合格」として扱わない。CTCなど検証保留の企業は確認待ち
- 公式採用ページの公開HTMLから応募締切に見える記述を収集するスクリプト
- GitHub Actionsの定期実行とGitHub Pagesによる固定URL公開

## URLだけで使う（GitHub Pages）

アカウント所有者が1回だけ次の公開設定をする必要があります。

1. [GitHub](https://github.com/)で新規の**Public Repository**（例: `shukatsu-tracker`）を作る。ブランチ名は `main`。
2. このZIPの**中身すべてをリポジトリ直下に**アップロードする（`.github/workflows/update-and-deploy.yml` を含める。GitHubのブラウザーUIでフォルダごとアップロードできない場合はローカルGit経由）。
3. **Settings → Pages → Build and deployment → Source: GitHub Actions** を選択する。
4. **Actions** タブで `Collect 28卒 deadlines and publish site` を選び、`Run workflow` を実行する。`main` への push でも実行される。
5. **Settings → Pages** に発行されたURLへアクセスする。一般に `https://<ユーザー名>.github.io/<リポジトリ名>/` という形（実URLはGitHub側で確定）。以後はそのURLだけでサイトにアクセスできる。

GitHub Actionsは**毎日2回（09:15／21:15 JST）**に収集と公開を行う設定です（GitHub側の負荷や設定により遅延・欠落することがあります）。スケジュールが無効化された場合はActionsで再有効化して手動実行してください。GitHubの公開リポジトリでは60日間アクティビティがないとスケジュールが停止し得ます。

**Vercelを使う場合**：同じGitHubリポジトリをVercelに連携できます。Actionsが生成JSONを`main`にコミットできればVercelも更新されます（リポジトリの保護設定等でコミットできない場合はGitHub Pagesの方を使用）。

**重要**：ZIPを手元で開くだけ、またはNetlify DropにZIPを一度置くだけでは1日2回の自動収集は開始しません。GitHub Actionsでの実行設定が必要です。

## データ品質について

- 自動収集は、`data/sources.json` に列挙した **12件の公開公式ページ**のみを対象とするベストエフォート方式です。企業のマイページ、ログイン画面、動的JSサイト、無関係なページ、robots.txtで拒否されたページは対象外です。
- `scripts/update_deadlines.py` は応募締切の候補を文字列の近接関係から機械抽出します。**候補はすべて「自動収集・要確認」と表示**します。開催日、誤った学年、ページ内の古い情報が混ざる可能性があります。公式マイページや採用担当からの案内を最終的な根拠にしてください。
- 初期登録された20件は**2026年10月22日**の調査情報で、別途に自動確認されたことを意味しません。
- OpenWorkの数値は公開比較ページの確認可能なスナップショットです。掲載元の比較ページから確認できるよう各社カードに出典リンクを付けています。スコアと年収は**現職・元職の社員口コミ平均**であり、初任給でも30歳平均年収でもありません。
- **東京固定・異動可能性・リモート回数はこのバージョンでは職種別に検証していないため未確認**と表示しています。「高待遇」と「ホワイト企業」を同一視しないでください。
- 手動入力した応募履歴とお気に入りは**ブラウザー内のLocalStorage**で保持します。別端末間で同期しません。公開されたGitHubリポジトリにはユーザーの入力情報は送信しません。

## 収集対象の追加

`data/sources.json` の`"sources"`配列に以下の形式で追加してください。

```json
{"company":"企業名","industry":"SIer","url":"https://example.com/public-28grad-recruitment-page"}
```

個人の認証を必要とするページ、禁止されたスクレイピング、ロボット防御の回避を行わないでください。収集対象を増やしても「全募集の網羅」にはなりません。

```sh
pip install -r requirements.txt
python scripts/update_deadlines.py
python -m unittest discover -s scripts -p 'test_*.py'
node scripts/test_frontend.js
```

## データの場所

- `index.html` — フロントエンド本体
- `data/company_profiles.json` — 待遇データの原本（同じスナップショットをHTML本体にも埋め込み）
- `data/sources.json` — 機械チェック対象の公式ページ
- `data/deadlines.json` — GitHub Actions実行時に1日2回更新されるデータ
- `scripts/update_deadlines.py` — 自動収集器
- `.github/workflows/update-and-deploy.yml` — 定期更新・公開設定

注：会社プロフィールを改訂するときは `data/company_profiles.json` と `index.html` 内の `COMPANY_PROFILES` を一致させてください。手動編集者向けの構成で、現在両者の同期ビルドは用意していません。
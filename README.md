# 保田の家 空室カレンダー

AirbnbのiCalフィードから空室カレンダーのHTMLを生成し、GitHub Pagesで配信する。
hota.life（Wix）にiframeで埋め込んで使う。

- 公開URL: https://chiikys-toshi.github.io/hota-calendar/
- 更新頻度: 毎時（GitHub Actions）
- 生成スクリプト: [tools/build_calendar.py](tools/build_calendar.py)

## なぜ作ったか

hota.lifeの予約導線はGoogleフォームのみで、サイト上に空室状況が出ていなかった。
そのため既に予約済み・ブロック済みの日程にリクエストが届き、お断りする事故が
2026年8月に2件続いた（8/3 大山様・8/14 森田様）。サイト上で空室が分かる状態にするのが目的。

## セキュリティ上の約束

AirbnbのiCalフィードには**予約詳細URLと予約者電話番号の下4桁が含まれる**。

- iCalのURL自体もトークン付きの秘密情報。GitHub Secrets `HOTA_ICAL_URL` にのみ置く
- スクリプトが出力HTMLに書き出すのは「その夜が空いているか」だけ。
  予約者情報・予約URL・ブロック理由は一切含めない
- 埋め込みページのJavaScriptからiCalを直接読みに行かない（読めば誰でも中身を見られるため）

## 表示ルール

| 表示 | 意味 |
|---|---|
| ○ | 空室 |
| × | 満室（予約済み、または手動ブロック） |

Airbnbのカレンダーで押さえられている日はそのまま×にする、という単純なルール。
特別扱いはしない。

○×は「その日に宿泊する夜」の空き。iCalのDTENDは排他的なので、チェックアウトのみの日は空室になる。

なおAirbnbは「予約受付期間の上限」より先の日程も1本の長大なブロックとして書き出す
（2026年8月時点では 2026-12-01〜2027-08-15）。これも×として表示される。
先の日程を空室として見せたい場合は、Airbnb側の予約受付期間を延ばす。

## 前提

Airbnbのカレンダーが全チャネル（Airbnb・ACO・直予約）の予約を集約した「正」であること。
ここが崩れると、このカレンダーは正しくても重複予約が起きる。

## ローカルで確認する

```bash
HOTA_ICAL_URL='https://www.airbnb.jp/calendar/ical/49803948.ics?t=...' python3 tools/build_calendar.py
open docs/index.html
```

## 注意

GitHub Actionsのスケジュール実行は、リポジトリが60日間無活動だと自動で停止する。
長く触っていない場合はActionsタブで動いているか確認する。

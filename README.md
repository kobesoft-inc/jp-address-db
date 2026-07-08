# jp-address-db

デジタル庁 [アドレス・ベース・レジストリ](https://registry.digital.go.jp/) の町字マスター（`mt_town_all.csv`）を正規化した SQLite データベースを毎月自動ビルド・リリースします。

## ダウンロード

[Releases](../../releases/latest) から最新版をダウンロードできます。

```bash
# gzip 版（推奨）
curl -fSL -o address.db.gz \
  https://github.com/kobesoft-inc/jp-address-db/releases/latest/download/address.db.gz
gunzip address.db.gz
```

## スキーマ

```
prefectures    都道府県マスター          (47 件)
municipalities 市区町村マスター          (~1,900 件)
wards          区マスター（政令指定都市） (~171 件)
machiaza       町字マスター              (~727,000 件)
metadata       ビルド情報
v_address      全結合ビュー（検索用）
```

### prefectures

| 列 | 型 | 説明 |
|---|---|---|
| pref_code | TEXT PK | 都道府県コード（2桁） |
| pref | TEXT | 都道府県名 |
| pref_kana | TEXT | カナ |
| pref_roma | TEXT | ローマ字 |

### municipalities

| 列 | 型 | 説明 |
|---|---|---|
| lg_code | TEXT PK | 全国地方公共団体コード（6桁） |
| pref_code | TEXT FK | 都道府県コード |
| county | TEXT | 郡名 |
| city | TEXT | 市区町村名 |
| … | | kana / roma 列あり |

### wards

| 列 | 型 | 説明 |
|---|---|---|
| lg_code | TEXT PK/FK | 市コード |
| ward | TEXT PK | 区名 |
| … | | kana / roma 列あり |

### machiaza

| 列 | 型 | 説明 |
|---|---|---|
| lg_code | TEXT PK/FK | 市区町村コード |
| machiaza_id | TEXT PK | 町字ID（7桁） |
| machiaza_type | INTEGER | 町字区分 |
| ward | TEXT | 区名 |
| oaza_cho | TEXT | 大字・町名 |
| chome | TEXT | 丁目 |
| chome_number | INTEGER | 丁目数値 |
| koaza | TEXT | 小字名 |
| post_code | TEXT | 郵便番号 |
| rsdt_addr_flg | INTEGER | 住居表示フラグ |
| status_flg | INTEGER | 状態フラグ |
| efct_date | TEXT | 効力発生日 |
| ablt_date | TEXT | 廃止日 |
| … | | その他フラグ列 |

## 使用例

```sql
-- 郵便番号で検索
SELECT pref, city, oaza_cho, chome, post_code
FROM v_address
WHERE post_code = '1000001';

-- 市区町村の全町字を取得
SELECT * FROM v_address
WHERE city = '千代田区'
ORDER BY machiaza_id;

-- 都道府県ごとの町字数
SELECT p.pref, COUNT(*) AS cnt
FROM machiaza mz
JOIN municipalities m USING (lg_code)
JOIN prefectures p USING (pref_code)
GROUP BY p.pref_code
ORDER BY cnt DESC;
```

## ビルド

手動でローカルビルドする場合：

```bash
# ソースCSVをダウンロード
curl -fSL -o mt_town_all.csv.zip \
  https://catalog.registries.digital.go.jp/rsc/address/mt_town_all.csv.zip
unzip mt_town_all.csv.zip

# SQLiteデータベースを生成
python3 scripts/build.py mt_town_all.csv address.db
```

## 更新スケジュール

毎月1日に GitHub Actions が自動実行し、最新のソースデータでリビルド・リリースします。  
手動実行は Actions タブの **Build and Release** → **Run workflow** から行えます。

## ライセンス

ソースデータ: [デジタル庁 アドレス・ベース・レジストリ利用規約](https://registry.digital.go.jp/terms)  
本リポジトリのスクリプト: MIT

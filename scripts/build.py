#!/usr/bin/env python3
"""mt_town_all.csv を正規化して SQLite データベースに変換する"""

import csv
import sqlite3
import sys
import os
from pathlib import Path


DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prefectures (
    pref_code TEXT PRIMARY KEY,
    pref      TEXT NOT NULL,
    pref_kana TEXT NOT NULL,
    pref_roma TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS municipalities (
    lg_code     TEXT PRIMARY KEY,
    pref_code   TEXT NOT NULL REFERENCES prefectures(pref_code),
    county      TEXT,
    county_kana TEXT,
    county_roma TEXT,
    city        TEXT NOT NULL,
    city_kana   TEXT NOT NULL,
    city_roma   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wards (
    lg_code   TEXT NOT NULL REFERENCES municipalities(lg_code),
    ward      TEXT NOT NULL,
    ward_kana TEXT NOT NULL,
    ward_roma TEXT NOT NULL,
    PRIMARY KEY (lg_code, ward)
);

CREATE TABLE IF NOT EXISTS machiaza (
    lg_code             TEXT    NOT NULL REFERENCES municipalities(lg_code),
    machiaza_id         TEXT    NOT NULL,
    machiaza_type       INTEGER NOT NULL,
    ward                TEXT,
    oaza_cho            TEXT,
    oaza_cho_kana       TEXT,
    oaza_cho_roma       TEXT,
    chome               TEXT,
    chome_kana          TEXT,
    chome_number        INTEGER,
    koaza               TEXT,
    koaza_kana          TEXT,
    koaza_roma          TEXT,
    machiaza_dist       TEXT,
    rsdt_addr_flg       INTEGER,
    rsdt_addr_mtd_code  INTEGER,
    oaza_cho_aka_flg    INTEGER,
    koaza_aka_code      INTEGER,
    oaza_cho_gsi_uncmn  TEXT,
    koaza_gsi_uncmn     TEXT,
    status_flg          INTEGER,
    wake_num_flg        INTEGER,
    efct_date           TEXT,
    ablt_date           TEXT,
    src_code            INTEGER,
    post_code           TEXT,
    remarks             TEXT,
    PRIMARY KEY (lg_code, machiaza_id)
);

CREATE INDEX IF NOT EXISTS idx_machiaza_post_code  ON machiaza (post_code);
CREATE INDEX IF NOT EXISTS idx_machiaza_oaza_cho   ON machiaza (lg_code, ward, oaza_cho);
CREATE INDEX IF NOT EXISTS idx_municipalities_city ON municipalities (city);
CREATE INDEX IF NOT EXISTS idx_prefectures_pref    ON prefectures (pref);

CREATE VIEW IF NOT EXISTS v_address AS
SELECT
    p.pref_code,
    p.pref,
    p.pref_kana,
    p.pref_roma,
    m.lg_code,
    m.county,
    m.county_kana,
    m.county_roma,
    m.city,
    m.city_kana,
    m.city_roma,
    mz.ward,
    mz.oaza_cho,
    mz.oaza_cho_kana,
    mz.oaza_cho_roma,
    mz.chome,
    mz.chome_kana,
    mz.chome_number,
    mz.koaza,
    mz.koaza_kana,
    mz.koaza_roma,
    mz.machiaza_id,
    mz.machiaza_type,
    mz.post_code,
    mz.rsdt_addr_flg,
    mz.status_flg,
    mz.efct_date,
    mz.ablt_date
FROM machiaza mz
JOIN municipalities m USING (lg_code)
JOIN prefectures   p ON p.pref_code = m.pref_code;
"""


def int_or_none(v: str):
    return int(v) if v else None


def build(csv_path: str, db_path: str, source_date: str = ""):
    print(f"Reading {csv_path} ...")
    seen_prefs = {}
    seen_munis = {}
    seen_wards = {}

    if os.path.exists(db_path):
        os.remove(db_path)

    con = sqlite3.connect(db_path)
    con.executescript(DDL)

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        machiaza_rows = []
        count = 0

        for row in reader:
            pref_code = row["lg_code"][:2]

            if pref_code not in seen_prefs:
                seen_prefs[pref_code] = True
                con.execute(
                    "INSERT OR IGNORE INTO prefectures VALUES (?,?,?,?)",
                    (pref_code, row["pref"], row["pref_kana"], row["pref_roma"]),
                )

            lg_code = row["lg_code"]
            if lg_code not in seen_munis:
                seen_munis[lg_code] = True
                con.execute(
                    "INSERT OR IGNORE INTO municipalities VALUES (?,?,?,?,?,?,?,?)",
                    (
                        lg_code,
                        pref_code,
                        row["county"] or None,
                        row["county_kana"] or None,
                        row["county_roma"] or None,
                        row["city"],
                        row["city_kana"],
                        row["city_roma"],
                    ),
                )

            ward = row["ward"] or None
            if ward and (lg_code, ward) not in seen_wards:
                seen_wards[(lg_code, ward)] = True
                con.execute(
                    "INSERT OR IGNORE INTO wards VALUES (?,?,?,?)",
                    (lg_code, ward, row["ward_kana"], row["ward_roma"]),
                )

            machiaza_rows.append((
                lg_code,
                row["machiaza_id"],
                int_or_none(row["machiaza_type"]),
                ward,
                row["oaza_cho"] or None,
                row["oaza_cho_kana"] or None,
                row["oaza_cho_roma"] or None,
                row["chome"] or None,
                row["chome_kana"] or None,
                int_or_none(row["chome_number"]),
                row["koaza"] or None,
                row["koaza_kana"] or None,
                row["koaza_roma"] or None,
                row["machiaza_dist"] or None,
                int_or_none(row["rsdt_addr_flg"]),
                int_or_none(row["rsdt_addr_mtd_code"]),
                int_or_none(row["oaza_cho_aka_flg"]),
                int_or_none(row["koaza_aka_code"]),
                row["oaza_cho_gsi_uncmn"] or None,
                row["koaza_gsi_uncmn"] or None,
                int_or_none(row["status_flg"]),
                int_or_none(row["wake_num_flg"]),
                row["efct_date"] or None,
                row["ablt_date"] or None,
                int_or_none(row["src_code"]),
                row["post_code"] or None,
                row["remarks"] or None,
            ))

            count += 1
            if count % 100_000 == 0:
                print(f"  {count:,} rows processed ...")

        print(f"Inserting {len(machiaza_rows):,} machiaza rows ...")
        con.executemany(
            "INSERT OR IGNORE INTO machiaza VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            machiaza_rows,
        )

    con.execute("INSERT OR REPLACE INTO metadata VALUES ('source', 'デジタル庁 アドレス・ベース・レジストリ 町字マスター')")
    con.execute("INSERT OR REPLACE INTO metadata VALUES ('source_url', 'https://catalog.registries.digital.go.jp/rsc/address/mt_town_all.csv.zip')")
    if source_date:
        con.execute("INSERT OR REPLACE INTO metadata VALUES ('source_date', ?)", (source_date,))
    con.execute("INSERT OR REPLACE INTO metadata VALUES ('rows_machiaza', (SELECT COUNT(*) FROM machiaza))")
    con.execute("INSERT OR REPLACE INTO metadata VALUES ('rows_municipalities', (SELECT COUNT(*) FROM municipalities))")
    con.execute("INSERT OR REPLACE INTO metadata VALUES ('rows_prefectures', (SELECT COUNT(*) FROM prefectures))")

    con.commit()
    con.close()

    size_mb = os.path.getsize(db_path) / 1024 / 1024
    print(f"Done. {db_path} ({size_mb:.1f} MB)")
    print(f"  prefectures:    {len(seen_prefs):,}")
    print(f"  municipalities: {len(seen_munis):,}")
    print(f"  wards:          {len(seen_wards):,}")
    print(f"  machiaza:       {count:,}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <mt_town_all.csv> <output.db> [source_date]")
        sys.exit(1)
    source_date = sys.argv[3] if len(sys.argv) > 3 else ""
    build(sys.argv[1], sys.argv[2], source_date)

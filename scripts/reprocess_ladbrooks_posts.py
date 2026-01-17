import sqlite3

from website.LadbrooksPokerHandProcessor import LadbrooksPokerHandProcessor


def main():
    db_path = r"C:\Users\verbi\OneDrive\Desktop\Poker_data_webpage-main\instance\database.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, file_data, category FROM post WHERE file_data IS NOT NULL"
    )
    rows = cur.fetchall()
    updated = 0
    skipped = 0

    for post_id, file_blob, category in rows:
        if category != "ladbrooks":
            continue
        if not file_blob:
            skipped += 1
            continue
        data = file_blob.decode("utf-8")
        processor = LadbrooksPokerHandProcessor(data)
        ok, reason, df, results = processor.process_ladbrooks()
        if not ok or df is None or results is None or df.empty or results.empty:
            skipped += 1
            continue

        cur.execute(
            "UPDATE post SET data_frame=?, data_frame_results=? WHERE id=?",
            (df.to_json(orient="records"), results.to_json(orient="records"), post_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"updated={updated} skipped={skipped}")


if __name__ == "__main__":
    main()

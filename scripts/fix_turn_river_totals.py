import json
import sqlite3
from io import StringIO

import pandas as pd


def hero_reached_street(raw_hand, street):
    if not raw_hand or not isinstance(raw_hand, str):
        return False
    if "** Dealing Flop **" not in raw_hand:
        return False
    if street == "turn" and "** Dealing Turn **" not in raw_hand:
        return False
    if street == "river" and "** Dealing River **" not in raw_hand:
        return False

    # Preflop: Hero must not fold before flop
    if "** Dealing down cards **" in raw_hand:
        preflop = raw_hand.split("** Dealing down cards **")[1].split("** Dealing Flop **")[0]
        if "Hero folds" in preflop:
            return False

    # Flop: Hero must not fold before turn/river
    flop_section = raw_hand.split("** Dealing Flop **")[1]
    if "** Dealing Turn **" in flop_section:
        flop_section = flop_section.split("** Dealing Turn **")[0]
    elif "** Summary **" in flop_section:
        flop_section = flop_section.split("** Summary **")[0]
    if "Hero folds" in flop_section:
        return False

    if street == "river":
        turn_section = raw_hand.split("** Dealing Turn **")[1]
        if "** Dealing River **" in turn_section:
            turn_section = turn_section.split("** Dealing River **")[0]
        elif "** Summary **" in turn_section:
            turn_section = turn_section.split("** Summary **")[0]
        if "Hero folds" in turn_section:
            return False

    return True


def compute_street_total(df, street):
    active_col = f"hero_is_active_on_{street}"
    saw_col = f"hero_saw_{street}"
    flop_active_col = "hero_is_active_on_flop"
    flop_saw_col = "hero_saw_flop"

    if active_col in df.columns:
        mask = df[active_col] == True
    elif saw_col in df.columns:
        mask = df[saw_col] == True
    else:
        if "Raw Hand" not in df.columns:
            return None
        return int(df["Raw Hand"].apply(lambda x: hero_reached_street(x, street)).sum())

    if flop_active_col in df.columns:
        mask = mask & (df[flop_active_col] == True)
    elif flop_saw_col in df.columns:
        mask = mask & (df[flop_saw_col] == True)

    return int(mask.sum())


def main():
    db_path = r"C:\Users\verbi\OneDrive\Desktop\Poker_data_webpage-main\instance\database.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, data_frame, data_frame_results FROM post")
    rows = cur.fetchall()
    updated = 0

    for post_id, df_json, results_json in rows:
        if not df_json or not results_json:
            continue
        df = pd.read_json(StringIO(df_json), orient="records")
        metrics_list = json.loads(results_json)
        if not metrics_list or not isinstance(metrics_list, list):
            continue
        metrics = metrics_list[0]

        turn_total = compute_street_total(df, "turn")
        river_total = compute_street_total(df, "river")
        if turn_total is None and river_total is None:
            continue

        if turn_total is not None:
            metrics["Turn Action Frequency"] = json.dumps({"total_hands": turn_total})
        if river_total is not None:
            metrics["River Action Frequency"] = json.dumps({"total_hands": river_total})

        metrics_list[0] = metrics
        cur.execute(
            "UPDATE post SET data_frame_results=? WHERE id=?",
            (json.dumps(metrics_list), post_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"updated={updated}")


if __name__ == "__main__":
    main()

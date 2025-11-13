from __future__ import annotations
import argparse
import os
import sqlite3
import pandas as pd

TABLES = {
    # Map: csv file name → sqlite table name
    "olist_customers_dataset.csv": "olist_customers_dataset",
    "olist_geolocation_dataset.csv": "olist_geolocation_dataset",
    "olist_order_items_dataset.csv": "olist_order_items_dataset",
    "olist_order_payments_dataset.csv": "olist_order_payments_dataset",
    "olist_order_reviews_dataset.csv": "olist_order_reviews_dataset",
    "olist_orders_dataset.csv": "olist_orders_dataset",
    "olist_products_dataset.csv": "olist_products_dataset",
    "olist_sellers_dataset.csv": "olist_sellers_dataset",
    "product_category_name_translation.csv": "product_category_name_translation",
}

DTYPES = {
    # allow pandas type inference but we can enforce some
}


def build_db(csv_dir: str, out_db: str):
    if not os.path.isdir(csv_dir):
        raise SystemExit(f"CSV dir not found: {csv_dir}")
    if os.path.exists(out_db):
        os.remove(out_db)
    con = sqlite3.connect(out_db)

    try:
        for fname, tname in TABLES.items():
            fpath = os.path.join(csv_dir, fname)
            if not os.path.exists(fpath):
                print(f"WARN: missing {fname}, skipping")
                continue
            print(f"Loading {fname} → {tname}")
            df = pd.read_csv(fpath)
            df.to_sql(tname, con, if_exists="fail", index=False)

        # Helpful indices
        idx_cmds = [
            "CREATE INDEX IF NOT EXISTS idx_orders_customer ON olist_orders_dataset(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_items_order ON olist_order_items_dataset(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_items_product ON olist_order_items_dataset(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_products_category ON olist_products_dataset(product_category_name)",
        ]
        for cmd in idx_cmds:
            con.execute(cmd)

        # Example materialized view: revenue per order item
        con.execute(
            """
            CREATE VIEW IF NOT EXISTS v_order_item_revenue AS
            SELECT
              i.order_id,
              i.product_id,
              (i.price + COALESCE(i.freight_value,0)) AS revenue
            FROM olist_order_items_dataset i;
            """
        )
        con.commit()
        print(f"Built {out_db}")
    finally:
        con.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv_dir", required=True)
    ap.add_argument("--out_db", default="olist.db")
    args = ap.parse_args()
    build_db(args.csv_dir, args.out_db)

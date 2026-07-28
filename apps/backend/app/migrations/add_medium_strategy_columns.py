"""
Migration script to add Medium Strategy columns to the blog_posts table.
Run this once to add the new columns that were added to the BlogPost model.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text, inspect
from app.core.database import engine


# Columns to add: (column_name, column_type_sql)
NEW_COLUMNS = [
    ("seo_title", "VARCHAR"),
    ("feed_title", "VARCHAR"),
    ("title_variations", "JSON"),
    ("url_slug", "VARCHAR"),
    ("kicker", "VARCHAR"),
    ("subtitle", "VARCHAR"),
    ("hero_image_url", "VARCHAR"),
    ("hero_image_caption", "VARCHAR"),
    ("compliance_flags", "JSON"),
    ("strategy_audit", "JSON"),
    ("tag_recommendations", "JSON"),
]


def migrate():
    inspector = inspect(engine)
    existing_columns = [col["name"] for col in inspector.get_columns("blog_posts")]

    print(f"Existing columns in blog_posts: {existing_columns}")
    print()

    added = []
    skipped = []

    with engine.begin() as conn:
        for col_name, col_type in NEW_COLUMNS:
            if col_name in existing_columns:
                skipped.append(col_name)
                print(f"  [SKIP] Column '{col_name}' already exists.")
            else:
                sql = f"ALTER TABLE blog_posts ADD COLUMN {col_name} {col_type}"
                conn.execute(text(sql))
                added.append(col_name)
                print(f"  [ADD]  Column '{col_name}' ({col_type}) added successfully.")

    print()
    print(f"Migration complete: {len(added)} columns added, {len(skipped)} already existed.")
    if added:
        print(f"  Added: {', '.join(added)}")


if __name__ == "__main__":
    migrate()

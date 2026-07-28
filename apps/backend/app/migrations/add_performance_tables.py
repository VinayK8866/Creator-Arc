"""
Migration script to create performance_snapshots & learned_insights tables,
and add publication tracking columns to the blog_posts table.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text, inspect
from app.core.database import engine, Base
from app.models.blog_post import BlogPost
from app.models.performance_snapshot import PerformanceSnapshot
from app.models.learned_insight import LearnedInsight


BLOG_POST_NEW_COLUMNS = [
    ("publication_status", "VARCHAR DEFAULT 'draft'"),
    ("published_url", "VARCHAR"),
    ("published_at", "TIMESTAMP"),
    ("publication_name", "VARCHAR"),
    ("last_snapshot_at", "TIMESTAMP"),
]


def migrate():
    # 1. Create missing tables (performance_snapshots, learned_insights)
    Base.metadata.create_all(bind=engine, tables=[
        PerformanceSnapshot.__table__,
        LearnedInsight.__table__
    ])
    print("Checked/Created performance_snapshots and learned_insights tables.")

    # 2. Add columns to blog_posts if not exists
    inspector = inspect(engine)
    existing_columns = [col["name"] for col in inspector.get_columns("blog_posts")]

    added = []
    skipped = []

    with engine.begin() as conn:
        for col_name, col_type in BLOG_POST_NEW_COLUMNS:
            if col_name in existing_columns:
                skipped.append(col_name)
                print(f"  [SKIP] Column '{col_name}' already exists in blog_posts.")
            else:
                sql = f"ALTER TABLE blog_posts ADD COLUMN {col_name} {col_type}"
                conn.execute(text(sql))
                added.append(col_name)
                print(f"  [ADD]  Column '{col_name}' ({col_type}) added successfully.")

    print(f"Migration complete: {len(added)} columns added to blog_posts, {len(skipped)} skipped.")


if __name__ == "__main__":
    migrate()

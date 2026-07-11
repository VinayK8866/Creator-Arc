from sqlalchemy import text
from app.core.database import engine


def run_pgvector_migration():
    print("Migration: Starting pgvector PostgreSQL database migration...")
    
    # 1. Enable extension
    sql_enable_ext = "CREATE EXTENSION IF NOT EXISTS vector;"
    
    # 2. Check and recreate embedding column as type vector(768)
    sql_check_type = """
    SELECT data_type 
    FROM information_schema.columns 
    WHERE table_name = 'style_references' AND column_name = 'embedding';
    """
    
    sql_drop_col = "ALTER TABLE style_references DROP COLUMN IF EXISTS embedding;"
    sql_add_col = "ALTER TABLE style_references ADD COLUMN embedding vector(768);"
    
    # 3. Create HNSW index for cosine distance similarity
    sql_create_index = """
    CREATE INDEX IF NOT EXISTS style_references_embedding_hnsw_idx 
    ON style_references USING hnsw (embedding vector_cosine_ops);
    """
    
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            # 1. Create pgvector extension
            print("Migration: Creating pgvector extension if not exists...")
            conn.execute(text(sql_enable_ext))
            
            # 2. Inspect column type
            result = conn.execute(text(sql_check_type)).fetchone()
            column_type = result[0] if result else None
            print(f"Migration: Current 'embedding' column type is: {column_type}")
            
            if column_type != 'USER-DEFINED': # 'USER-DEFINED' represents custom types like vector in PG
                print("Migration: Dropping old column and adding vector(768) column type...")
                conn.execute(text(sql_drop_col))
                conn.execute(text(sql_add_col))
            else:
                print("Migration: Column 'embedding' is already of vector type. Skipping column recreation.")
                
            # 3. Create HNSW index
            print("Migration: Creating HNSW index for cosine operations...")
            conn.execute(text(sql_create_index))
            
            transaction.commit()
            print("Migration: pgvector database migration completed successfully.")
            return True
            
        except Exception as e:
            transaction.rollback()
            err_msg = str(e)
            print(f"Migration Error: Failed to run pgvector migration. Details: {err_msg}")
            
            # Check if it was a permission error (common on managed/free databases)
            if "permission" in err_msg.lower() or "superuser" in err_msg.lower():
                print("Migration Warning: Insufficient permissions to compile PG extensions. Cosine similarities will run on fallback Python numpy logic.")
            return False


if __name__ == "__main__":
    run_pgvector_migration()

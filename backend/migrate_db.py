import os
import sys
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.config import get_settings

def migrate_db():
    print("Migrating database...")
    settings = get_settings()
    
    # Construct DB URL from settings
    # When running inside container, postgres_host should be 'postgres' (or whatever is in env)
    # We trust the settings unless we are explicitly overriding for local host execution
    db_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}/{settings.postgres_db}"
    
    # Only adjust if we are NOT in the container (simple heuristic: if host is 'postgres' but we can't resolve it, 
    # but here we assume we are running where we should be).
    # If we really need to support local run, we should check env var or argument.
    # For now, let's assume we run inside container as instructed.
    if os.environ.get("RUNNING_LOCALLY") == "true":
         db_url = db_url.replace("@postgres", "@localhost")
         
    print(f"Connecting to DB: {db_url}")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='documents' AND column_name='hash_sha256'"))
            if result.fetchone():
                print("Column 'hash_sha256' already exists.")
            else:
                print("Adding column 'hash_sha256'...")
                conn.execute(text("ALTER TABLE documents ADD COLUMN hash_sha256 VARCHAR"))
                conn.execute(text("CREATE INDEX ix_documents_hash_sha256 ON documents (hash_sha256)"))
                conn.commit()
                print("Column added successfully.")
            
            # Check if forensic_metadata column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='documents' AND column_name='forensic_metadata'"))
            if result.fetchone():
                print("Column 'forensic_metadata' already exists.")
            else:
                print("Adding column 'forensic_metadata'...")
                conn.execute(text("ALTER TABLE documents ADD COLUMN forensic_metadata JSONB"))
                conn.commit()
                print("Column 'forensic_metadata' added successfully.")
                
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_db()

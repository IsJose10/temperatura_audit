"""Migration: Add foto_url_2 column to auditoria_detalle table."""
import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="1015",
    dbname="temperatura_audit",
    autocommit=True
)
cur = conn.cursor()

# Check if column already exists
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name='auditoria_detalle' AND column_name='foto_url_2'
""")
result = cur.fetchone()

if result:
    print("[OK] Column 'foto_url_2' already exists, skipping.")
else:
    cur.execute("ALTER TABLE auditoria_detalle ADD COLUMN foto_url_2 TEXT NULL")
    print("[OK] Column 'foto_url_2' added successfully.")

cur.close()
conn.close()

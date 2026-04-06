"""Migration: Add temperatura_pasillo column to auditoria_detalle table."""
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
    WHERE table_name='auditoria_detalle' AND column_name='temperatura_pasillo'
""")
result = cur.fetchone()

if result:
    print("[OK] Column 'temperatura_pasillo' already exists, skipping.")
else:
    cur.execute("ALTER TABLE auditoria_detalle ADD COLUMN temperatura_pasillo NUMERIC(5,2) NULL")
    print("[OK] Column 'temperatura_pasillo' added successfully.")

cur.close()
conn.close()

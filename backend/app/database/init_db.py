import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

def create_database():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = "postgresql://postgres:postgres@localhost:5432/payin_automation"
    
    try:
        temp = database_url
        if temp.startswith("postgresql://"):
            temp = temp[len("postgresql://"):]
        elif temp.startswith("postgres://"):
            temp = temp[len("postgres://"):]
        
        user_pass, host_port_db = temp.split("@")
        user, password = user_pass.split(":")
        
        host_port, target_db = host_port_db.split("/")
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, "5432"
            
        if "?" in target_db:
            target_db = target_db.split("?")[0]
            
        print(f"Connecting to 'postgres' database on {host}:{port} to check target DB '{target_db}'...")
        
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (target_db,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{target_db}' does not exist. Creating it...")
            cursor.execute(f'CREATE DATABASE "{target_db}"')
            print(f"Database '{target_db}' created successfully.")
        else:
            print(f"Database '{target_db}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to check/create database: {e}")
        print("Continuing, assuming database exists or is created externally.")

if __name__ == "__main__":
    create_database()

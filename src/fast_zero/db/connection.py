import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB__HOST"),
        port=int(os.getenv("DB__PORT", 5432)),
        user=os.getenv("DB__USERNAME"),
        password=os.getenv("DB__PASSWORD"),
        dbname=os.getenv("DB__NAME"),
        cursor_factory=RealDictCursor
    ) 
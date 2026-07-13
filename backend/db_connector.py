import os

import pyodbc


def get_connection():
    server = os.getenv("DB_SERVER", "192.168.11.15")
    database = os.getenv("DB_NAME", "Practice")
    username = os.getenv("DB_USERNAME", "imada")
    password = os.getenv("DB_PASSWORD", "Riki0603##")

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"Trust_Connection=no;"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(conn_str)

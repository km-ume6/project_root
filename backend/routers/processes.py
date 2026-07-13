from fastapi import APIRouter
from backend.db_connector import get_connection

router = APIRouter(prefix="/processes", tags=["processes"])

@router.get("/")
def get_processes(department_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, sort_order
        FROM processes
        WHERE department_id = ?
        ORDER BY sort_order
    """, (department_id,))
    
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "sort_order": row[2]
        })

    cursor.close()
    conn.close()

    return result
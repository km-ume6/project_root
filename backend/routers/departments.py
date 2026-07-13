from fastapi import APIRouter
from backend.db_connector import get_connection

router = APIRouter(prefix="/departments", tags=["departments"])

@router.get("/")
def get_departments(location_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name 
        FROM departments 
        WHERE location_id = ?
        ORDER BY id
    """, (location_id,))
    
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1]
        })

    cursor.close()
    conn.close()

    return result
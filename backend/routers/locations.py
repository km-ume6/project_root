from fastapi import APIRouter, HTTPException

from backend.db_connector import get_connection

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/")
def get_locations():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM locations ORDER BY id")
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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
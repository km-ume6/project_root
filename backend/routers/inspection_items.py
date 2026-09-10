from fastapi import APIRouter
from backend.db_connector import get_connection
router = APIRouter(prefix='/inspection_items')
from pydantic import BaseModel

class InspectionItemCreate(BaseModel):
    equipment_id: int
    name: str
    type: str
    min_value: float | None = None
    max_value: float | None = None
@router.get("/")
def get_inspection_items(equipment_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, type, min_value, max_value
        FROM inspection_items
        WHERE equipment_id = ?
    """, (equipment_id,))

    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "min_value": row[3],
            "max_value": row[4]
        })

    cursor.close()
    conn.close()

    return result


@router.get("/by_process")
def get_inspection_items_by_process(process_id: int):
    """工程に属する全設備の点検項目を一括取得"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.id, i.equipment_id, i.name, i.type, i.min_value, i.max_value
        FROM inspection_items i
        INNER JOIN equipments e ON e.id = i.equipment_id
        WHERE e.process_id = ?
        ORDER BY i.equipment_id, i.id
    """, (process_id,))

    result = []
    for row in cursor.fetchall():
        result.append({
            "id": row[0],
            "equipment_id": row[1],
            "name": row[2],
            "type": row[3],
            "min_value": row[4],
            "max_value": row[5],
        })

    cursor.close()
    conn.close()
    return result


@router.post("/")
def add_inspection_item(item: InspectionItemCreate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO inspection_items (equipment_id, name, type, min_value, max_value)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?)
    """, (item.equipment_id, item.name, item.type, item.min_value, item.max_value))

    new_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "ok", "item_id": new_id}



@router.get("/{item_id}")
def get_inspection_item(item_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, equipment_id, name, type, min_value, max_value
        FROM inspection_items
        WHERE id = ?
    """, (item_id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        return {"error": "Item not found"}

    return {
        "id": row[0],
        "equipment_id": row[1],
        "name": row[2],
        "type": row[3],
        "min_value": row[4],
        "max_value": row[5]
    }
class InspectionItemUpdate(BaseModel):
    name: str
    type: str
    min_value: float | None = None
    max_value: float | None = None

@router.put("/{item_id}")
def update_inspection_item(item_id: int, item: InspectionItemUpdate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE inspection_items
        SET name = ?, type = ?, min_value = ?, max_value = ?
        WHERE id = ?
    """, (item.name, item.type, item.min_value, item.max_value, item_id))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "updated"}
@router.delete("/{item_id}")
def delete_inspection_item(item_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM inspection_items WHERE id = ?", (item_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return {"status": "deleted"}
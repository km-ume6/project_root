from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from backend.db_connector import get_connection

router = APIRouter(prefix="/inspection_results")

# ===============================
# Pydantic モデル
# ===============================
class InspectionResultCreate(BaseModel):
    equipment_id: int
    item_id: int
    date: date
    value: str


# ===============================
# 点検結果の登録（POST）
# ===============================
@router.post("/")
def add_result(data: InspectionResultCreate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO inspection_results (equipment_id, item_id, date, value)
        VALUES (?, ?, ?, ?)
    """, (data.equipment_id, data.item_id, data.date, data.value))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "ok"}


# ===============================
# 点検結果の取得（GET）
# - 必須ではないが、date が無ければ [] を返す（今日にフォールバックしない）
# - date は YYYY-MM-DD で検証
# ===============================
@router.get("/")
def get_results(equipment_id: int, date: Optional[str] = Query(None)):
    print("GET /inspection_results/ params:", {"equipment_id": equipment_id, "date": date})

    conn = get_connection()
    cursor = conn.cursor()

    # date が無ければ「その機器の全件」を返す（今日フォールバックはしない）
    if not date or date.strip() == "" or date in ("undefined", "null"):
        cursor.execute("""
            SELECT id, equipment_id, item_id, date, value
            FROM inspection_results
            WHERE equipment_id = ?
            ORDER BY date, id
        """, (equipment_id,))
        rows = cursor.fetchall()

        results = []
        for r in rows:
            dt = r[3]
            results.append({
                "id": r[0],
                "equipment_id": r[1],
                "item_id": r[2],
                "date": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                "value": r[4]
            })

        cursor.close()
        conn.close()
        return results

    # date がある場合は YYYY-MM-DD を検証してその日で絞る
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    cursor.execute("""
        SELECT id, equipment_id, item_id, date, value
        FROM inspection_results
        WHERE equipment_id = ? AND date = ?
        ORDER BY id
    """, (equipment_id, target_date))

    rows = cursor.fetchall()
    results = []
    for r in rows:
        dt = r[3]
        results.append({
            "id": r[0],
            "equipment_id": r[1],
            "item_id": r[2],
            "date": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
            "value": r[4]
        })

    cursor.close()
    conn.close()
    return results
# ===============================
# 点検結果の削除（DELETE）
# ===============================
@router.delete("/{result_id}")
def delete_result(result_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM inspection_results
        WHERE id = ?
    """, (result_id,))

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Result not found")

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "deleted"}

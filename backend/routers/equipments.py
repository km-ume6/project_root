from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from typing import Optional, List
from backend.db_connector import get_connection
from fastapi import Body

router = APIRouter(prefix='/equipments')

# 使用した日を登録するモデル
class EquipmentUsageCreate(BaseModel):
    equipment_id: int
    date: date


class EquipmentSkipCreate(BaseModel):
    equipment_id: int
    date: date


def _ensure_equipment_day_skip_table(cursor):
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'equipment_day_skip')
        BEGIN
            CREATE TABLE equipment_day_skip (
                id INT IDENTITY(1,1) PRIMARY KEY,
                equipment_id INT NOT NULL,
                skip_date DATE NOT NULL,
                CONSTRAINT UQ_equipment_day_skip UNIQUE (equipment_id, skip_date)
            );
        END
    """)


def _ensure_equipment_day_use_table(cursor):
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'equipment_day_use')
        BEGIN
            CREATE TABLE equipment_day_use (
                id INT IDENTITY(1,1) PRIMARY KEY,
                equipment_id INT NOT NULL,
                use_date DATE NOT NULL,
                CONSTRAINT UQ_equipment_day_use UNIQUE (equipment_id, use_date)
            );
        END
    """)


def _ensure_default_skip_column(cursor):
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.columns
            WHERE object_id = OBJECT_ID('equipments') AND name = 'default_skip'
        )
        BEGIN
            ALTER TABLE equipments ADD default_skip BIT NOT NULL
                CONSTRAINT DF_equipments_default_skip DEFAULT 0;
        END
    """)


def _row_default_skip(row, index: int) -> bool:
    if len(row) <= index:
        return False
    return bool(row[index])


def _commit_schema(conn, cursor):
    """DDL（CREATE/ALTER）を同じ接続で確定させる"""
    conn.commit()


def _parse_ymd(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")


# ================================
# POST：設備追加
# ================================
@router.post("/")
def add_equipment(
    process_id: int,
    name: str,
    unit_no: str = None,
    management_no: str = None,
    default_skip: bool = False,
):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_default_skip_column(cursor)
    conn.commit()

    cursor.execute("""
        INSERT INTO equipments (process_id, name, unit_no, management_no, default_skip)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?)
    """, (process_id, name, unit_no, management_no, 1 if default_skip else 0))

    new_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "ok", "equipment_id": new_id}


# ================================
# GET：設備一覧取得
# ================================
@router.get("/")
def get_equipments(process_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_default_skip_column(cursor)
    conn.commit()

    cursor.execute("""
        SELECT id, name, unit_no, management_no, sort_order, default_skip
        FROM equipments
        WHERE process_id = ?
        ORDER BY sort_order
    """, (process_id,))

    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "unit_no": row[2],
            "management_no": row[3],
            "sort_order": row[4],
            "default_skip": _row_default_skip(row, 5),
        })

    cursor.close()
    conn.close()

    return result


# ================================
# POST：使用した日を登録（今回追加）
# ================================
@router.post("/equipment_usage")
def add_usage(data: EquipmentUsageCreate):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_skip_table(cursor)
    _ensure_equipment_day_use_table(cursor)

    cursor.execute("""
        DELETE FROM equipment_day_skip
        WHERE equipment_id = ? AND skip_date = ?
    """, (data.equipment_id, data.date))

    cursor.execute("""
        INSERT INTO equipment_usage (equipment_id, date)
        VALUES (?, ?)
    """, (data.equipment_id, data.date))

    cursor.execute("""
        SELECT 1 FROM equipment_day_use
        WHERE equipment_id = ? AND use_date = ?
    """, (data.equipment_id, data.date))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO equipment_day_use (equipment_id, use_date)
            VALUES (?, ?)
        """, (data.equipment_id, data.date))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "ok"}


# ================================
# 本日使用しない（スキップ）登録・解除・取得
# ================================
@router.get("/equipment_skip")
def get_equipment_skips(
    process_id: int,
    date: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_skip_table(cursor)
    conn.commit()

    if date:
        target = _parse_ymd(date)
        cursor.execute("""
            SELECT s.equipment_id, s.skip_date
            FROM equipment_day_skip s
            INNER JOIN equipments e ON e.id = s.equipment_id
            WHERE e.process_id = ? AND s.skip_date = ?
        """, (process_id, target))
    elif from_date and to_date:
        d_from = _parse_ymd(from_date)
        d_to = _parse_ymd(to_date)
        cursor.execute("""
            SELECT s.equipment_id, s.skip_date
            FROM equipment_day_skip s
            INNER JOIN equipments e ON e.id = s.equipment_id
            WHERE e.process_id = ? AND s.skip_date >= ? AND s.skip_date <= ?
        """, (process_id, d_from, d_to))
    else:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Specify date=YYYY-MM-DD or from= and to=",
        )

    rows = cursor.fetchall()
    skips = []
    for row in rows:
        dt = row[1]
        skips.append({
            "equipment_id": row[0],
            "date": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
        })

    cursor.close()
    conn.close()
    return skips


def _has_inspection_results_on_date(cursor, equipment_id: int, target: date) -> bool:
    cursor.execute("""
        SELECT TOP 1 1
        FROM inspection_results
        WHERE equipment_id = ?
          AND date = ?
          AND value IS NOT NULL
          AND LTRIM(RTRIM(CAST(value AS NVARCHAR(4000)))) <> ''
    """, (equipment_id, target))
    return cursor.fetchone() is not None


def _fetch_day_id_set(cursor, table: str, date_col: str, process_id: int, target: date) -> set:
    cursor.execute(f"""
        SELECT t.equipment_id
        FROM {table} t
        INNER JOIN equipments e ON e.id = t.equipment_id
        WHERE e.process_id = ? AND t.{date_col} = ?
    """, (process_id, target))
    return {row[0] for row in cursor.fetchall()}


def _is_equipment_skipped_on_date(eq: dict, skip_ids: set, use_ids: set) -> bool:
    eid = eq["id"]
    if eid in use_ids:
        return False
    if eid in skip_ids:
        return True
    return bool(eq.get("default_skip"))


def _apply_auto_skip_from_previous_day(cursor, process_id: int, target: date) -> list:
    """前日が点検対象かつ未点検だった設備を、当日「使用しない」に自動登録する"""
    prev = target - timedelta(days=1)
    prev_skips = _fetch_day_id_set(cursor, "equipment_day_skip", "skip_date", process_id, prev)
    prev_uses = _fetch_day_id_set(cursor, "equipment_day_use", "use_date", process_id, prev)
    today_skips = _fetch_day_id_set(cursor, "equipment_day_skip", "skip_date", process_id, target)
    today_uses = _fetch_day_id_set(cursor, "equipment_day_use", "use_date", process_id, target)

    cursor.execute(
        "SELECT id, default_skip FROM equipments WHERE process_id = ?",
        (process_id,),
    )
    equipments = [{"id": row[0], "default_skip": bool(row[1])} for row in cursor.fetchall()]

    applied = []
    for eq in equipments:
        eid = eq["id"]
        if _is_equipment_skipped_on_date(eq, prev_skips, prev_uses):
            continue
        if _has_inspection_results_on_date(cursor, eid, prev):
            continue
        if _has_inspection_results_on_date(cursor, eid, target):
            continue
        if eid in today_uses:
            continue
        if _is_equipment_skipped_on_date(eq, today_skips, today_uses):
            continue
        if eid in today_skips:
            continue

        cursor.execute("""
            INSERT INTO equipment_day_skip (equipment_id, skip_date)
            VALUES (?, ?)
        """, (eid, target))
        applied.append(eid)

    return applied


@router.post("/equipment_skip/auto_from_previous_day")
def auto_skip_from_previous_day(
    process_id: int,
    date: str = Query(...),
):
    """前日未点検の設備を当日「本日は使用しない」へ自動登録（当日分のみ）"""
    target = _parse_ymd(date)
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_skip_table(cursor)
    _ensure_equipment_day_use_table(cursor)
    _ensure_default_skip_column(cursor)
    _commit_schema(conn, cursor)

    applied = _apply_auto_skip_from_previous_day(cursor, process_id, target)
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "ok", "applied_equipment_ids": applied}


@router.post("/equipment_skip")
def add_equipment_skip(data: EquipmentSkipCreate):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_skip_table(cursor)
    _ensure_equipment_day_use_table(cursor)
    _commit_schema(conn, cursor)

    if _has_inspection_results_on_date(cursor, data.equipment_id, data.date):
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="点検結果が登録されているため「本日は使用しない」にできません",
        )

    cursor.execute("""
        SELECT 1 FROM equipment_day_skip
        WHERE equipment_id = ? AND skip_date = ?
    """, (data.equipment_id, data.date))

    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO equipment_day_skip (equipment_id, skip_date)
            VALUES (?, ?)
        """, (data.equipment_id, data.date))

    cursor.execute("""
        DELETE FROM equipment_day_use
        WHERE equipment_id = ? AND use_date = ?
    """, (data.equipment_id, data.date))

    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "ok"}


@router.delete("/equipment_skip")
def delete_equipment_skip(equipment_id: int, date: str = Query(...)):
    target = _parse_ymd(date)
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_skip_table(cursor)
    _commit_schema(conn, cursor)

    cursor.execute("""
        DELETE FROM equipment_day_skip
        WHERE equipment_id = ? AND skip_date = ?
    """, (equipment_id, target))

    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "deleted"}


class EquipmentUseCreate(BaseModel):
    equipment_id: int
    date: date


@router.get("/equipment_use")
def get_equipment_uses(
    process_id: int,
    date: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_use_table(cursor)
    conn.commit()

    if date:
        target = _parse_ymd(date)
        cursor.execute("""
            SELECT u.equipment_id, u.use_date
            FROM equipment_day_use u
            INNER JOIN equipments e ON e.id = u.equipment_id
            WHERE e.process_id = ? AND u.use_date = ?
        """, (process_id, target))
    elif from_date and to_date:
        d_from = _parse_ymd(from_date)
        d_to = _parse_ymd(to_date)
        cursor.execute("""
            SELECT u.equipment_id, u.use_date
            FROM equipment_day_use u
            INNER JOIN equipments e ON e.id = u.equipment_id
            WHERE e.process_id = ? AND u.use_date >= ? AND u.use_date <= ?
        """, (process_id, d_from, d_to))
    else:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Specify date=YYYY-MM-DD or from= and to=",
        )

    rows = cursor.fetchall()
    uses = []
    for row in rows:
        dt = row[1]
        uses.append({
            "equipment_id": row[0],
            "date": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
        })

    cursor.close()
    conn.close()
    return uses


@router.post("/equipment_use")
def add_equipment_use(data: EquipmentUseCreate):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _ensure_equipment_day_use_table(cursor)
        _ensure_equipment_day_skip_table(cursor)
        _commit_schema(conn, cursor)

        cursor.execute("""
            DELETE FROM equipment_day_skip
            WHERE equipment_id = ? AND skip_date = ?
        """, (data.equipment_id, data.date))

        cursor.execute("""
            SELECT 1 FROM equipment_day_use
            WHERE equipment_id = ? AND use_date = ?
        """, (data.equipment_id, data.date))

        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO equipment_day_use (equipment_id, use_date)
                VALUES (?, ?)
            """, (data.equipment_id, data.date))

        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/equipment_use")
def delete_equipment_use(equipment_id: int, date: str = Query(...)):
    target = _parse_ymd(date)
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_use_table(cursor)
    _commit_schema(conn, cursor)

    cursor.execute("""
        DELETE FROM equipment_day_use
        WHERE equipment_id = ? AND use_date = ?
    """, (equipment_id, target))

    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "deleted"}


# ================================
# DELETE：設備削除（/{equipment_id} より前に固定パスを置くこと）
# ================================
@router.delete("/{equipment_id}")
def delete_equipment(equipment_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_equipment_day_skip_table(cursor)
    _ensure_equipment_day_use_table(cursor)

    try:
        cursor.execute("SELECT id FROM equipments WHERE id = ?", (equipment_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="設備が見つかりません")

        cursor.execute(
            "DELETE FROM inspection_results WHERE equipment_id = ?",
            (equipment_id,),
        )
        cursor.execute(
            "DELETE FROM inspection_results WHERE item_id IN (SELECT id FROM inspection_items WHERE equipment_id = ?)",
            (equipment_id,),
        )
        cursor.execute(
            "DELETE FROM inspection_items WHERE equipment_id = ?",
            (equipment_id,),
        )
        cursor.execute(
            "DELETE FROM equipment_day_skip WHERE equipment_id = ?",
            (equipment_id,),
        )
        cursor.execute(
            "DELETE FROM equipment_day_use WHERE equipment_id = ?",
            (equipment_id,),
        )
        try:
            cursor.execute(
                "DELETE FROM equipment_usage WHERE equipment_id = ?",
                (equipment_id,),
            )
        except Exception:
            pass

        cursor.execute("DELETE FROM equipments WHERE id = ?", (equipment_id,))

        conn.commit()
        return {"status": "deleted"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ================================
# GET：設備詳細取得（今回追加）
# ================================
@router.put("/sort_order")
def update_sort_order(ids: list[int] = Body(...)):
    print("RECEIVED:", ids)
    conn = get_connection()
    cursor = conn.cursor()

    for index, equipment_id in enumerate(ids):
        cursor.execute("""
            UPDATE equipments
            SET sort_order = ?
            WHERE id = ?
        """, (index, equipment_id))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "ok"}
@router.get("/{equipment_id}")
def get_equipment_detail(equipment_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_default_skip_column(cursor)
    conn.commit()

    cursor.execute("""
        SELECT id, name, unit_no, management_no, process_id, default_skip
        FROM equipments
        WHERE id = ?
    """, (equipment_id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "unit_no": row[2],
            "management_no": row[3],
            "process_id": row[4],
            "default_skip": _row_default_skip(row, 5),
        }
    else:
        return {"error": "not found"}


@router.put("/{equipment_id}")
def update_equipment(
    equipment_id: int,
    name: str,
    unit_no: str = None,
    management_no: str = None,
    default_skip: bool = False,
):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_default_skip_column(cursor)
    conn.commit()

    cursor.execute("""
        UPDATE equipments
        SET name = ?, unit_no = ?, management_no = ?, default_skip = ?
        WHERE id = ?
    """, (name, unit_no, management_no, 1 if default_skip else 0, equipment_id))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "updated"}






# ================================
# GET：点検結果取得（新規追加）
# - date が無ければ空配列を返す（今日にフォールバックしない）
# - date は YYYY-MM-DD で検証
# - DB のカラム名はプロジェクトに合わせて調整してください
# ================================
@router.get("/inspection_results/")
def get_inspection_results(equipment_id: int, date: Optional[str] = Query(None)):
    # デバッグログ（開発環境のみ）
    print("GET /inspection_results/ params:", {"equipment_id": equipment_id, "date": date})

    # date が無ければ空配列を返す（今日にフォールバックしない）
    if not date or date.strip() == "" or date in ("undefined", "null"):
        return []

    # date のフォーマット検証（YYYY-MM-DD）
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    conn = get_connection()
    cursor = conn.cursor()

    # ここで使用しているカラム名は 'inspection_date' を想定しています。
    # 実際のテーブル定義が異なる場合は 'inspection_date' を適切なカラム名に置き換えてください。
    cursor.execute("""
        SELECT id, equipment_id, item_id, value, inspection_date
        FROM inspection_results
        WHERE equipment_id = ? AND inspection_date = ?
        ORDER BY id
    """, (equipment_id, target_date))

    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "equipment_id": row[1],
            "item_id": row[2],
            "value": row[3],
            # 日付は文字列で返す（フロントが期待する形式に合わせてください）
            "inspection_date": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4])
        })

    cursor.close()
    conn.close()

    return result
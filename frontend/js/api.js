// 8000番で画面+APIを同じオリジン配信。5500番のときだけ :8000 を使う
const API_BASE =
    window.location.port === "8000" || window.location.port === "80" || window.location.port === "443" || window.location.port === ""
        ? ""
        : `${window.location.protocol}//${window.location.hostname}:8000`;


async function getLocations() {
    const res = await fetch(`${API_BASE}/locations/`);
    if (!res.ok) throw new Error("拠点一覧の取得に失敗しました");
    return await res.json();
}

async function addEquipment(process_id, name, number, manager) {
    const res = await fetch(`${API_BASE}/equipments/?process_id=${process_id}&name=${name}&number=${number}&manager=${manager}`, {
        method: "POST"
    });
    return await res.json();
}

async function addInspectionItem(equipment_id, name, type, min_value, max_value) {
    const res = await fetch(`${API_BASE}/inspection_items/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            equipment_id,
            name,
            type,
            min_value,
            max_value
        })
    });

    return await res.json();
}

// ===============================
// 設備削除 API
// ===============================
async function deleteEquipment(equipmentId) {
    const res = await fetch(`${API_BASE}/equipments/${encodeURIComponent(equipmentId)}`, {
        method: "DELETE"
    });

    if (!res.ok) {
        const msg = await _apiErrorMessage(res, "設備の削除に失敗しました");
        alert(msg);
        return false;
    }

    return true;
}

/** ローカル暦で YYYY-MM-DD（toISOString の UTC ズレを避ける） */
function formatLocalDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

/** URL の date=YYYY-MM-DD が有効か */
function isValidCalendarDateParam(dateStr) {
    if (!dateStr || typeof dateStr !== "string") return false;
    const s = dateStr.trim();
    if (s === "" || s === "undefined" || s === "null") return false;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    const [y, m, d] = s.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
}

/** URL の date が有効ならそれを使い、無効・欠落時はローカルの今日 */
function resolveInspectionTargetDate(urlDateParam) {
    if (isValidCalendarDateParam(urlDateParam)) return urlDateParam.trim();
    return formatLocalDate(new Date());
}

/** YYYY-MM-DD を「2026年5月15日（金）」形式へ（ローカル暦） */
function formatInspectionDateLabel(ymd) {
    if (!isValidCalendarDateParam(ymd)) return "";
    const [y, m, d] = ymd.trim().split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
    return `${y}年${m}月${d}日（${weekdays[dt.getDay()]}）`;
}

/** 工程×日付の「本日使用しない」一覧を取得 */
async function fetchEquipmentSkips(processId, dateYmd) {
    const res = await fetch(
        `${API_BASE}/equipments/equipment_skip?process_id=${encodeURIComponent(processId)}&date=${encodeURIComponent(dateYmd)}`
    );
    if (!res.ok) return [];
    return await res.json();
}

/** 工程×期間のスキップ一覧（カレンダー用） */
async function fetchEquipmentSkipsRange(processId, fromYmd, toYmd) {
    const res = await fetch(
        `${API_BASE}/equipments/equipment_skip?process_id=${encodeURIComponent(processId)}&from=${encodeURIComponent(fromYmd)}&to=${encodeURIComponent(toYmd)}`
    );
    if (!res.ok) return [];
    return await res.json();
}

async function setEquipmentSkip(equipmentId, dateYmd, skipped) {
    let res;
    if (skipped) {
        res = await fetch(`${API_BASE}/equipments/equipment_skip`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ equipment_id: Number(equipmentId), date: dateYmd }),
        });
    } else {
        res = await fetch(
            `${API_BASE}/equipments/equipment_skip?equipment_id=${encodeURIComponent(equipmentId)}&date=${encodeURIComponent(dateYmd)}`,
            { method: "DELETE" }
        );
    }
    if (!res.ok) {
        const detail = await res.text().catch(() => "");
        throw new Error(detail || `equipment_skip failed (${res.status})`);
    }
}

async function fetchEquipmentUses(processId, dateYmd) {
    const res = await fetch(
        `${API_BASE}/equipments/equipment_use?process_id=${encodeURIComponent(processId)}&date=${encodeURIComponent(dateYmd)}`
    );
    if (!res.ok) return [];
    return await res.json();
}

async function fetchEquipmentUsesRange(processId, fromYmd, toYmd) {
    const res = await fetch(
        `${API_BASE}/equipments/equipment_use?process_id=${encodeURIComponent(processId)}&from=${encodeURIComponent(fromYmd)}&to=${encodeURIComponent(toYmd)}`
    );
    if (!res.ok) return [];
    return await res.json();
}

/** 前日未点検の設備を当日「使用しない」へ自動登録（当日表示時のみ） */
async function applyAutoSkipFromPreviousDay(processId, dateYmd) {
    if (!processId || !dateYmd || dateYmd !== formatLocalDate(new Date())) {
        return { applied_equipment_ids: [] };
    }
    try {
        const res = await fetch(
            `${API_BASE}/equipments/equipment_skip/auto_from_previous_day?process_id=${encodeURIComponent(processId)}&date=${encodeURIComponent(dateYmd)}`,
            { method: "POST" }
        );
        if (!res.ok) {
            console.warn("auto skip:", await res.text().catch(() => ""));
            return { applied_equipment_ids: [] };
        }
        return await res.json();
    } catch (e) {
        console.warn("auto skip failed", e);
        return { applied_equipment_ids: [] };
    }
}

/** その日の点検結果が1件でも登録されているか（値が空でないもの） */
function hasInspectionResultsForDay(results) {
    if (!results || !results.length) return false;
    return results.some((r) => {
        const v = r.value;
        return v !== null && v !== undefined && String(v).trim() !== "";
    });
}

/** その日「使用しない」か（明示スキップ or マスタ初期値） */
function isEquipmentSkippedToday(eq, skipIds, useIds) {
    const id = String(eq.id);
    if (useIds && useIds.has(id)) return false;
    if (skipIds && skipIds.has(id)) return true;
    return !!eq.default_skip;
}

/** その日の使用／不使用を保存（普段は使用しない設備の例外も扱う） */
async function _apiErrorMessage(res, fallback) {
    const text = await res.text().catch(() => "");
    try {
        const j = JSON.parse(text);
        if (j.detail) return typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch (_) { /* not json */ }
    return text || fallback || `HTTP ${res.status}`;
}

async function setEquipmentDayState(equipmentId, dateYmd, wantSkip, defaultSkip) {
    const id = Number(equipmentId);
    if (wantSkip) {
        await setEquipmentSkip(id, dateYmd, true);
        const res = await fetch(
            `${API_BASE}/equipments/equipment_use?equipment_id=${encodeURIComponent(id)}&date=${encodeURIComponent(dateYmd)}`,
            { method: "DELETE" }
        );
        if (!res.ok) throw new Error(await _apiErrorMessage(res, "equipment_use の解除に失敗"));
    } else {
        await setEquipmentSkip(id, dateYmd, false);
        if (defaultSkip) {
            const res = await fetch(`${API_BASE}/equipments/equipment_use`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ equipment_id: id, date: dateYmd }),
            });
            if (!res.ok) throw new Error(await _apiErrorMessage(res, "「今日は使用する」の保存に失敗"));
        } else {
            const res = await fetch(
                `${API_BASE}/equipments/equipment_use?equipment_id=${encodeURIComponent(id)}&date=${encodeURIComponent(dateYmd)}`,
                { method: "DELETE" }
            );
            if (!res.ok) throw new Error(await _apiErrorMessage(res, "equipment_use の解除に失敗"));
        }
    }
}

/** カレンダーで選んだ点検日をページ上部に表示（無効・未指定なら非表示） */
function applySelectedDateBanner(elementId, ymd) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const label = formatInspectionDateLabel(ymd);
    if (!label) {
        el.classList.add("hidden");
        el.textContent = "";
        return;
    }
    el.classList.remove("hidden");
    el.textContent = `点検日：${label}`;
}
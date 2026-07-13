// ===============================
// 拠点一覧
// ===============================
async function loadLocations() {
    const container = document.getElementById("location-container");
    const status = document.getElementById("load-status");
    if (!container) return;

    if (status) status.textContent = "読み込み中…";

    try {
        const locations = await getLocations();
        container.innerHTML = "";

        if (!Array.isArray(locations) || locations.length === 0) {
            if (status) status.textContent = "";
            container.innerHTML = "<p>拠点が登録されていません。</p>";
            return;
        }

        locations.forEach(loc => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `<div class="card-title">${loc.name}</div>`;

            card.onclick = () => {
                window.location.href = `departments.html?location_id=${loc.id}`;
            };

            container.appendChild(card);
        });
        if (status) status.textContent = "";
    } catch (err) {
        console.error("拠点一覧の取得エラー:", err);
        if (status) status.textContent = "";
        const entry = `${window.location.protocol}//${window.location.hostname}:8000/pages/locations.html`;
        container.innerHTML = `<p style="color:#c00;">拠点一覧を読み込めませんでした。<br>次のURLで開いてください：<br><a href="${entry}">${entry}</a><br>（古いQRやブックマークのIPが合っていない可能性があります）</p>`;
    }
}

// ===============================
// 部署一覧
// ===============================
async function loadDepartments(location_id) {
    const res = await fetch(`${API_BASE}/departments/?location_id=${location_id}`);
    const departments = await res.json();

    const container = document.getElementById("department-container");
    if (!container) return;

    container.innerHTML = "";

    departments.forEach(dep => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `<div class="card-title">${dep.name}</div>`;

        card.onclick = () => {
            window.location.href =
                `processes.html?department_id=${dep.id}&location_id=${location_id}`;
        };

        container.appendChild(card);
    });
}

// ===============================
// 工程一覧
// ===============================
async function loadProcesses(department_id) {
    const res = await fetch(`${API_BASE}/processes/?department_id=${department_id}`);
    const processes = await res.json();

    const container = document.getElementById("process-container");
    if (!container) return;

    container.innerHTML = "";

    processes.forEach(proc => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `<div class="card-title">${proc.name}</div>`;

        card.onclick = () => {
            window.location.href =
                `calendar.html?process_id=${proc.id}&department_id=${department_id}`;
        };

        container.appendChild(card);
    });
}

// ===============================
// 設備一覧
// ===============================
async function loadEquipments(process_id) {
    const res = await fetch(`${API_BASE}/equipments/?process_id=${process_id}`);
    const equipments = await res.json();

    const container = document.getElementById("equipment-container");
    if (!container) return;

    container.innerHTML = "";

    equipments.forEach(eq => {
        const card = document.createElement("div");
        card.className = "card equipment-card";

        card.innerHTML = `
            <div class="card-header">
                <div class="card-title">${eq.name}</div>
                <button class="delete-btn" data-id="${eq.id}">🗑</button>
            </div>
            <div class="card-sub">号機: ${eq.unit_no ?? "-"}</div>
            <div class="card-sub">管理番号: ${eq.management_no ?? "-"}</div>
        `;

        // カードクリック → 詳細へ  
        card.onclick = (e) => {
            if (e.target.classList.contains("delete-btn")) return;

            const params = new URLSearchParams(window.location.search);
            const processId = params.get("process_id");
            const departmentId = params.get("department_id");
            const date = params.get("date");

            const dateParam = date ? `&date=${encodeURIComponent(date)}` : "";

            window.location.href =
                `equipment_detail.html?equipment_id=${eq.id}&process_id=${processId}&department_id=${departmentId}${dateParam}`;
        };

        // 削除
        card.querySelector(".delete-btn").onclick = async (e) => {
            e.stopPropagation();

            if (!confirm("この設備を削除しますか？")) return;

            try {
                await deleteEquipment(eq.id);
                loadEquipments(process_id);
            } catch (err) {
                alert("削除に失敗しました");
            }
        };

        container.appendChild(card);
    });
}

// ===============================
// 点検項目カード（完全版）
// ===============================
function renderInspectionItemCard(item) {
    const card = document.createElement("div");
    card.className = "item-card";
    card.dataset.id = item.id;

    let bandClass = "";
    if (item.type === "okng") bandClass = "band-okng";
    if (item.type === "numeric") bandClass = "band-numeric";
    if (item.type === "text") bandClass = "band-text";

    card.innerHTML = `
        <button class="edit-btn" data-id="${item.id}">✎</button>
        <button class="delete-btn" data-id="${item.id}">🗑️</button>

        <div class="item-band ${bandClass}"></div>

        <div class="item-content">
            <div class="item-title">${item.name}</div>
            <div class="item-sub"></div>
        </div>
    `;

    return card;
}

// ===============================
// 点検項目一覧
// ===============================
async function loadInspectionItems(equipmentId) {
    const container = document.getElementById("item-container");
    if (!container) return;

    const res = await fetch(`${API_BASE}/inspection_items/?equipment_id=${equipmentId}`);
    const items = await res.json();

    container.innerHTML = "";

    items.forEach(item => {
        const card = renderInspectionItemCard(item);
        container.appendChild(card);
    });
}

// ===============================
// 点検項目削除イベント
// ===============================
document.addEventListener("click", async (e) => {
    if (e.target.classList.contains("delete-btn")) {
        const itemId = e.target.dataset.id;

        if (!confirm("この点検項目を削除しますか？")) return;

        const res = await fetch(`${API_BASE}/inspection_items/${itemId}`, {
            method: "DELETE"
        });

        const data = await res.json();
        if (data.status === "deleted") {
            document.querySelector(`.item-card[data-id="${itemId}"]`).remove();
            
        }
    }
});
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("edit-btn")) {
        const itemId = e.target.dataset.id;
        openEditInspectionItemDialog(itemId);
    }
});
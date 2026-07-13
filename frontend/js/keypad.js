let activeInput = null;

function openKeypad(targetInput) {
    activeInput = targetInput;
    document.getElementById("keypad-display").textContent = targetInput.value || "";
    document.getElementById("keypad").classList.remove("hidden");
}

function closeKeypad() {
    document.getElementById("keypad").classList.add("hidden");
}

document.querySelectorAll(".keypad-grid button").forEach(btn => {
    btn.addEventListener("click", () => {
        const key = btn.dataset.key;
        const display = document.getElementById("keypad-display");

        if (key === "del") {
            display.textContent = display.textContent.slice(0, -1);
        } else {
            display.textContent += key;
        }
                // ★ マイナスの特別ルール
        if (key === "-") {
            // 先頭にしか付けられない
            if (display.textContent.startsWith("-")) return;
            display.textContent = "-" + display.textContent;
            return;
        }
    });
});

document.getElementById("keypad-ok").onclick = () => {
    if (activeInput) {
        activeInput.value = document.getElementById("keypad-display").textContent;
    }
    closeKeypad();
};
// ★ numeric-input をタップしたらテンキーを開く
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("numeric-input")) {
        e.preventDefault();
        openKeypad(e.target);
    }
});


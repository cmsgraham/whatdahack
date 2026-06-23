CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$;
    const root = (CTFd.config && CTFd.config.urlRoot) || "";

    // A single shared countdown timer across modal opens.
    if (window._wdhTimer) {
        clearInterval(window._wdhTimer);
        window._wdhTimer = null;
    }
    if (window._wdhPoll) {
        clearTimeout(window._wdhPoll);
        window._wdhPoll = null;
    }

    const panel = document.getElementById("wdh-instance-panel");
    if (!panel) {
        return; // not an instance challenge view
    }
    const body = document.getElementById("wdh-instance-body");
    const challengeId = panel.getAttribute("data-challenge-id");
    const connectMode = panel.getAttribute("data-connect-mode") || "ssh";

    const API = "/plugins/instance_challenges/instances";

    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function jfetch(path, opts) {
        return CTFd.fetch(path, opts).then((r) =>
            r.json().then((j) => ({ ok: r.ok, status: r.status, body: j }))
        );
    }

    function setBusy(text) {
        body.innerHTML =
            '<div class="wdh-muted"><i class="fas fa-circle-notch fa-spin"></i> ' +
            esc(text) +
            "</div>";
    }

    function showError(msg) {
        body.innerHTML =
            '<div class="wdh-muted" style="color:#f0a4a4;">' + esc(msg) + "</div>" +
            renderLaunchButton();
        wireLaunch();
    }

    function renderLaunchButton() {
        return (
            '<button type="button" class="btn btn-primary wdh-launch">' +
            '<i class="fas fa-play"></i> Launch Instance</button>'
        );
    }

    function copyBtn(value, label) {
        return (
            '<button type="button" class="btn btn-sm btn-outline-secondary wdh-copy" ' +
            'data-copy="' + esc(value) + '" title="Copy ' + esc(label) + '">' +
            '<i class="fas fa-copy"></i></button>'
        );
    }

    function fmtCountdown(secsLeft) {
        if (secsLeft <= 0) return "expired";
        const m = Math.floor(secsLeft / 60);
        const s = secsLeft % 60;
        return m + "m " + (s < 10 ? "0" + s : s) + "s";
    }

    function renderRunning(d) {
        const sshLine = "ssh " + d.ssh_user + "@" + d.ssh_host + " -p " + d.ssh_port;
        let rows = "";

        if (connectMode === "ssh" || connectMode === "both") {
            rows +=
                '<div class="wdh-row"><span class="wdh-k">SSH</span>' +
                '<code class="wdh-v">' + esc(sshLine) + "</code>" +
                copyBtn(sshLine, "SSH command") + "</div>";
            rows +=
                '<div class="wdh-row"><span class="wdh-k">Password</span>' +
                '<code class="wdh-v">' +
                (d.ssh_password ? esc(d.ssh_password) : "&middot;&middot;&middot; (shown at launch)") +
                "</code>" +
                (d.ssh_password ? copyBtn(d.ssh_password, "password") : "") +
                "</div>";
        }

        if (connectMode === "console" || connectMode === "both") {
            if (d.console_url) {
                rows +=
                    '<div class="wdh-row"><span class="wdh-k">Console</span>' +
                    '<a class="wdh-v" target="_blank" rel="noopener" href="' +
                    esc(d.console_url) + '">Open browser console</a></div>';
            } else {
                rows +=
                    '<div class="wdh-row"><span class="wdh-k">Console</span>' +
                    '<span class="wdh-v wdh-muted">browser console coming soon</span></div>';
            }
        }

        body.innerHTML =
            '<div class="wdh-running">' +
            rows +
            '<div class="wdh-row"><span class="wdh-k">Expires</span>' +
            '<span class="wdh-v" id="wdh-countdown">—</span></div>' +
            '<div class="wdh-actions">' +
            '<button type="button" class="btn btn-sm btn-secondary wdh-extend"><i class="fas fa-clock"></i> Extend 30m</button>' +
            '<button type="button" class="btn btn-sm btn-danger wdh-terminate"><i class="fas fa-stop"></i> Terminate</button>' +
            "</div></div>";

        startCountdown(d.expires_at);
        wireCopy();
        wireRunningActions(d.id);
    }

    function startCountdown(expiresAt) {
        const el = document.getElementById("wdh-countdown");
        function tick() {
            if (!document.getElementById("wdh-countdown")) {
                clearInterval(window._wdhTimer);
                window._wdhTimer = null;
                return;
            }
            const left = Math.floor(expiresAt - Date.now() / 1000);
            el.textContent = fmtCountdown(left);
            el.style.color = left < 120 ? "#f0a4a4" : "";
            if (left <= 0) {
                clearInterval(window._wdhTimer);
                window._wdhTimer = null;
                refresh();
            }
        }
        tick();
        window._wdhTimer = setInterval(tick, 1000);
    }

    function render(d) {
        if (window._wdhTimer) {
            clearInterval(window._wdhTimer);
            window._wdhTimer = null;
        }
        if (window._wdhPoll) {
            clearTimeout(window._wdhPoll);
            window._wdhPoll = null;
        }
        if (d && (d.status === "starting" || d.status === "created")) {
            // Container is up but the SSH/console port is not accepting yet.
            setBusy("Starting your instance… waiting for it to come online");
            window._wdhPoll = setTimeout(refresh, 3000);
            return;
        }
        if (d && (d.status === "running" || d.status === "restarting")) {
            renderRunning(d);
        } else {
            body.innerHTML =
                '<p class="wdh-muted">Launch your own private, sandboxed instance for this challenge.</p>' +
                renderLaunchButton();
            wireLaunch();
        }
    }

    function refresh() {
        jfetch(API + "?challenge_id=" + encodeURIComponent(challengeId), { method: "GET" })
            .then((res) => {
                if (res.ok && res.body.success) {
                    render(res.body.data);
                } else {
                    showError((res.body && res.body.message) || "Failed to load instance");
                }
            })
            .catch(() => showError("Network error"));
    }

    function wireLaunch() {
        const btn = body.querySelector(".wdh-launch");
        if (!btn) return;
        btn.addEventListener("click", () => {
            setBusy("Launching instance… this can take a few seconds");
            jfetch(API, {
                method: "POST",
                body: JSON.stringify({ challenge_id: parseInt(challengeId, 10) }),
            })
                .then((res) => {
                    if (res.ok && res.body.success) {
                        render(res.body.data);
                    } else {
                        showError((res.body && res.body.message) || "Launch failed");
                    }
                })
                .catch(() => showError("Network error"));
        });
    }

    function wireRunningActions(instanceId) {
        const ext = body.querySelector(".wdh-extend");
        const term = body.querySelector(".wdh-terminate");
        if (ext) {
            ext.addEventListener("click", () => {
                ext.disabled = true;
                jfetch(API + "/" + encodeURIComponent(instanceId) + "/extend", {
                    method: "POST",
                })
                    .then((res) => {
                        if (res.ok && res.body.success) {
                            render(res.body.data);
                        } else {
                            ext.disabled = false;
                            alert((res.body && res.body.message) || "Extend failed");
                        }
                    })
                    .catch(() => {
                        ext.disabled = false;
                    });
            });
        }
        if (term) {
            term.addEventListener("click", () => {
                if (!confirm("Terminate this instance? Your progress inside it will be lost.")) {
                    return;
                }
                term.disabled = true;
                setBusy("Terminating…");
                jfetch(API + "/" + encodeURIComponent(instanceId), { method: "DELETE" })
                    .then((res) => {
                        if (res.ok && res.body.success) {
                            render(null);
                        } else {
                            showError((res.body && res.body.message) || "Terminate failed");
                        }
                    })
                    .catch(() => showError("Network error"));
            });
        }
    }

    function wireCopy() {
        body.querySelectorAll(".wdh-copy").forEach((b) => {
            b.addEventListener("click", () => {
                const val = b.getAttribute("data-copy");
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(val);
                }
                const icon = b.querySelector("i");
                if (icon) {
                    icon.className = "fas fa-check";
                    setTimeout(() => (icon.className = "fas fa-copy"), 1200);
                }
            });
        });
    }

    refresh();
});


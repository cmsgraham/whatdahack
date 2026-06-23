// Standard CTFd challenge-type interface. The active "core" theme drives the
// challenge modal via an Alpine component that calls these hooks; if they are
// missing it throws "o.preRender is not a function". We run our instance panel
// bootstrap from postRender (the challenge HTML, incl. #wdh-instance-panel, is
// server-rendered into the modal before this runs).
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function () {};
CTFd._internal.challenge.render = null;
CTFd._internal.challenge.postRender = function () {
    var data = CTFd._internal.challenge.data || {};
    // Only instance challenges render the #wdh-instance-panel; skip others so we
    // don't poll the DOM needlessly.
    if (data.type !== "instance") {
        return;
    }
    // The active "core" theme injects the challenge HTML reactively (Vue/Alpine),
    // but calls postRender() as soon as this script's onload fires. When the
    // script is cached the panel may not be in the DOM yet, so a plain
    // initInstancePanel() would hit `if (!panel) return;` and the spinner would
    // stay on "Checking instance…" forever. Wait for the panel to appear first.
    waitForInstancePanel(0);
};

function waitForInstancePanel(attempt) {
    var panel = document.getElementById("wdh-instance-panel");
    if (!panel) {
        if (attempt < 50) {
            // ~5s total at 100ms intervals — plenty for the reactive render.
            setTimeout(function () {
                waitForInstancePanel(attempt + 1);
            }, 100);
        }
        return;
    }
    try {
        initInstancePanel();
    } catch (e) {
        // Never let panel errors break the core challenge modal.
        console.error("instance panel init failed", e);
    }
}
CTFd._internal.challenge.submit = function (preview) {
    var challenge_id = parseInt(CTFd.lib.$("#challenge-id").val());
    var submission = CTFd.lib.$("#challenge-input").val();
    var body = { challenge_id: challenge_id, submission: submission };
    var params = {};
    if (preview) {
        params["preview"] = true;
    }
    return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
        if (response.status === 429) {
            return response;
        }
        if (response.status === 403) {
            return response;
        }
        return response;
    });
};

function initInstancePanel() {
    const $ = CTFd.lib.$;
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

        const hardcap = d.hardcap || 0;
        // At the hard cap there is nothing left to extend into.
        const atCap = hardcap > 0 && hardcap - (d.expires_at || 0) <= 60;
        const capLine = hardcap
            ? new Date(hardcap * 1000).toLocaleTimeString()
            : null;

        const extendBtn = atCap
            ? '<button type="button" class="btn btn-sm btn-secondary wdh-extend" disabled title="Maximum lifetime reached"><i class="fas fa-clock"></i> Max lifetime reached</button>'
            : '<button type="button" class="btn btn-sm btn-secondary wdh-extend"><i class="fas fa-clock"></i> Extend 30m</button>';

        body.innerHTML =
            '<div class="wdh-running">' +
            '<div class="wdh-warn" id="wdh-warn" style="display:none;"></div>' +
            rows +
            '<div class="wdh-row"><span class="wdh-k">Expires</span>' +
            '<span class="wdh-v" id="wdh-countdown">—</span></div>' +
            (capLine
                ? '<div class="wdh-row"><span class="wdh-k">Max session</span>' +
                  '<span class="wdh-v wdh-muted">until ' + esc(capLine) +
                  ' · active sessions auto-renew</span></div>'
                : "") +
            '<div class="wdh-actions">' +
            extendBtn +
            '<button type="button" class="btn btn-sm btn-danger wdh-terminate"><i class="fas fa-stop"></i> Terminate</button>' +
            "</div></div>";

        startCountdown(d.expires_at, atCap);
        wireCopy();
        wireRunningActions(d.id);
    }

    function startCountdown(expiresAt, atCap) {
        const el = document.getElementById("wdh-countdown");
        const warn = document.getElementById("wdh-warn");
        function tick() {
            if (!document.getElementById("wdh-countdown")) {
                clearInterval(window._wdhTimer);
                window._wdhTimer = null;
                return;
            }
            const left = Math.floor(expiresAt - Date.now() / 1000);
            el.textContent = fmtCountdown(left);
            el.style.color = left < 120 ? "#f0a4a4" : "";
            // Pre-reclaim warning inside the last 5 minutes.
            if (warn) {
                if (left > 0 && left < 300) {
                    warn.style.display = "";
                    warn.innerHTML =
                        '<i class="fas fa-triangle-exclamation"></i> ' +
                        (atCap
                            ? "This instance has reached its maximum lifetime and will be reclaimed soon. Finish up or relaunch."
                            : "Expiring soon — click <strong>Extend 30m</strong> to keep it. Active SSH/console sessions are auto-renewed.");
                } else {
                    warn.style.display = "none";
                }
            }
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
}


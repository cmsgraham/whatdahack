"""
whatdahack instance_challenges plugin
=====================================

Adds an "instance" challenge type to CTFd. An instance challenge launches a
per-user ephemeral Docker container (an "instance") on the dedicated runner host
via the Instance Manager broker API (see /instancer/manager).

Phase 2 scope (this file):
  * Register the "instance" challenge type (admin create/update/read).
  * Store per-challenge instance config (image, connect mode, TTL, resource
    limits, egress allow-list) in a child table `instance_challenge`.
  * Provide an admin settings page to configure the Manager connection
    (URL + token), the public SSH host, and the curated image allow-list.
  * Expose the allow-list to the challenge form via a small admin JSON endpoint.

The player-facing launch/connect UI and the actual broker calls live in Phase 3.
"""
import requests
from flask import Blueprint, jsonify, render_template, request

from CTFd.cache import cache
from CTFd.models import Challenges, db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
    register_plugin_stylesheet,
)
from CTFd.plugins.challenges import CHALLENGE_CLASSES, BaseChallenge
from CTFd.plugins.migrations import upgrade
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user

# ---------------------------------------------------------------------------
# Config helpers (stored in CTFd's config table via get_config/set_config)
# ---------------------------------------------------------------------------
CFG_MANAGER_URL = "instance:manager_url"
CFG_MANAGER_TOKEN = "instance:manager_token"
CFG_SSH_HOST = "instance:ssh_host"
CFG_ALLOWED_IMAGES = "instance:allowed_images"


def get_allowed_images():
    """Return the curated image allow-list as a list of strings."""
    raw = get_config(CFG_ALLOWED_IMAGES) or ""
    images = []
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            images.append(line)
    return images


def get_manager_config():
    """Return (url, token) for the Instance Manager broker."""
    return (get_config(CFG_MANAGER_URL) or "", get_config(CFG_MANAGER_TOKEN) or "")


# Cache key prefix for the one-time SSH password (so the owner can re-reveal it
# while the modal is open without us persisting it on the runner).
PW_CACHE_PREFIX = "instance:pw:"
PW_CACHE_TTL = 6 * 60 * 60  # 6h — matches the Manager hard lifetime cap


class ManagerError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)


def _manager_request(method, path, *, params=None, json_body=None, timeout=10):
    """Call the Instance Manager broker with the configured bearer token.

    Raises ManagerError on transport failure or non-2xx responses.
    """
    url, token = get_manager_config()
    if not url:
        raise ManagerError(503, "Instance Manager is not configured")
    full = url.rstrip("/") + path
    try:
        resp = requests.request(
            method,
            full,
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise ManagerError(502, f"Manager unreachable: {e}")

    if resp.status_code >= 400:
        # Surface the Manager's structured error when present.
        try:
            detail = resp.json().get("detail")
        except ValueError:
            detail = resp.text[:200]
        raise ManagerError(resp.status_code, detail or "Manager error")

    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()



# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class InstanceChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "instance"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    # Docker image to launch. Must be present in the admin allow-list.
    # (The parent `Challenges.image` column already exists, but we keep an
    #  explicit child column so instance config is self-contained.)
    instance_image = db.Column(db.Text)
    # "ssh", "console", or "both" — how the player connects.
    connect_mode = db.Column(db.String(16), default="ssh")
    # Optional per-challenge overrides (NULL -> Manager defaults).
    ttl_minutes = db.Column(db.Integer)
    memory_mb = db.Column(db.Integer)
    cpus = db.Column(db.String(8))
    pids = db.Column(db.Integer)
    # Newline-separated egress allow-list (host or host:port). NULL -> deny all.
    egress = db.Column(db.Text)

    def __init__(self, *args, **kwargs):
        super(InstanceChallenge, self).__init__(**kwargs)


def _coerce_int(value):
    if value in (None, "", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_cpus(value):
    if value in (None, "", "null"):
        return None
    try:
        # validate it parses as a float, but store the canonical string
        return str(float(value))
    except (TypeError, ValueError):
        return None


def _sanitize_instance_fields(data):
    """Coerce instance-specific form fields in place (mutates `data`)."""
    if "ttl_minutes" in data:
        data["ttl_minutes"] = _coerce_int(data["ttl_minutes"])
    if "memory_mb" in data:
        data["memory_mb"] = _coerce_int(data["memory_mb"])
    if "pids" in data:
        data["pids"] = _coerce_int(data["pids"])
    if "cpus" in data:
        data["cpus"] = _coerce_cpus(data["cpus"])
    if "connect_mode" in data:
        mode = (data["connect_mode"] or "ssh").strip().lower()
        data["connect_mode"] = mode if mode in ("ssh", "console", "both") else "ssh"
    if "egress" in data:
        egress = (data["egress"] or "").strip()
        data["egress"] = egress or None
    if "instance_image" in data:
        data["instance_image"] = (data["instance_image"] or "").strip() or None
    return data


# ---------------------------------------------------------------------------
# Challenge type
# ---------------------------------------------------------------------------
class InstanceValueChallenge(BaseChallenge):
    id = "instance"
    name = "instance"
    templates = {
        "create": "/plugins/instance_challenges/assets/create.html",
        "update": "/plugins/instance_challenges/assets/update.html",
        "view": "/plugins/instance_challenges/assets/view.html",
    }
    scripts = {
        "create": "/plugins/instance_challenges/assets/create.js",
        "update": "/plugins/instance_challenges/assets/update.js",
        "view": "/plugins/instance_challenges/assets/view.js",
    }
    route = "/plugins/instance_challenges/assets/"
    blueprint = Blueprint(
        "instance_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = InstanceChallenge

    @classmethod
    def create(cls, request):
        data = request.form or request.get_json()
        data = dict(data)
        if "practice" in data:
            data["practice"] = data["practice"] in (True, "true", "True", "1", 1)
        _sanitize_instance_fields(data)

        challenge = cls.challenge_model(**data)
        db.session.add(challenge)
        db.session.commit()
        return challenge

    @classmethod
    def read(cls, challenge):
        challenge = InstanceChallenge.query.filter_by(id=challenge.id).first()
        data = super().read(challenge)
        data.update(
            {
                "instance_image": challenge.instance_image,
                "connect_mode": challenge.connect_mode,
                "ttl_minutes": challenge.ttl_minutes,
                "memory_mb": challenge.memory_mb,
                "cpus": challenge.cpus,
                "pids": challenge.pids,
                "egress": challenge.egress,
            }
        )
        return data

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json()
        data = dict(data)
        _sanitize_instance_fields(data)

        for attr, value in data.items():
            if attr == "practice":
                value = value in (True, "true", "True", "1", 1)
            setattr(challenge, attr, value)

        db.session.commit()
        return challenge


# ---------------------------------------------------------------------------
# Admin settings blueprint
# ---------------------------------------------------------------------------
def _register_admin_routes(app):
    admin_bp = Blueprint(
        "instance_admin",
        __name__,
        template_folder="templates",
    )

    @admin_bp.route("/admin/instances/settings", methods=["GET", "POST"])
    @admins_only
    def settings():
        if request.method == "POST":
            set_config(CFG_MANAGER_URL, (request.form.get("manager_url") or "").strip())
            set_config(
                CFG_MANAGER_TOKEN, (request.form.get("manager_token") or "").strip()
            )
            set_config(CFG_SSH_HOST, (request.form.get("ssh_host") or "").strip())
            set_config(
                CFG_ALLOWED_IMAGES, (request.form.get("allowed_images") or "").strip()
            )
        return render_template(
            "instance_admin_settings.html",
            manager_url=get_config(CFG_MANAGER_URL) or "",
            manager_token=get_config(CFG_MANAGER_TOKEN) or "",
            ssh_host=get_config(CFG_SSH_HOST) or "",
            allowed_images=get_config(CFG_ALLOWED_IMAGES) or "",
        )

    @admin_bp.route("/admin/instances/images", methods=["GET"])
    @admins_only
    def images():
        return jsonify({"images": get_allowed_images()})

    @admin_bp.route("/admin/instances/test", methods=["POST"])
    @admins_only
    def test_connection():
        url, token = get_manager_config()
        if not url:
            return jsonify({"success": False, "message": "Manager URL not set"}), 400
        try:
            resp = requests.get(
                url.rstrip("/") + "/health",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            ok = resp.status_code == 200
            return jsonify(
                {
                    "success": ok,
                    "message": resp.text[:300],
                    "status": resp.status_code,
                }
            )
        except requests.RequestException as e:
            return jsonify({"success": False, "message": str(e)}), 502

    app.register_blueprint(admin_bp)


# ---------------------------------------------------------------------------
# Player-facing API (proxies to the Manager; the broker token never leaves
# the server). All routes require an authenticated, non-admin-or-admin user.
# ---------------------------------------------------------------------------
def _instance_owner_id(user):
    """Per-user instances: the owner is always the individual user."""
    return user.id


def _load_instance_challenge(challenge_id):
    chal = InstanceChallenge.query.filter_by(id=challenge_id).first()
    return chal


def _public_instance(info, *, password=None, connect_mode=None):
    """Strip the Manager payload down to what the browser is allowed to see."""
    if info is None:
        return None
    return {
        "id": info.get("id"),
        "status": info.get("status"),
        "ready": info.get("ready", False),
        "ssh_host": info.get("ssh_host"),
        "ssh_port": info.get("ssh_port"),
        "ssh_user": info.get("ssh_user", "player"),
        "ssh_password": password if password is not None else info.get("ssh_password"),
        "console_url": info.get("console_url"),
        "expires_at": info.get("expires_at"),
        "hardcap": info.get("hardcap"),
        "created_at": info.get("created_at"),
        "connect_mode": connect_mode or info.get("connect_mode"),
    }


def _register_player_routes(app):
    player_bp = Blueprint("instance_player", __name__)

    @player_bp.route("/plugins/instance_challenges/instances", methods=["GET"])
    @authed_only
    def status():
        user = get_current_user()
        try:
            challenge_id = int(request.args.get("challenge_id", ""))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "challenge_id required"}), 400

        chal = _load_instance_challenge(challenge_id)
        if chal is None:
            return jsonify({"success": False, "message": "Not an instance challenge"}), 404

        owner_id = _instance_owner_id(user)
        try:
            instances = _manager_request(
                "GET",
                "/instances",
                params={"owner_id": owner_id, "challenge_id": challenge_id},
            )
        except ManagerError as e:
            return jsonify({"success": False, "message": e.message}), e.status

        info = instances[0] if instances else None
        password = None
        if info:
            password = cache.get(PW_CACHE_PREFIX + info["id"])
        return jsonify(
            {
                "success": True,
                "data": _public_instance(
                    info, password=password, connect_mode=chal.connect_mode
                ),
            }
        )

    @player_bp.route("/plugins/instance_challenges/instances", methods=["POST"])
    @authed_only
    def launch():
        user = get_current_user()
        body = request.get_json(silent=True) or {}
        try:
            challenge_id = int(body.get("challenge_id"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "challenge_id required"}), 400

        chal = _load_instance_challenge(challenge_id)
        if chal is None:
            return jsonify({"success": False, "message": "Not an instance challenge"}), 404
        if chal.state != "visible":
            return jsonify({"success": False, "message": "Challenge is not available"}), 403
        if not chal.instance_image:
            return jsonify({"success": False, "message": "No image configured"}), 400

        # Only allow images the admin has whitelisted.
        if chal.instance_image not in get_allowed_images():
            return (
                jsonify({"success": False, "message": "Image is not allow-listed"}),
                400,
            )

        owner_id = _instance_owner_id(user)
        payload = {
            "challenge_id": challenge_id,
            "owner_id": owner_id,
            "image": chal.instance_image,
            "connect_mode": chal.connect_mode or "ssh",
        }
        if chal.ttl_minutes:
            payload["ttl_minutes"] = chal.ttl_minutes
        if chal.memory_mb:
            payload["mem_mb"] = chal.memory_mb
        if chal.cpus:
            try:
                payload["cpus"] = float(chal.cpus)
            except (TypeError, ValueError):
                pass
        if chal.pids:
            payload["pids"] = chal.pids

        try:
            info = _manager_request("POST", "/instances", json_body=payload)
        except ManagerError as e:
            # 409 -> already running; return the existing instance instead of erroring.
            if e.status == 409:
                try:
                    existing = _manager_request(
                        "GET",
                        "/instances",
                        params={"owner_id": owner_id, "challenge_id": challenge_id},
                    )
                    info = existing[0] if existing else None
                    if info:
                        pw = cache.get(PW_CACHE_PREFIX + info["id"])
                        return jsonify(
                            {
                                "success": True,
                                "data": _public_instance(
                                    info, password=pw, connect_mode=chal.connect_mode
                                ),
                            }
                        )
                except ManagerError:
                    pass
                return jsonify({"success": False, "message": "Instance already running"}), 409
            return jsonify({"success": False, "message": e.message}), e.status

        # Cache the one-time password so the owner can re-reveal it.
        if info and info.get("ssh_password"):
            cache.set(
                PW_CACHE_PREFIX + info["id"], info["ssh_password"], timeout=PW_CACHE_TTL
            )
        return jsonify(
            {
                "success": True,
                "data": _public_instance(info, connect_mode=chal.connect_mode),
            }
        )

    @player_bp.route(
        "/plugins/instance_challenges/instances/<instance_id>/extend", methods=["POST"]
    )
    @authed_only
    def extend(instance_id):
        user = get_current_user()
        owner_id = _instance_owner_id(user)
        # Verify ownership before mutating (IDOR protection).
        try:
            info = _manager_request("GET", f"/instances/{instance_id}")
        except ManagerError as e:
            return jsonify({"success": False, "message": e.message}), e.status
        if not info or int(info.get("owner_id", -1)) != owner_id:
            return jsonify({"success": False, "message": "Not found"}), 404

        try:
            info = _manager_request(
                "POST", f"/instances/{instance_id}/extend", params={"minutes": 30}
            )
        except ManagerError as e:
            return jsonify({"success": False, "message": e.message}), e.status
        pw = cache.get(PW_CACHE_PREFIX + instance_id)
        return jsonify({"success": True, "data": _public_instance(info, password=pw)})

    @player_bp.route(
        "/plugins/instance_challenges/instances/<instance_id>", methods=["DELETE"]
    )
    @authed_only
    def terminate(instance_id):
        user = get_current_user()
        owner_id = _instance_owner_id(user)
        try:
            info = _manager_request("GET", f"/instances/{instance_id}")
        except ManagerError as e:
            return jsonify({"success": False, "message": e.message}), e.status
        if not info or int(info.get("owner_id", -1)) != owner_id:
            return jsonify({"success": False, "message": "Not found"}), 404

        try:
            _manager_request("DELETE", f"/instances/{instance_id}")
        except ManagerError as e:
            return jsonify({"success": False, "message": e.message}), e.status
        cache.delete(PW_CACHE_PREFIX + instance_id)
        return jsonify({"success": True})

    app.register_blueprint(player_bp)


# ---------------------------------------------------------------------------
# Plugin entrypoint
# ---------------------------------------------------------------------------
def load(app):
    upgrade(plugin_name="instance_challenges")
    CHALLENGE_CLASSES["instance"] = InstanceValueChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/instance_challenges/assets/"
    )
    register_plugin_stylesheet(
        "/plugins/instance_challenges/assets/instance.css"
    )
    _register_admin_routes(app)
    _register_player_routes(app)
    register_admin_plugin_menu_bar("Instances", "/admin/instances/settings")


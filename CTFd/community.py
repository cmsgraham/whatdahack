import datetime
import os
import uuid

from flask import Blueprint, abort, current_app, jsonify, render_template, request
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from CTFd.models import Awards, db
from CTFd.models.community import (
    CommunityAttempt,
    CommunityChallenge,
    CommunityRating,
    CommunitySolve,
)
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import authed, get_current_user, is_admin

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "zip", "tar", "gz", "7z", "rar", "pdf", "txt", "py", "c", "cpp", "pcap", "pcapng", "html", "htm", "js", "css", "json", "xml", "csv", "md", "sh", "rb", "java", "rs", "go", "sql", "dockerfile", "yaml", "yml", "toml", "ini", "conf", "log", "eml", "bmp", "svg"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

community = Blueprint("community", __name__)


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

VALID_CATEGORIES = (
    "web",
    "crypto",
    "pwn",
    "forensics",
    "reverse",
    "misc",
    "osint",
    "steganography",
)
VALID_DIFFICULTIES = ("easy", "medium", "hard", "insane")


# ──────────────────────────── HTML Views ────────────────────────────


@community.route("/community")
@authed_only
def browse():
    total_challenges = CommunityChallenge.query.filter_by(state="published").count()
    total_solves = (
        db.session.query(db.func.coalesce(db.func.sum(CommunityChallenge.solve_count), 0))
        .filter(CommunityChallenge.state == "published")
        .scalar()
    )
    total_authors = (
        db.session.query(db.func.count(db.func.distinct(CommunityChallenge.author_id)))
        .filter(CommunityChallenge.state == "published")
        .scalar()
    )
    return render_template(
        "community/browse.html",
        stats={
            "total_challenges": total_challenges,
            "total_solves": total_solves,
            "total_authors": total_authors,
        },
    )


@community.route("/community/create")
@authed_only
def create():
    return render_template("community/create.html")


@community.route("/community/edit/<int:challenge_id>")
@authed_only
def edit(challenge_id):
    ch = CommunityChallenge.query.get_or_404(challenge_id)
    user = get_current_user()
    if user.id != ch.author_id and not is_admin():
        abort(403)
    return render_template("community/edit.html", challenge_id=challenge_id)


@community.route("/community/challenge/<int:challenge_id>")
@authed_only
def detail(challenge_id):
    ch = CommunityChallenge.query.get_or_404(challenge_id)
    if ch.state != "published":
        if not authed():
            abort(404)
        user = get_current_user()
        if user.id != ch.author_id and not is_admin():
            abort(404)
    return render_template("community/detail.html", challenge_id=challenge_id)


# ──────────────────────────── JSON API ──────────────────────────────


def _serialize_challenge(c, solved_ids=None, user_ratings=None):
    return {
        "id": c.id,
        "title": c.title,
        "category": c.category,
        "difficulty": c.difficulty,
        "community_difficulty": c.community_difficulty,
        "points": c.points,
        "author": c.author.name if c.author else "Unknown",
        "author_id": c.author_id,
        "solve_count": c.solve_count,
        "attempt_count": c.attempt_count,
        "success_rate": c.success_rate,
        "thumbs_up": c.thumbs_up,
        "thumbs_down": c.thumbs_down,
        "rating_percent": c.rating_percent,
        "tags": c.tag_list,
        "banner_url": c.banner_url,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "solved": c.id in (solved_ids or set()),
        "user_rating": (user_ratings or {}).get(c.id),
    }


@community.route("/community/api/challenges", methods=["GET"])
@authed_only
def api_list_challenges():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    category = (request.args.get("category") or "").strip()
    difficulty = (request.args.get("difficulty") or "").strip()
    sort = (request.args.get("sort") or "newest").strip()
    search = (request.args.get("q") or "").strip()

    q = CommunityChallenge.query.filter_by(state="published")

    if category:
        q = q.filter(CommunityChallenge.category == category)
    if difficulty:
        q = q.filter(CommunityChallenge.difficulty == difficulty)
    if search:
        safe = search.replace("%", "\\%").replace("_", "\\_")
        q = q.filter(CommunityChallenge.title.ilike(f"%{safe}%"))

    if sort == "popular":
        q = q.order_by(CommunityChallenge.solve_count.desc())
    elif sort == "highest_rated":
        q = q.order_by(CommunityChallenge.thumbs_up.desc())
    elif sort == "most_solved":
        q = q.order_by(CommunityChallenge.solve_count.desc())
    elif sort == "unsolved":
        q = q.filter(CommunityChallenge.solve_count == 0).order_by(
            CommunityChallenge.created_at.desc()
        )
    elif sort == "trending":
        q = q.order_by(
            (CommunityChallenge.solve_count + CommunityChallenge.thumbs_up).desc()
        )
    else:
        q = q.order_by(CommunityChallenge.created_at.desc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    solved_ids = set()
    user_ratings = {}
    if authed():
        uid = get_current_user().id
        solved_ids = {
            s.challenge_id
            for s in CommunitySolve.query.filter_by(user_id=uid)
            .with_entities(CommunitySolve.challenge_id)
            .all()
        }
        user_ratings = {
            r.challenge_id: r.value
            for r in CommunityRating.query.filter_by(user_id=uid)
            .with_entities(CommunityRating.challenge_id, CommunityRating.value)
            .all()
        }

    return jsonify(
        {
            "success": True,
            "data": [
                _serialize_challenge(c, solved_ids, user_ratings)
                for c in pagination.items
            ],
            "meta": {
                "pagination": {
                    "page": pagination.page,
                    "pages": pagination.pages,
                    "per_page": pagination.per_page,
                    "total": pagination.total,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                }
            },
        }
    )


@community.route("/community/api/upload", methods=["POST"])
@authed_only
def api_upload_file():
    """Upload a file attachment for a community challenge."""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"success": False, "errors": ["No file provided"]}), 400
    if not _allowed_file(f.filename):
        return jsonify({"success": False, "errors": [f"File type not allowed: {f.filename}"]}), 400

    data = f.read()
    if len(data) > MAX_FILE_SIZE:
        return jsonify({"success": False, "errors": ["File too large (max 25 MB)"]}), 400
    f.seek(0)

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "/var/uploads")
    community_dir = os.path.join(upload_folder, "community")
    os.makedirs(community_dir, exist_ok=True)

    ext = f.filename.rsplit(".", 1)[1].lower()
    original = secure_filename(f.filename.rsplit(".", 1)[0])[:40]
    unique = uuid.uuid4().hex[:12]
    safe_name = secure_filename(f"{original}_{unique}.{ext}")
    filepath = os.path.join(community_dir, safe_name)

    with open(filepath, "wb") as dst:
        dst.write(data)

    url = f"/files/community/{safe_name}"
    return jsonify({"success": True, "data": {"url": url, "name": f.filename}})


@community.route("/community/api/challenges", methods=["POST"])
@authed_only
def api_create_challenge():
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "errors": ["No data provided"]}), 400

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category = (data.get("category") or "").strip()
    difficulty = (data.get("difficulty") or "").strip()
    points = data.get("points", 100)
    flag = (data.get("flag") or "").strip()
    case_insensitive = bool(data.get("case_insensitive", False))
    tags = (data.get("tags") or "").strip()
    attachment_url = (data.get("attachment_url") or "").strip() or None
    banner_url = (data.get("banner_url") or "").strip() or None
    state = data.get("state", "draft")

    errors = []
    if not title or len(title) > 200:
        errors.append("Title is required (max 200 characters)")
    if not description:
        errors.append("Description is required")
    if category not in VALID_CATEGORIES:
        errors.append("Invalid category")
    if difficulty not in VALID_DIFFICULTIES:
        errors.append("Invalid difficulty")
    if not isinstance(points, int) or points < 1 or points > 10000:
        errors.append("Points must be between 1 and 10,000")
    if not flag:
        errors.append("Flag is required")
    if state not in ("draft", "published"):
        errors.append("Invalid state")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    ch = CommunityChallenge(
        author_id=user.id,
        title=title,
        description=description,
        category=category,
        difficulty=difficulty,
        points=points,
        flag=flag,
        case_insensitive=case_insensitive,
        tags=tags,
        attachment_url=attachment_url,
        banner_url=banner_url,
        state=state,
    )
    db.session.add(ch)
    db.session.commit()

    return jsonify({"success": True, "data": {"id": ch.id, "state": ch.state}}), 201


@community.route("/community/api/challenges/<int:cid>", methods=["GET"])
@authed_only
def api_get_challenge(cid):
    ch = CommunityChallenge.query.get_or_404(cid)
    if ch.state != "published":
        if not authed():
            abort(404)
        u = get_current_user()
        if u.id != ch.author_id and not is_admin():
            abort(404)

    first_blood = CommunitySolve.query.filter_by(
        challenge_id=cid, is_first_blood=True
    ).first()
    recent_solves = (
        CommunitySolve.query.filter_by(challenge_id=cid)
        .order_by(CommunitySolve.solved_at.desc())
        .limit(10)
        .all()
    )

    user_solved = False
    user_rating = None
    is_author = False
    if authed():
        u = get_current_user()
        is_author = u.id == ch.author_id
        user_solved = (
            CommunitySolve.query.filter_by(challenge_id=cid, user_id=u.id).first()
            is not None
        )
        r = CommunityRating.query.filter_by(challenge_id=cid, user_id=u.id).first()
        user_rating = r.value if r else None

    return jsonify(
        {
            "success": True,
            "data": {
                "id": ch.id,
                "title": ch.title,
                "description": ch.description,
                "category": ch.category,
                "difficulty": ch.difficulty,
                "community_difficulty": ch.community_difficulty,
                "points": ch.points,
                "state": ch.state,
                "author": ch.author.name if ch.author else "Unknown",
                "author_id": ch.author_id,
                "tags": ch.tag_list,
                "attachment_url": ch.attachment_url,
                "banner_url": ch.banner_url,
                "solve_count": ch.solve_count,
                "attempt_count": ch.attempt_count,
                "success_rate": ch.success_rate,
                "thumbs_up": ch.thumbs_up,
                "thumbs_down": ch.thumbs_down,
                "rating_percent": ch.rating_percent,
                "created_at": ch.created_at.isoformat() if ch.created_at else None,
                "first_blood": (
                    {
                        "user": first_blood.user.name,
                        "user_id": first_blood.user_id,
                        "solved_at": first_blood.solved_at.isoformat(),
                    }
                    if first_blood
                    else None
                ),
                "recent_solves": [
                    {
                        "user": s.user.name,
                        "user_id": s.user_id,
                        "solved_at": s.solved_at.isoformat(),
                        "is_first_blood": s.is_first_blood,
                    }
                    for s in recent_solves
                ],
                "user_solved": user_solved,
                "user_rating": user_rating,
                "is_author": is_author,
                "flag": ch.flag if is_author else None,
                "case_insensitive": ch.case_insensitive if is_author else None,
            },
        }
    )


@community.route("/community/api/challenges/<int:cid>", methods=["PATCH"])
@authed_only
def api_update_challenge(cid):
    user = get_current_user()
    ch = CommunityChallenge.query.get_or_404(cid)
    if user.id != ch.author_id and not is_admin():
        abort(403)

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "errors": ["No data provided"]}), 400

    allowed = {
        "title",
        "description",
        "category",
        "difficulty",
        "points",
        "flag",
        "case_insensitive",
        "tags",
        "attachment_url",
        "banner_url",
        "state",
    }
    for key, val in data.items():
        if key not in allowed:
            continue
        if key == "title":
            v = (val or "").strip()
            if not v or len(v) > 200:
                return jsonify({"success": False, "errors": ["Invalid title"]}), 400
            ch.title = v
        elif key == "description":
            ch.description = (val or "").strip()
        elif key == "category":
            if val not in VALID_CATEGORIES:
                return jsonify({"success": False, "errors": ["Invalid category"]}), 400
            ch.category = val
        elif key == "difficulty":
            if val not in VALID_DIFFICULTIES:
                return (
                    jsonify({"success": False, "errors": ["Invalid difficulty"]}),
                    400,
                )
            ch.difficulty = val
        elif key == "points":
            if not isinstance(val, int) or val < 1 or val > 10000:
                return jsonify({"success": False, "errors": ["Invalid points"]}), 400
            ch.points = val
        elif key == "flag":
            v = (val or "").strip()
            if not v:
                return (
                    jsonify({"success": False, "errors": ["Flag is required"]}),
                    400,
                )
            ch.flag = v
        elif key == "case_insensitive":
            ch.case_insensitive = bool(val)
        elif key == "tags":
            ch.tags = (val or "").strip()
        elif key == "attachment_url":
            ch.attachment_url = (val or "").strip() or None
        elif key == "banner_url":
            ch.banner_url = (val or "").strip() or None
        elif key == "state":
            if val not in ("draft", "published", "archived"):
                return jsonify({"success": False, "errors": ["Invalid state"]}), 400
            ch.state = val

    ch.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "data": {"id": ch.id}})


@community.route("/community/api/challenges/<int:cid>/attempt", methods=["POST"])
@authed_only
def api_attempt_challenge(cid):
    user = get_current_user()
    ch = CommunityChallenge.query.get_or_404(cid)
    if ch.state != "published":
        abort(404)

    if user.id == ch.author_id:
        return (
            jsonify(
                {"success": False, "errors": ["You cannot solve your own challenge"]}
            ),
            400,
        )

    existing = CommunitySolve.query.filter_by(
        challenge_id=cid, user_id=user.id
    ).first()
    if existing:
        return (
            jsonify(
                {
                    "success": False,
                    "errors": ["Already solved"],
                    "already_solved": True,
                }
            ),
            400,
        )

    # Rate limit: 10 attempts per minute
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    recent = CommunityAttempt.query.filter(
        CommunityAttempt.challenge_id == cid,
        CommunityAttempt.user_id == user.id,
        CommunityAttempt.submitted_at > cutoff,
    ).count()
    if recent >= 10:
        return (
            jsonify(
                {"success": False, "errors": ["Too many attempts. Wait a moment."]}
            ),
            429,
        )

    data = request.get_json()
    submitted = (data.get("flag") or "").strip()
    if not submitted:
        return jsonify({"success": False, "errors": ["Flag is required"]}), 400

    stored = ch.flag.strip()
    if ch.case_insensitive:
        correct = submitted.lower() == stored.lower()
    else:
        correct = submitted == stored

    attempt = CommunityAttempt(
        challenge_id=cid, user_id=user.id, is_correct=correct
    )
    db.session.add(attempt)
    ch.attempt_count = CommunityChallenge.attempt_count + 1

    point_value = 0
    is_first = False

    if correct:
        is_first = ch.solve_count == 0
        solve = CommunitySolve(
            challenge_id=cid,
            user_id=user.id,
            is_first_blood=is_first,
        )
        db.session.add(solve)

        point_value = ch.points
        award = Awards(
            user_id=user.id,
            team_id=user.team_id,
            name=f"Community: {ch.title}"[:80],
            description=f"Solved community challenge"
            + (" (First Blood!)" if is_first else ""),
            value=point_value,
            category="community",
        )
        db.session.add(award)
        ch.solve_count = CommunityChallenge.solve_count + 1

        try:
            db.session.flush()
            solve.award_id = award.id
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return (
                jsonify({"success": False, "errors": ["Already solved"]}),
                400,
            )
    else:
        db.session.commit()

    return jsonify(
        {
            "success": True,
            "data": {
                "correct": correct,
                "is_first_blood": is_first,
                "points_awarded": point_value,
                "solve_count": ch.solve_count,
                "attempt_count": ch.attempt_count,
            },
        }
    )


@community.route("/community/api/challenges/<int:cid>/rate", methods=["POST"])
@authed_only
def api_rate_challenge(cid):
    user = get_current_user()
    ch = CommunityChallenge.query.get_or_404(cid)
    if ch.state != "published":
        abort(404)

    data = request.get_json()
    value = data.get("value")
    if value not in (1, -1):
        return jsonify({"success": False, "errors": ["Value must be 1 or -1"]}), 400

    existing = CommunityRating.query.filter_by(
        challenge_id=cid, user_id=user.id
    ).first()

    if existing:
        if existing.value == value:
            # Toggle off
            db.session.delete(existing)
            if value == 1:
                ch.thumbs_up = max(ch.thumbs_up - 1, 0)
            else:
                ch.thumbs_down = max(ch.thumbs_down - 1, 0)
            db.session.commit()
            db.session.refresh(ch)
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "action": "removed",
                        "thumbs_up": ch.thumbs_up,
                        "thumbs_down": ch.thumbs_down,
                        "rating_percent": ch.rating_percent,
                        "user_rating": None,
                    },
                }
            )
        else:
            # Switch vote
            existing.value = value
            if value == 1:
                ch.thumbs_up = ch.thumbs_up + 1
                ch.thumbs_down = max(ch.thumbs_down - 1, 0)
            else:
                ch.thumbs_down = ch.thumbs_down + 1
                ch.thumbs_up = max(ch.thumbs_up - 1, 0)
            db.session.commit()
            db.session.refresh(ch)
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "action": "changed",
                        "thumbs_up": ch.thumbs_up,
                        "thumbs_down": ch.thumbs_down,
                        "rating_percent": ch.rating_percent,
                        "user_rating": value,
                    },
                }
            )
    else:
        rating = CommunityRating(challenge_id=cid, user_id=user.id, value=value)
        db.session.add(rating)
        if value == 1:
            ch.thumbs_up = ch.thumbs_up + 1
        else:
            ch.thumbs_down = ch.thumbs_down + 1
        db.session.commit()
        db.session.refresh(ch)
        return jsonify(
            {
                "success": True,
                "data": {
                    "action": "created",
                    "thumbs_up": ch.thumbs_up,
                    "thumbs_down": ch.thumbs_down,
                    "rating_percent": ch.rating_percent,
                    "user_rating": value,
                },
            }
        )


@community.route("/community/api/categories", methods=["GET"])
@authed_only
def api_categories():
    rows = (
        db.session.query(
            CommunityChallenge.category, db.func.count(CommunityChallenge.id)
        )
        .filter_by(state="published")
        .group_by(CommunityChallenge.category)
        .all()
    )
    return jsonify(
        {"success": True, "data": [{"name": r[0], "count": r[1]} for r in rows]}
    )


@community.route("/community/api/my-challenges", methods=["GET"])
@authed_only
def api_my_challenges():
    user = get_current_user()
    items = (
        CommunityChallenge.query.filter_by(author_id=user.id)
        .order_by(CommunityChallenge.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "id": c.id,
                    "title": c.title,
                    "category": c.category,
                    "difficulty": c.difficulty,
                    "points": c.points,
                    "state": c.state,
                    "solve_count": c.solve_count,
                    "thumbs_up": c.thumbs_up,
                    "thumbs_down": c.thumbs_down,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in items
            ],
        }
    )

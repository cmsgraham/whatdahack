import datetime
import json
import os
import uuid

from flask import Blueprint, abort, current_app, jsonify, render_template, request
from sqlalchemy import case, desc, func
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from CTFd.models import db
from CTFd.models.social import (
    SocialComment,
    SocialFollow,
    SocialLike,
    SocialNotification,
    SocialPost,
    SocialReport,
)
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import authed, get_current_user, is_admin

social_feed = Blueprint("social_feed", __name__)

VALID_POST_TYPES = ("text", "solve", "discussion", "question")
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


# ─── helpers ────────────────────────────────────────────────────────


def _notify(user_id, actor_id, verb, post_id=None, comment_id=None):
    """Create notification if actor != user."""
    if user_id == actor_id:
        return
    n = SocialNotification(
        user_id=user_id,
        actor_id=actor_id,
        verb=verb,
        post_id=post_id,
        comment_id=comment_id,
    )
    db.session.add(n)


def _serialize_post(p, liked_ids=None, current_uid=None):
    return {
        "id": p.id,
        "author": {
            "id": p.author.id,
            "name": p.author.name,
            "avatar": p.author.avatar,
        }
        if p.author
        else None,
        "content": p.content,
        "post_type": p.post_type,
        "challenge_id": p.challenge_id,
        "challenge_name": p.challenge_ref.title if p.challenge_ref else None,
        "tags": p.tag_list,
        "image_url": p.image_url,
        "images": p.image_list,
        "link_url": p.link_url,
        "like_count": p.like_count,
        "comment_count": p.comment_count,
        "pinned": p.pinned,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "liked": p.id in (liked_ids or set()),
        "is_author": p.author_id == current_uid if current_uid else False,
    }


def _serialize_comment(c, liked_ids=None, current_uid=None):
    return {
        "id": c.id,
        "post_id": c.post_id,
        "parent_id": c.parent_id,
        "author": {
            "id": c.author.id,
            "name": c.author.name,
            "avatar": c.author.avatar,
        }
        if c.author
        else None,
        "content": c.content,
        "like_count": c.like_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "liked": c.id in (liked_ids or set()),
        "is_author": c.author_id == current_uid if current_uid else False,
        "replies": [],
    }


# ─── HTML views ─────────────────────────────────────────────────────


@social_feed.route("/feed")
@authed_only
def feed():
    return render_template("social/feed.html")


@social_feed.route("/feed/post/<int:post_id>")
@authed_only
def post_detail(post_id):
    p = SocialPost.query.get_or_404(post_id)
    if p.deleted and not is_admin():
        abort(404)
    return render_template("social/post_detail.html", post_id=post_id)


@social_feed.route("/feed/user/<int:user_id>")
@authed_only
def user_profile(user_id):
    from CTFd.models import Users

    u = Users.query.get_or_404(user_id)
    return render_template("social/profile.html", profile_user_id=user_id)


# ─── Image Upload ───────────────────────────────────────────────────


def _allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


@social_feed.route("/feed/api/upload", methods=["POST"])
@authed_only
def api_upload_image():
    """Upload one or more images for social posts. Returns list of URLs."""
    files = request.files.getlist("images")
    if not files or len(files) == 0:
        return jsonify({"success": False, "errors": ["No files provided"]}), 400
    if len(files) > 10:
        return jsonify({"success": False, "errors": ["Maximum 10 images"]}), 400

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "/var/uploads")
    social_dir = os.path.join(upload_folder, "social")
    os.makedirs(social_dir, exist_ok=True)

    urls = []
    for f in files:
        if not f or not f.filename:
            continue
        if not _allowed_image(f.filename):
            return jsonify({"success": False, "errors": [f"Invalid file type: {f.filename}"]}), 400

        # Read and check size
        data = f.read()
        if len(data) > MAX_IMAGE_SIZE:
            return jsonify({"success": False, "errors": ["Image too large (max 5MB)"]}), 400
        f.seek(0)

        ext = f.filename.rsplit(".", 1)[1].lower()
        unique = uuid.uuid4().hex[:16]
        safe_name = secure_filename(f"{unique}.{ext}")
        filepath = os.path.join(social_dir, safe_name)

        with open(filepath, "wb") as dst:
            dst.write(data)

        urls.append(f"/files/social/{safe_name}")

    return jsonify({"success": True, "data": {"urls": urls}})


# ─── Feed API ───────────────────────────────────────────────────────


@social_feed.route("/feed/api/posts", methods=["GET"])
@authed_only
def api_list_posts():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)
    mode = (request.args.get("mode") or "global").strip()
    sort = (request.args.get("sort") or "newest").strip()
    post_type = (request.args.get("type") or "").strip()
    search = (request.args.get("q") or "").strip()
    user_id = request.args.get("user_id", None, type=int)

    q = SocialPost.query.filter_by(deleted=False)

    if user_id:
        q = q.filter(SocialPost.author_id == user_id)

    if post_type and post_type in VALID_POST_TYPES:
        q = q.filter(SocialPost.post_type == post_type)

    if search:
        safe = search.replace("%", "\\%").replace("_", "\\_")
        q = q.filter(SocialPost.content.ilike(f"%{safe}%"))

    if mode == "following" and authed():
        uid = get_current_user().id
        following_ids = [
            f.following_id
            for f in SocialFollow.query.filter_by(follower_id=uid)
            .with_entities(SocialFollow.following_id)
            .all()
        ]
        following_ids.append(uid)
        q = q.filter(SocialPost.author_id.in_(following_ids))

    if sort == "trending":
        week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        q = q.filter(SocialPost.created_at > week_ago).order_by(
            desc(SocialPost.like_count + SocialPost.comment_count)
        )
    elif sort == "popular":
        q = q.order_by(desc(SocialPost.like_count))
    else:
        q = q.order_by(
            desc(SocialPost.pinned), desc(SocialPost.created_at)
        )

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    liked_ids = set()
    current_uid = None
    if authed():
        current_uid = get_current_user().id
        liked_ids = {
            lk.post_id
            for lk in SocialLike.query.filter(
                SocialLike.user_id == current_uid,
                SocialLike.post_id.isnot(None),
            )
            .with_entities(SocialLike.post_id)
            .all()
        }

    return jsonify(
        {
            "success": True,
            "data": [
                _serialize_post(p, liked_ids, current_uid)
                for p in pagination.items
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


# ─── Post CRUD ──────────────────────────────────────────────────────


@social_feed.route("/feed/api/posts", methods=["POST"])
@authed_only
def api_create_post():
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "errors": ["No data"]}), 400

    content = (data.get("content") or "").strip()
    images_list = data.get("images") or []
    if not content and not images_list:
        return jsonify({"success": False, "errors": ["Content or images required"]}), 400
    if len(content) > 10000:
        return jsonify({"success": False, "errors": ["Content too long (max 10,000 chars)"]}), 400

    post_type = data.get("post_type", "text")
    if post_type not in VALID_POST_TYPES:
        post_type = "text"

    challenge_id = data.get("challenge_id")
    if challenge_id is not None:
        try:
            challenge_id = int(challenge_id)
        except (ValueError, TypeError):
            challenge_id = None

    tags = (data.get("tags") or "").strip()
    image_url = (data.get("image_url") or "").strip() or None
    link_url = (data.get("link_url") or "").strip() or None

    # Support multiple images as JSON list
    images_list = data.get("images") or []
    if isinstance(images_list, list):
        # Validate each entry is a string
        images_list = [str(u) for u in images_list if u][:10]
    else:
        images_list = []
    images_json = json.dumps(images_list) if images_list else None

    # Use first image as image_url fallback
    if not image_url and images_list:
        image_url = images_list[0]

    p = SocialPost(
        author_id=user.id,
        content=content,
        post_type=post_type,
        challenge_id=challenge_id,
        tags=tags,
        image_url=image_url,
        images=images_json,
        link_url=link_url,
    )
    db.session.add(p)
    db.session.commit()

    return jsonify({"success": True, "data": {"id": p.id}}), 201


@social_feed.route("/feed/api/posts/<int:pid>", methods=["DELETE"])
@authed_only
def api_delete_post(pid):
    user = get_current_user()
    p = SocialPost.query.get_or_404(pid)
    if p.author_id != user.id and not is_admin():
        abort(403)
    p.deleted = True
    db.session.commit()
    return jsonify({"success": True})


@social_feed.route("/feed/api/posts/<int:pid>", methods=["GET"])
@authed_only
def api_get_post(pid):
    p = SocialPost.query.get_or_404(pid)
    if p.deleted and not is_admin():
        abort(404)

    liked_ids = set()
    current_uid = None
    if authed():
        current_uid = get_current_user().id
        lk = SocialLike.query.filter_by(user_id=current_uid, post_id=pid).first()
        if lk:
            liked_ids.add(pid)

    return jsonify(
        {"success": True, "data": _serialize_post(p, liked_ids, current_uid)}
    )


# ─── Like system ────────────────────────────────────────────────────


@social_feed.route("/feed/api/posts/<int:pid>/like", methods=["POST"])
@authed_only
def api_toggle_like_post(pid):
    user = get_current_user()
    p = SocialPost.query.get_or_404(pid)
    if p.deleted:
        abort(404)

    existing = SocialLike.query.filter_by(user_id=user.id, post_id=pid).first()
    if existing:
        db.session.delete(existing)
        p.like_count = max(p.like_count - 1, 0)
        db.session.commit()
        return jsonify(
            {"success": True, "data": {"liked": False, "like_count": p.like_count}}
        )
    else:
        lk = SocialLike(user_id=user.id, post_id=pid)
        db.session.add(lk)
        p.like_count = SocialPost.like_count + 1
        _notify(p.author_id, user.id, "liked_post", post_id=pid)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"success": True, "data": {"liked": True, "like_count": p.like_count}})
        return jsonify(
            {"success": True, "data": {"liked": True, "like_count": p.like_count}}
        )


# ─── Comments ───────────────────────────────────────────────────────


@social_feed.route("/feed/api/posts/<int:pid>/comments", methods=["GET"])
@authed_only
def api_list_comments(pid):
    p = SocialPost.query.get_or_404(pid)
    if p.deleted and not is_admin():
        abort(404)

    comments = (
        SocialComment.query.filter_by(post_id=pid, deleted=False)
        .order_by(SocialComment.created_at.asc())
        .all()
    )

    liked_ids = set()
    current_uid = None
    if authed():
        current_uid = get_current_user().id
        cids = [c.id for c in comments]
        if cids:
            liked_ids = {
                lk.comment_id
                for lk in SocialLike.query.filter(
                    SocialLike.user_id == current_uid,
                    SocialLike.comment_id.in_(cids),
                )
                .with_entities(SocialLike.comment_id)
                .all()
            }

    # Build threaded structure
    by_id = {}
    roots = []
    for c in comments:
        sc = _serialize_comment(c, liked_ids, current_uid)
        by_id[c.id] = sc
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id]["replies"].append(sc)
        else:
            roots.append(sc)

    return jsonify({"success": True, "data": roots})


@social_feed.route("/feed/api/posts/<int:pid>/comments", methods=["POST"])
@authed_only
def api_create_comment(pid):
    user = get_current_user()
    p = SocialPost.query.get_or_404(pid)
    if p.deleted:
        abort(404)

    data = request.get_json()
    content = (data.get("content") or "").strip()
    if not content or len(content) > 5000:
        return jsonify({"success": False, "errors": ["Content required (max 5,000 chars)"]}), 400

    parent_id = data.get("parent_id")
    if parent_id is not None:
        try:
            parent_id = int(parent_id)
            parent = SocialComment.query.get(parent_id)
            if not parent or parent.post_id != pid:
                parent_id = None
        except (ValueError, TypeError):
            parent_id = None

    c = SocialComment(
        post_id=pid,
        author_id=user.id,
        parent_id=parent_id,
        content=content,
    )
    db.session.add(c)
    p.comment_count = SocialPost.comment_count + 1

    _notify(p.author_id, user.id, "commented", post_id=pid)
    if parent_id:
        parent_comment = SocialComment.query.get(parent_id)
        if parent_comment:
            _notify(parent_comment.author_id, user.id, "replied", post_id=pid, comment_id=parent_id)

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "data": {
                "id": c.id,
                "comment_count": p.comment_count,
            },
        }
    ), 201


@social_feed.route("/feed/api/comments/<int:cid>/like", methods=["POST"])
@authed_only
def api_toggle_like_comment(cid):
    user = get_current_user()
    c = SocialComment.query.get_or_404(cid)
    if c.deleted:
        abort(404)

    existing = SocialLike.query.filter_by(user_id=user.id, comment_id=cid).first()
    if existing:
        db.session.delete(existing)
        c.like_count = max(c.like_count - 1, 0)
        db.session.commit()
        return jsonify(
            {"success": True, "data": {"liked": False, "like_count": c.like_count}}
        )
    else:
        lk = SocialLike(user_id=user.id, comment_id=cid)
        db.session.add(lk)
        c.like_count = SocialComment.like_count + 1
        _notify(c.author_id, user.id, "liked_comment", post_id=c.post_id, comment_id=cid)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"success": True, "data": {"liked": True, "like_count": c.like_count}})
        return jsonify(
            {"success": True, "data": {"liked": True, "like_count": c.like_count}}
        )


@social_feed.route("/feed/api/comments/<int:cid>", methods=["DELETE"])
@authed_only
def api_delete_comment(cid):
    user = get_current_user()
    c = SocialComment.query.get_or_404(cid)
    if c.author_id != user.id and not is_admin():
        abort(403)
    c.deleted = True
    p = SocialPost.query.get(c.post_id)
    if p:
        p.comment_count = max(p.comment_count - 1, 0)
    db.session.commit()
    return jsonify({"success": True})


# ─── Follow system ──────────────────────────────────────────────────


@social_feed.route("/feed/api/users/<int:uid>/follow", methods=["POST"])
@authed_only
def api_toggle_follow(uid):
    user = get_current_user()
    if user.id == uid:
        return jsonify({"success": False, "errors": ["Cannot follow yourself"]}), 400

    from CTFd.models import Users
    target = Users.query.get_or_404(uid)

    existing = SocialFollow.query.filter_by(
        follower_id=user.id, following_id=uid
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = SocialFollow.query.filter_by(following_id=uid).count()
        return jsonify(
            {"success": True, "data": {"following": False, "follower_count": count}}
        )
    else:
        f = SocialFollow(follower_id=user.id, following_id=uid)
        db.session.add(f)
        _notify(uid, user.id, "followed")
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            count = SocialFollow.query.filter_by(following_id=uid).count()
            return jsonify(
                {"success": True, "data": {"following": True, "follower_count": count}}
            )
        count = SocialFollow.query.filter_by(following_id=uid).count()
        return jsonify(
            {"success": True, "data": {"following": True, "follower_count": count}}
        )


@social_feed.route("/feed/api/users/<int:uid>/profile", methods=["GET"])
@authed_only
def api_user_profile(uid):
    from CTFd.models import Users

    u = Users.query.get_or_404(uid)

    post_count = SocialPost.query.filter_by(author_id=uid, deleted=False).count()
    follower_count = SocialFollow.query.filter_by(following_id=uid).count()
    following_count = SocialFollow.query.filter_by(follower_id=uid).count()

    is_following = False
    if authed():
        current_uid = get_current_user().id
        is_following = (
            SocialFollow.query.filter_by(
                follower_id=current_uid, following_id=uid
            ).first()
            is not None
        )

    try:
        score = u.get_score()
    except Exception:
        score = 0
    try:
        place = u.get_place()
    except Exception:
        place = None

    from CTFd.models.community import CommunityChallenge
    challenges_created = CommunityChallenge.query.filter_by(
        author_id=uid, state="published"
    ).count()

    return jsonify(
        {
            "success": True,
            "data": {
                "id": u.id,
                "name": u.name,
                "avatar": u.avatar,
                "affiliation": u.affiliation,
                "country": u.country,
                "website": u.website,
                "score": score,
                "place": place,
                "post_count": post_count,
                "follower_count": follower_count,
                "following_count": following_count,
                "challenges_created": challenges_created,
                "is_following": is_following,
                "joined": u.created.isoformat() if u.created else None,
            },
        }
    )


# ─── Notifications ──────────────────────────────────────────────────


@social_feed.route("/feed/api/notifications", methods=["GET"])
@authed_only
def api_notifications():
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 30, type=int), 50)

    q = SocialNotification.query.filter_by(user_id=user.id).order_by(
        desc(SocialNotification.created_at)
    )
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    unread_count = SocialNotification.query.filter_by(
        user_id=user.id, read=False
    ).count()

    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "id": n.id,
                    "actor": {
                        "id": n.actor.id,
                        "name": n.actor.name,
                        "avatar": n.actor.avatar,
                    }
                    if n.actor
                    else None,
                    "verb": n.verb,
                    "post_id": n.post_id,
                    "comment_id": n.comment_id,
                    "read": n.read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in pagination.items
            ],
            "meta": {"unread_count": unread_count},
        }
    )


@social_feed.route("/feed/api/notifications/read", methods=["POST"])
@authed_only
def api_mark_notifications_read():
    user = get_current_user()
    SocialNotification.query.filter_by(user_id=user.id, read=False).update(
        {"read": True}
    )
    db.session.commit()
    return jsonify({"success": True})


@social_feed.route("/feed/api/notifications/count", methods=["GET"])
@authed_only
def api_notification_count():
    user = get_current_user()
    count = SocialNotification.query.filter_by(
        user_id=user.id, read=False
    ).count()
    return jsonify({"success": True, "data": {"count": count}})


# ─── Reporting ──────────────────────────────────────────────────────


@social_feed.route("/feed/api/report", methods=["POST"])
@authed_only
def api_report():
    user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "errors": ["No data"]}), 400

    reason = (data.get("reason") or "").strip()
    if not reason or len(reason) > 200:
        return jsonify({"success": False, "errors": ["Reason required (max 200 chars)"]}), 400

    post_id = data.get("post_id")
    comment_id = data.get("comment_id")
    if not post_id and not comment_id:
        return jsonify({"success": False, "errors": ["Must specify post or comment"]}), 400

    r = SocialReport(
        reporter_id=user.id,
        post_id=post_id,
        comment_id=comment_id,
        reason=reason,
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"success": True}), 201

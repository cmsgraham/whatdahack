from flask import Blueprint, render_template, request, url_for

from CTFd.models import Awards, Challenges, Configs, Solves, Users, db
from CTFd.utils import config
from CTFd.utils.decorators import authed_only
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.helpers import get_errors, get_infos
from CTFd.utils.user import get_current_user

users = Blueprint("users", __name__)


def _score_subquery():
    """Return a subquery mapping user_id -> total_score (solves + awards)."""
    import datetime

    solve_scores = (
        db.session.query(
            Solves.user_id.label("uid"),
            db.func.sum(Challenges.value).label("score"),
        )
        .join(Challenges, Solves.challenge_id == Challenges.id)
        .filter(Challenges.value != 0)
        .group_by(Solves.user_id)
    )

    award_scores = (
        db.session.query(
            Awards.user_id.label("uid"),
            db.func.sum(Awards.value).label("score"),
        )
        .filter(Awards.value != 0)
        .group_by(Awards.user_id)
    )

    # Respect freeze if configured
    freeze = Configs.query.filter_by(key="freeze").first()
    if freeze and freeze.value:
        freeze_dt = datetime.datetime.utcfromtimestamp(int(freeze.value))
        solve_scores = solve_scores.filter(Solves.date < freeze_dt)
        award_scores = award_scores.filter(Awards.date < freeze_dt)

    union = db.union_all(solve_scores, award_scores).subquery()

    return (
        db.session.query(
            union.c.uid,
            db.func.sum(union.c.score).label("total"),
        )
        .group_by(union.c.uid)
        .subquery()
    )


@users.route("/users")
@check_account_visibility
def listing():
    q = request.args.get("q")
    field = request.args.get("field", "name")
    sort = request.args.get("sort", "score")  # "score" | "name"
    order = request.args.get("order", "desc")  # "asc" | "desc"

    if field not in ("name", "affiliation", "website"):
        field = "name"
    if sort not in ("score", "name"):
        sort = "score"
    if order not in ("asc", "desc"):
        order = "desc"

    filters = []
    if q:
        filters.append(getattr(Users, field).like("%{}%".format(q)))

    sq = _score_subquery()

    base_q = (
        Users.query.filter_by(banned=False, hidden=False)
        .filter(*filters)
        .outerjoin(sq, Users.id == sq.c.uid)
    )

    if sort == "score":
        score_col = db.func.coalesce(sq.c.total, 0)
        order_col = score_col.desc() if order == "desc" else score_col.asc()
    else:
        order_col = Users.name.asc() if order == "asc" else Users.name.desc()

    users = base_q.order_by(order_col).paginate(per_page=50, error_out=False)

    args = dict(request.args)
    args.pop("page", 1)

    return render_template(
        "users/users.html",
        users=users,
        prev_page=url_for(request.endpoint, page=users.prev_num, **args),
        next_page=url_for(request.endpoint, page=users.next_num, **args),
        q=q,
        field=field,
        sort=sort,
        order=order,
    )


@users.route("/profile")
@users.route("/user")
@authed_only
def private():
    infos = get_infos()
    errors = get_errors()

    user = get_current_user()

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    return render_template(
        "users/private.html",
        user=user,
        account=user.account,
        infos=infos,
        errors=errors,
    )


@users.route("/users/<int:user_id>")
@check_account_visibility
@check_score_visibility
def public(user_id):
    infos = get_infos()
    errors = get_errors()
    user = Users.query.filter_by(id=user_id, banned=False, hidden=False).first_or_404()

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    return render_template(
        "users/public.html", user=user, account=user.account, infos=infos, errors=errors
    )

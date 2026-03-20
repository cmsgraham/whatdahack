"""
CTFd/admin/competitions.py

Admin views for managing competitions:

    GET  /admin/competitions                → list all competitions
    GET  /admin/competitions/new            → new competition form
    POST /admin/competitions/new            → create competition
    GET  /admin/competitions/<id>           → view/edit competition + assign challenges
    POST /admin/competitions/<id>           → update competition settings
    POST /admin/competitions/<id>/activate  → set as active competition
    POST /admin/competitions/<id>/deactivate → clear active competition
    POST /admin/competitions/<id>/delete    → delete competition row
    POST /admin/competitions/<id>/challenges/add    → assign challenges
    POST /admin/competitions/<id>/challenges/remove → unassign challenges
"""

import datetime

from flask import flash, redirect, render_template, request, url_for

from CTFd.admin import admin
from CTFd.cache import clear_challenges, clear_standings
from CTFd.models import Challenges, Competition, db
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only


def _parse_dt(value):
    """Parse a naive datetime string from an HTML datetime-local input."""
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@admin.route("/admin/competitions")
@admins_only
def competitions_listing():
    competitions = Competition.query.order_by(Competition.id.asc()).all()
    active_slug = get_config("active_competition")
    return render_template(
        "admin/competitions/competitions.html",
        competitions=competitions,
        active_slug=active_slug,
    )


# ---------------------------------------------------------------------------
# New / Create
# ---------------------------------------------------------------------------


@admin.route("/admin/competitions/new", methods=["GET", "POST"])
@admins_only
def competitions_new():
    if request.method == "POST":
        slug = request.form.get("slug", "").strip()
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        state = request.form.get("state", "hidden")
        user_mode = request.form.get("user_mode", "teams")
        team_size = request.form.get("team_size", 0, type=int)
        start = _parse_dt(request.form.get("start"))
        end = _parse_dt(request.form.get("end"))
        freeze = _parse_dt(request.form.get("freeze"))

        errors = []
        if not slug:
            errors.append("Slug is required.")
        if not name:
            errors.append("Name is required.")
        if Competition.query.filter_by(slug=slug).first():
            errors.append(f"A competition with slug '{slug}' already exists.")

        if errors:
            return render_template(
                "admin/competitions/new.html",
                errors=errors,
                form=request.form,
            )

        comp = Competition(
            slug=slug,
            name=name,
            description=description,
            state=state,
            user_mode=user_mode,
            team_size=team_size,
            start=start,
            end=end,
            freeze=freeze,
        )
        db.session.add(comp)
        db.session.commit()

        flash(f"Competition '{name}' created.", "success")
        return redirect(url_for("admin.competitions_detail", competition_id=comp.id))

    return render_template("admin/competitions/new.html", errors=[], form={})


# ---------------------------------------------------------------------------
# Detail / Edit
# ---------------------------------------------------------------------------


@admin.route("/admin/competitions/<int:competition_id>", methods=["GET", "POST"])
@admins_only
def competitions_detail(competition_id):
    comp = Competition.query.filter_by(id=competition_id).first_or_404()

    if request.method == "POST":
        comp.name = request.form.get("name", comp.name).strip()
        comp.description = request.form.get("description", "").strip()
        comp.state = request.form.get("state", comp.state)
        comp.lifecycle = request.form.get("lifecycle", comp.lifecycle or "draft")
        comp.user_mode = request.form.get("user_mode", comp.user_mode)
        comp.team_size = request.form.get("team_size", comp.team_size, type=int)
        comp.start = _parse_dt(request.form.get("start"))
        comp.end = _parse_dt(request.form.get("end"))
        comp.freeze = _parse_dt(request.form.get("freeze"))
        db.session.commit()
        clear_standings()
        flash("Competition updated.", "success")
        return redirect(url_for("admin.competitions_detail", competition_id=comp.id))

    # Challenges assigned to this competition
    assigned = comp.challenges.order_by(Challenges.id.asc()).all()
    assigned_ids = {c.id for c in assigned}

    # Challenges not yet assigned to any competition (available to assign)
    unassigned = (
        Challenges.query.filter(Challenges.competition_id.is_(None))
        .order_by(Challenges.id.asc())
        .all()
    )

    active_slug = get_config("active_competition")

    return render_template(
        "admin/competitions/competition.html",
        comp=comp,
        assigned=assigned,
        assigned_ids=assigned_ids,
        unassigned=unassigned,
        active_slug=active_slug,
    )


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


@admin.route("/admin/competitions/<int:competition_id>/end", methods=["POST"])
@admins_only
def competitions_end(competition_id):
    """Transition competition to 'ended' — preserves all data."""
    from CTFd.utils.competitions import end_competition

    comp = Competition.query.filter_by(id=competition_id).first_or_404()
    end_competition(comp)
    flash(f"'{comp.name}' has been ended. Historical data preserved.", "success")
    return redirect(url_for("admin.competitions_detail", competition_id=comp.id))


@admin.route("/admin/competitions/<int:competition_id>/archive", methods=["POST"])
@admins_only
def competitions_archive(competition_id):
    """Archive a competition — hides it from all public views."""
    from CTFd.utils.competitions import archive_competition

    comp = Competition.query.filter_by(id=competition_id).first_or_404()
    archive_competition(comp)
    flash(
        f"'{comp.name}' has been archived and hidden from public listings.",
        "success",
    )
    return redirect(url_for("admin.competitions_detail", competition_id=comp.id))


@admin.route("/admin/competitions/<int:competition_id>/unarchive", methods=["POST"])
@admins_only
def competitions_unarchive(competition_id):
    """Restore an archived competition to 'ended' state."""
    from CTFd.utils.competitions import unarchive_competition

    comp = Competition.query.filter_by(id=competition_id).first_or_404()
    unarchive_competition(comp)
    flash(f"'{comp.name}' restored to ended state.", "success")
    return redirect(url_for("admin.competitions_detail", competition_id=comp.id))


@admin.route("/admin/competitions/<int:competition_id>/clone", methods=["POST"])
@admins_only
def competitions_clone(competition_id):
    """Clone a competition's metadata into a new competition shell."""
    from CTFd.utils.competitions import clone_competition

    source = Competition.query.filter_by(id=competition_id).first_or_404()

    new_slug = request.form.get("new_slug", "").strip()
    new_name = request.form.get("new_name", "").strip()

    errors = []
    if not new_slug:
        errors.append("New slug is required.")
    if not new_name:
        errors.append("New name is required.")
    if new_slug and Competition.query.filter_by(slug=new_slug).first():
        errors.append(f"A competition with slug '{new_slug}' already exists.")

    if errors:
        for err in errors:
            flash(err, "danger")
        return redirect(
            url_for("admin.competitions_detail", competition_id=competition_id)
        )

    cloned = clone_competition(source, new_slug, new_name)
    flash(
        f"Cloned '{source.name}' \u2192 '{cloned.name}'. Assign challenges to the new competition.",
        "success",
    )
    return redirect(
        url_for("admin.competitions_detail", competition_id=cloned.id)
    )


# ---------------------------------------------------------------------------
# Activate / Deactivate
# ---------------------------------------------------------------------------


@admin.route("/admin/competitions/<int:competition_id>/activate", methods=["POST"])
@admins_only
def competitions_activate(competition_id):
    comp = Competition.query.filter_by(id=competition_id).first_or_404()
    set_config("active_competition", comp.slug)
    clear_standings()
    clear_challenges()
    flash(f"'{comp.name}' is now the active competition.", "success")
    return redirect(url_for("admin.competitions_detail", competition_id=comp.id))


@admin.route(
    "/admin/competitions/<int:competition_id>/deactivate", methods=["POST"]
)
@admins_only
def competitions_deactivate(competition_id):
    comp = Competition.query.filter_by(id=competition_id).first_or_404()
    set_config("active_competition", None)
    clear_standings()
    clear_challenges()
    flash("Active competition cleared — platform is now in legacy (global) mode.", "success")
    return redirect(url_for("admin.competitions_detail", competition_id=comp.id))


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@admin.route("/admin/competitions/<int:competition_id>/delete", methods=["POST"])
@admins_only
def competitions_delete(competition_id):
    comp = Competition.query.filter_by(id=competition_id).first_or_404()

    # Unassign challenges so foreign keys don't cascade-delete them
    Challenges.query.filter_by(competition_id=comp.id).update(
        {"competition_id": None}, synchronize_session=False
    )
    db.session.delete(comp)
    db.session.commit()

    # If this was the active competition, clear the config
    if get_config("active_competition") == comp.slug:
        set_config("active_competition", None)

    clear_standings()
    clear_challenges()
    flash(f"Competition '{comp.name}' deleted.", "success")
    return redirect(url_for("admin.competitions_listing"))


# ---------------------------------------------------------------------------
# Challenge assignment
# ---------------------------------------------------------------------------


@admin.route(
    "/admin/competitions/<int:competition_id>/challenges/add", methods=["POST"]
)
@admins_only
def competitions_challenges_add(competition_id):
    comp = Competition.query.filter_by(id=competition_id).first_or_404()
    challenge_ids = request.form.getlist("challenge_ids", type=int)

    if challenge_ids:
        Challenges.query.filter(Challenges.id.in_(challenge_ids)).update(
            {"competition_id": comp.id}, synchronize_session=False
        )
        db.session.commit()
        clear_challenges()
        flash(f"{len(challenge_ids)} challenge(s) assigned to '{comp.name}'.", "success")

    return redirect(url_for("admin.competitions_detail", competition_id=comp.id))


@admin.route(
    "/admin/competitions/<int:competition_id>/challenges/remove", methods=["POST"]
)
@admins_only
def competitions_challenges_remove(competition_id):
    comp = Competition.query.filter_by(id=competition_id).first_or_404()
    challenge_ids = request.form.getlist("challenge_ids", type=int)

    if challenge_ids:
        # Verify these challenges belong to this competition before unlinking
        Challenges.query.filter(
            Challenges.id.in_(challenge_ids),
            Challenges.competition_id == comp.id,
        ).update({"competition_id": None}, synchronize_session=False)
        db.session.commit()
        clear_challenges()
        flash(f"{len(challenge_ids)} challenge(s) removed from '{comp.name}'.", "success")

    return redirect(url_for("admin.competitions_detail", competition_id=comp.id))


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@admin.route("/admin/competitions/<int:competition_id>/members")
@admins_only
def competitions_members(competition_id):
    """List all users registered for a competition, their status, and their team."""
    from CTFd.models import CompetitionTeamMember, CompetitionUser, Users

    comp = Competition.query.filter_by(id=competition_id).first_or_404()

    registrations = (
        CompetitionUser.query.filter_by(competition_id=competition_id)
        .order_by(CompetitionUser.joined_at.asc())
        .all()
    )

    memberships = {
        m.user_id: m
        for m in CompetitionTeamMember.query.filter_by(
            competition_id=competition_id
        ).all()
    }

    rows = []
    for reg in registrations:
        user = Users.query.get(reg.user_id)
        membership = memberships.get(reg.user_id)
        team = membership.team if membership else None
        rows.append(
            {
                "user": user,
                "status": reg.status,
                "joined_at": reg.joined_at,
                "team": team,
            }
        )

    return render_template(
        "admin/competitions/members.html",
        comp=comp,
        rows=rows,
    )

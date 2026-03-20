"""
CTFd/competitions.py

Flask Blueprint providing competition-scoped routes:

    GET /competitions                      → list all visible competitions
    GET /competitions/<slug>               → redirect to challenges
    GET /competitions/<slug>/challenges    → challenges scoped to competition
    GET /competitions/<slug>/scoreboard    → scoreboard scoped to competition

When a competition route is served, flask.g.competition_id is populated so that
all downstream utilities (get_current_competition_id, ctftime_or_competition,
challenges API, etc.) transparently scope to that competition without requiring
callers to pass explicit parameters.
"""

from flask import Blueprint, g, redirect, render_template, request, url_for
from flask_babel import lazy_gettext as _l
from sqlalchemy import func as sa_func

from CTFd.constants.config import ChallengeVisibilityTypes, Configs
from CTFd.utils import config
from CTFd.utils.competitions import (
    ctf_ended_for,
    ctftime_for,
    get_active_competition,
    get_competition_by_slug,
    get_competition_team,
    get_registration_status,
    register_user,
    create_competition_team,
    join_competition_team,
    can_register,
)
from CTFd.utils.config import is_teams_mode
from CTFd.utils.config.visibility import scores_visible
from CTFd.utils.decorators import (
    require_complete_profile,
    require_competition_registered,
    require_verified_emails,
)
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_challenge_visibility,
    check_score_visibility,
)
from CTFd.utils.helpers import get_errors, get_infos
from CTFd.utils.scores import get_standings
from CTFd.utils.user import authed, get_current_team, get_current_user, is_admin

competitions = Blueprint("competitions", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inject_competition(slug):
    """
    Resolve the competition by slug, store it on flask.g, and return it.

    Sets:
        g.competition      — Competition ORM instance
        g.competition_id   — competition.id (int)
    """
    competition = get_competition_by_slug(slug)  # aborts 404 on miss
    g.competition = competition
    g.competition_id = competition.id
    return competition


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@competitions.route("/competitions")
def listing():
    """List all publicly visible, non-archived competitions."""
    from CTFd.models import Competition

    query = Competition.query
    if not is_admin():
        # Public sees only visible + not archived
        query = query.filter_by(state="visible").filter(
            Competition.lifecycle.notin_(["archived"])
        )
    else:
        # Admins see everything except archived (archived lives in history)
        query = query.filter(
            Competition.lifecycle.notin_(["archived"])
        )
    all_competitions = query.order_by(Competition.id.asc()).all()
    active = get_active_competition()
    return render_template(
        "competitions/listing.html",
        competitions=all_competitions,
        active_competition=active,
    )


@competitions.route("/competitions/<slug>")
def show(slug):
    """Render the competition landing page."""
    competition = _inject_competition(slug)
    active = get_active_competition()

    reg_status = "not_joined"
    if authed() and not is_admin():
        user = get_current_user()
        reg_status = get_registration_status(user.id, competition.id)

    return render_template(
        "competitions/landing.html",
        competition=competition,
        active_competition=active,
        reg_status=reg_status,
        can_register=can_register(competition),
    )


@competitions.route("/competitions/history")
def history():
    """List all ended and archived competitions (historical record)."""
    from CTFd.models import Competition

    query = Competition.query.filter(
        Competition.lifecycle.in_(["ended", "archived"])
    )
    if not is_admin():
        query = query.filter_by(state="visible")
    past = query.order_by(
        sa_func.isnull(Competition.end).asc(),  # NULLs last (MariaDB/MySQL compatible)
        Competition.end.desc(),
        Competition.id.desc(),
    ).all()
    return render_template("competitions/history.html", competitions=past)


@competitions.route("/competitions/<slug>/challenges")
@require_complete_profile
@require_verified_emails
@check_challenge_visibility
@require_competition_registered
def challenges(slug):
    """Render the challenges page scoped to the given competition."""
    competition = _inject_competition(slug)

    infos = get_infos()
    errors = get_errors()

    if Configs.challenge_visibility == ChallengeVisibilityTypes.ADMINS:
        infos.append(_l("Challenge Visibility is set to Admins Only"))

    # Check competition timing
    if not ctftime_for(competition):
        if competition.start and competition.start.timestamp() > __import__("time").time():
            errors.append(
                _l(
                    "%(name)s has not started yet",
                    name=competition.name,
                )
            )
        elif ctf_ended_for(competition):
            infos.append(_l("%(name)s has ended", name=competition.name))

    # Teams mode: require team membership before allowing challenge access
    if (
        Configs.challenge_visibility != ChallengeVisibilityTypes.PUBLIC
        or authed()
    ):
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    return render_template(
        "competitions/challenges.html",
        competition=competition,
        infos=infos,
        errors=errors,
    )


@competitions.route("/competitions/<slug>/scoreboard")
@check_account_visibility
@check_score_visibility
def scoreboard(slug):
    """Render the scoreboard scoped to the given competition."""
    competition = _inject_competition(slug)

    infos = get_infos()

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    if is_admin() is True and scores_visible() is False:
        infos.append("Scores are not currently visible to users")

    standings = get_standings(competition_id=competition.id)
    return render_template(
        "competitions/scoreboard.html",
        competition=competition,
        standings=standings,
        infos=infos,
    )


# ---------------------------------------------------------------------------
# Explicit registration routes
# ---------------------------------------------------------------------------


@competitions.route("/competitions/<slug>/join", methods=["POST"])
@require_complete_profile
@require_verified_emails
def join(slug):
    """
    POST /competitions/<slug>/join

    Registers the current user for the competition.  Requires authentication.
    - users-mode competition → status set to 'joined' immediately, redirect to challenges.
    - teams-mode competition → status set to 'pending_team', redirect to team-select page.
    """
    if not authed():
        return redirect(url_for("auth.login", next=request.full_path))

    competition = _inject_competition(slug)
    user = get_current_user()

    reg, err = register_user(user.id, competition.id)
    if err:
        return render_template(
            "competitions/landing.html",
            competition=competition,
            active_competition=get_active_competition(),
            errors=[err],
            reg_status="not_joined",
        )

    if reg.status == "pending_team":
        return redirect(url_for("competitions.team_select", slug=slug))

    return redirect(url_for("competitions.challenges", slug=slug))


@competitions.route("/competitions/<slug>/team", methods=["GET"])
@require_complete_profile
@require_verified_emails
def team_select(slug):
    """
    GET /competitions/<slug>/team

    Team-selection landing for teams-mode competitions.
    Shows the user a form to create a new team or join an existing one.
    Only reachable after joining a competition.
    """
    if not authed():
        return redirect(url_for("auth.login", next=request.full_path))

    competition = _inject_competition(slug)
    user = get_current_user()

    status = get_registration_status(user.id, competition.id)
    if status == "not_joined":
        return redirect(url_for("competitions.show", slug=slug))

    membership = get_competition_team(user.id, competition.id)
    if membership is not None and status == "joined":
        # User already has a team — send them to challenges
        return redirect(url_for("competitions.challenges", slug=slug))

    # List teams currently enrolled in this competition for the join-team picker
    from CTFd.models import CompetitionTeam, CompetitionTeamMember, Teams
    enrolled_teams = (
        Teams.query.join(CompetitionTeam, Teams.id == CompetitionTeam.team_id)
        .filter(CompetitionTeam.competition_id == competition.id)
        .order_by(Teams.name.asc())
        .all()
    )
    # Attach member count to each team for display
    team_member_counts = {
        t.id: CompetitionTeamMember.query.filter_by(
            competition_id=competition.id, team_id=t.id
        ).count()
        for t in enrolled_teams
    }

    return render_template(
        "competitions/team_select.html",
        competition=competition,
        enrolled_teams=enrolled_teams,
        team_member_counts=team_member_counts,
        team_size=competition.team_size,
        errors=get_errors(),
        infos=get_infos(),
    )


@competitions.route("/competitions/<slug>/team/create", methods=["POST"])
@require_complete_profile
@require_verified_emails
def team_create(slug):
    """
    POST /competitions/<slug>/team/create

    Creates a new team in this competition and assigns the current user to it.
    """
    if not authed():
        return redirect(url_for("auth.login", next=request.full_path))

    competition = _inject_competition(slug)
    user = get_current_user()

    team_name = request.form.get("name", "").strip()
    team_password = request.form.get("password", "").strip() or None

    team, err = create_competition_team(
        user.id, competition.id, team_name, team_password
    )
    if err:
        return redirect(
            url_for("competitions.team_select", slug=slug, error=err)
        )

    return redirect(url_for("competitions.challenges", slug=slug))


@competitions.route("/competitions/<slug>/team/join", methods=["POST"])
@require_complete_profile
@require_verified_emails
def team_join(slug):
    """
    POST /competitions/<slug>/team/join

    Joins an existing team in this competition.
    """
    if not authed():
        return redirect(url_for("auth.login", next=request.full_path))

    competition = _inject_competition(slug)
    user = get_current_user()

    team_id = request.form.get("team_id", type=int)
    team_password = request.form.get("password", "").strip() or None

    if not team_id:
        return redirect(
            url_for("competitions.team_select", slug=slug, error="No team selected")
        )

    membership, err = join_competition_team(
        user.id, competition.id, team_id, team_password
    )
    if err:
        return redirect(
            url_for("competitions.team_select", slug=slug, error=err)
        )

    return redirect(url_for("competitions.challenges", slug=slug))

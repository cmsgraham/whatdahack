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

from CTFd.constants.config import ChallengeVisibilityTypes, Configs
from CTFd.utils import config
from CTFd.utils.competitions import (
    ctf_ended_for,
    ctftime_for,
    get_active_competition,
    get_competition_by_slug,
)
from CTFd.utils.config import is_teams_mode
from CTFd.utils.config.visibility import scores_visible
from CTFd.utils.decorators import require_complete_profile, require_verified_emails
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_challenge_visibility,
    check_score_visibility,
)
from CTFd.utils.helpers import get_errors, get_infos
from CTFd.utils.scores import get_standings
from CTFd.utils.user import authed, get_current_team, is_admin

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
    """List all publicly visible competitions."""
    from CTFd.models import Competition

    query = Competition.query
    if not is_admin():
        query = query.filter_by(state="visible")
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
    return render_template(
        "competitions/landing.html",
        competition=competition,
        active_competition=active,
    )


@competitions.route("/competitions/<slug>/challenges")
@require_complete_profile
@require_verified_emails
@check_challenge_visibility
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

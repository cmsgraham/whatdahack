from flask import Blueprint, redirect, render_template, url_for

from CTFd.utils import config
from CTFd.utils.competitions import get_active_competition, get_current_competition_id
from CTFd.utils.config.visibility import scores_visible
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.helpers import get_infos
from CTFd.utils.scores import get_standings
from CTFd.utils.user import is_admin

scoreboard = Blueprint("scoreboard", __name__)


@scoreboard.route("/scoreboard")
@check_account_visibility
@check_score_visibility
def listing():
    # If an active competition is configured, redirect to its scoreboard page
    active = get_active_competition()
    if active is not None:
        return redirect(url_for("competitions.scoreboard", slug=active.slug))

    infos = get_infos()

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    if is_admin() is True and scores_visible() is False:
        infos.append("Scores are not currently visible to users")

    competition_id = get_current_competition_id()
    standings = get_standings(competition_id=competition_id)
    return render_template("scoreboard.html", standings=standings, infos=infos)

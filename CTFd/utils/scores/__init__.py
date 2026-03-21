from sqlalchemy.sql.expression import union_all

from CTFd.cache import cache
from CTFd.models import Awards, Brackets, Challenges, CompetitionSolves, Solves, Submissions, Teams, Users, db
from CTFd.utils import get_config
from CTFd.utils.dates import unix_time_to_utc
from CTFd.utils.modes import TEAMS_MODE, get_model


@cache.memoize(timeout=60)
def get_standings(count=None, bracket_id=None, admin=False, fields=None, competition_id=None):
    """
    Platform leaderboard — queries the Solves table filtered to scope='platform'.

    Pass competition_id=N to get competition standings via get_competition_standings()
    instead; passing it here is kept for backward compatibility but redirects
    internally to the competition-scoped helper.
    """
    if competition_id is not None:
        return get_competition_standings(
            count=count, bracket_id=bracket_id, admin=admin, fields=fields,
            competition_id=competition_id,
        )

    if fields is None:
        fields = []
    Model = get_model()

    scores = (
        db.session.query(
            Solves.account_id.label("account_id"),
            db.func.sum(Challenges.value).label("score"),
            db.func.max(Solves.id).label("id"),
            db.func.max(Solves.date).label("date"),
        )
        .join(Challenges)
        .filter(Challenges.value != 0)
        # Platform leaderboard: only count platform-scoped challenge solves.
        .filter(Challenges.scope == "platform")
        .group_by(Solves.account_id)
    )

    awards = (
        db.session.query(
            Awards.account_id.label("account_id"),
            db.func.sum(Awards.value).label("score"),
            db.func.max(Awards.id).label("id"),
            db.func.max(Awards.date).label("date"),
        )
        .filter(Awards.value != 0)
        .group_by(Awards.account_id)
    )

    freeze = get_config("freeze")
    if not admin and freeze:
        scores = scores.filter(Solves.date < unix_time_to_utc(freeze))
        awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

    results = union_all(scores, awards).alias("results")

    sumscores = (
        db.session.query(
            results.columns.account_id,
            db.func.sum(results.columns.score).label("score"),
            db.func.max(results.columns.id).label("id"),
            db.func.max(results.columns.date).label("date"),
        )
        .group_by(results.columns.account_id)
        .subquery()
    )

    if admin:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                Model.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                Model.hidden,
                Model.banned,
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .join(Brackets, isouter=True)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )
    else:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                Model.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .join(Brackets, isouter=True)
            .filter(Model.banned == False, Model.hidden == False)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )

    if bracket_id is not None:
        standings_query = standings_query.filter(Model.bracket_id == bracket_id)

    if count is None:
        standings = standings_query.all()
    else:
        standings = standings_query.limit(count).all()

    return standings


@cache.memoize(timeout=60)
def get_competition_standings(count=None, bracket_id=None, admin=False, fields=None, competition_id=None):
    """
    Competition leaderboard — queries competition_solves for a specific competition.

    Completely isolated from Solves / the platform leaderboard.
    competition_id is required; returns [] if None.
    """
    if competition_id is None:
        return []

    if fields is None:
        fields = []
    Model = get_model()
    mode = get_config("user_mode")

    account_col = (
        CompetitionSolves.team_id if mode == TEAMS_MODE else CompetitionSolves.user_id
    )

    scores = (
        db.session.query(
            account_col.label("account_id"),
            db.func.sum(Challenges.value).label("score"),
            db.func.max(CompetitionSolves.id).label("id"),
            db.func.max(CompetitionSolves.date).label("date"),
        )
        .join(Challenges, Challenges.id == CompetitionSolves.challenge_id)
        .filter(CompetitionSolves.competition_id == competition_id)
        .filter(Challenges.value != 0)
        .group_by(account_col)
    )

    awards = (
        db.session.query(
            Awards.account_id.label("account_id"),
            db.func.sum(Awards.value).label("score"),
            db.func.max(Awards.id).label("id"),
            db.func.max(Awards.date).label("date"),
        )
        .filter(Awards.value != 0)
        .filter(Awards.competition_id == competition_id)
        .group_by(Awards.account_id)
    )

    results = union_all(scores, awards).alias("results")

    sumscores = (
        db.session.query(
            results.columns.account_id,
            db.func.sum(results.columns.score).label("score"),
            db.func.max(results.columns.id).label("id"),
            db.func.max(results.columns.date).label("date"),
        )
        .group_by(results.columns.account_id)
        .subquery()
    )

    if admin:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                Model.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                Model.hidden,
                Model.banned,
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .join(Brackets, isouter=True)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )
    else:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                Model.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .join(Brackets, isouter=True)
            .filter(Model.banned == False, Model.hidden == False)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )

    if bracket_id is not None:
        standings_query = standings_query.filter(Model.bracket_id == bracket_id)

    if count is None:
        standings = standings_query.all()
    else:
        standings = standings_query.limit(count).all()

    return standings


@cache.memoize(timeout=60)
def get_team_standings(count=None, bracket_id=None, admin=False, fields=None, competition_id=None):
    if fields is None:
        fields = []
    scores = (
        db.session.query(
            Solves.team_id.label("team_id"),
            db.func.sum(Challenges.value).label("score"),
            db.func.max(Solves.id).label("id"),
            db.func.max(Solves.date).label("date"),
        )
        .join(Challenges)
        .filter(Challenges.value != 0)
        .group_by(Solves.team_id)
    )

    awards = (
        db.session.query(
            Awards.team_id.label("team_id"),
            db.func.sum(Awards.value).label("score"),
            db.func.max(Awards.id).label("id"),
            db.func.max(Awards.date).label("date"),
        )
        .filter(Awards.value != 0)
        .group_by(Awards.team_id)
    )

    # Platform-only: exclude competition-scoped solves
    scores = scores.filter(Challenges.scope == "platform")

    freeze = get_config("freeze")
    if not admin and freeze:
        scores = scores.filter(Solves.date < unix_time_to_utc(freeze))
        awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

    results = union_all(scores, awards).alias("results")

    sumscores = (
        db.session.query(
            results.columns.team_id,
            db.func.sum(results.columns.score).label("score"),
            db.func.max(results.columns.id).label("id"),
            db.func.max(results.columns.date).label("date"),
        )
        .group_by(results.columns.team_id)
        .subquery()
    )

    if admin:
        standings_query = (
            db.session.query(
                Teams.id.label("team_id"),
                Teams.oauth_id.label("oauth_id"),
                Teams.name.label("name"),
                Teams.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                Teams.hidden,
                Teams.banned,
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Teams.id == sumscores.columns.team_id)
            .join(Brackets, isouter=True)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )
    else:
        standings_query = (
            db.session.query(
                Teams.id.label("team_id"),
                Teams.oauth_id.label("oauth_id"),
                Teams.name.label("name"),
                Teams.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Teams.id == sumscores.columns.team_id)
            .join(Brackets, isouter=True)
            .filter(Teams.banned == False)
            .filter(Teams.hidden == False)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )

    if bracket_id is not None:
        standings_query = standings_query.filter(Teams.bracket_id == bracket_id)

    if count is None:
        standings = standings_query.all()
    else:
        standings = standings_query.limit(count).all()

    return standings


@cache.memoize(timeout=60)
def get_user_standings(count=None, bracket_id=None, admin=False, fields=None, competition_id=None):
    if fields is None:
        fields = []
    scores = (
        db.session.query(
            Solves.user_id.label("user_id"),
            db.func.sum(Challenges.value).label("score"),
            db.func.max(Solves.id).label("id"),
            db.func.max(Solves.date).label("date"),
        )
        .join(Challenges)
        .filter(Challenges.value != 0)
        .group_by(Solves.user_id)
    )

    awards = (
        db.session.query(
            Awards.user_id.label("user_id"),
            db.func.sum(Awards.value).label("score"),
            db.func.max(Awards.id).label("id"),
            db.func.max(Awards.date).label("date"),
        )
        .filter(Awards.value != 0)
        .group_by(Awards.user_id)
    )

    # Platform-only: exclude competition-scoped solves
    scores = scores.filter(Challenges.scope == "platform")

    freeze = get_config("freeze")
    if not admin and freeze:
        scores = scores.filter(Solves.date < unix_time_to_utc(freeze))
        awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

    results = union_all(scores, awards).alias("results")

    sumscores = (
        db.session.query(
            results.columns.user_id,
            db.func.sum(results.columns.score).label("score"),
            db.func.max(results.columns.id).label("id"),
            db.func.max(results.columns.date).label("date"),
        )
        .group_by(results.columns.user_id)
        .subquery()
    )

    if admin:
        standings_query = (
            db.session.query(
                Users.id.label("user_id"),
                Users.oauth_id.label("oauth_id"),
                Users.name.label("name"),
                Users.team_id.label("team_id"),
                Users.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                Users.hidden,
                Users.banned,
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Users.id == sumscores.columns.user_id)
            .join(Brackets, isouter=True)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )
    else:
        standings_query = (
            db.session.query(
                Users.id.label("user_id"),
                Users.oauth_id.label("oauth_id"),
                Users.name.label("name"),
                Users.team_id.label("team_id"),
                Users.bracket_id.label("bracket_id"),
                Brackets.name.label("bracket_name"),
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Users.id == sumscores.columns.user_id)
            .join(Brackets, isouter=True)
            .filter(Users.banned == False, Users.hidden == False)
            .order_by(
                sumscores.columns.score.desc(),
                sumscores.columns.date.asc(),
                sumscores.columns.id.asc(),
            )
        )

    if bracket_id is not None:
        standings_query = standings_query.filter(Users.bracket_id == bracket_id)

    if count is None:
        standings = standings_query.all()
    else:
        standings = standings_query.limit(count).all()

    return standings

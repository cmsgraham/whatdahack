"""
CTFd/utils/competitions/__init__.py

Utility functions for multi-competition support.

All functions are safe to import at module level — heavy imports are deferred
inside the functions to avoid circular dependency issues with the app factory.
"""
import datetime


def get_active_competition():
    """
    Return the Competition instance configured as the active competition,
    or None if no active competition is set.

    The active competition is identified by the 'active_competition' config key,
    which should hold the competition's slug (e.g. 'wdh-2026').

    Set it via:
        flask set_config active_competition wdh-2026
    """
    from CTFd.models import Competition
    from CTFd.utils import get_config

    slug = get_config("active_competition")
    if not slug:
        return None
    return Competition.query.filter_by(slug=slug).first()


def get_current_competition_id():
    """
    Return the id of the currently active competition, or None.

    Resolution order (first non-None wins):
    1. flask.g.competition_id  — set by competition blueprint view handlers
    2. request.args['competition_id'] — explicit query-param from API callers
    3. 'active_competition' config key — global fallback for legacy routes

    This is the canonical way for request-level code to resolve the
    competition_id without importing Competition or worrying about
    whether a competition is configured.

    Usage:
        competition_id = get_current_competition_id()
        chal_q = get_all_challenges(competition_id=competition_id, ...)
    """
    # 1. Request-context injection from the competitions blueprint
    try:
        from flask import g

        if getattr(g, "competition_id", None) is not None:
            return g.competition_id
    except RuntimeError:
        # No active application/request context (e.g. CLI commands)
        pass

    # 2. Explicit query-param (API callers include ?competition_id=N)
    try:
        from flask import request

        raw = request.args.get("competition_id")
        if raw is not None:
            try:
                return int(raw)
            except (ValueError, TypeError):
                pass
    except RuntimeError:
        pass

    # 3. Config-based active competition (legacy / default behaviour)
    comp = get_active_competition()
    return comp.id if comp else None


def get_competition_by_slug(slug):
    """
    Return the Competition instance for the given slug, or 404.

    Usage:
        comp = get_competition_by_slug("wdh-2026")
    """
    from flask import abort

    from CTFd.models import Competition

    comp = Competition.query.filter_by(slug=slug).first()
    if comp is None:
        abort(404)
    return comp


def ctftime_for(competition):
    """
    Return True if the given competition is currently active (within its time window).

    Mirrors the behaviour of CTFd.utils.dates.ctftime() but scoped to a
    specific Competition object rather than reading from global config.

    Truth table:
        start set,  end set   → True iff start <= now <= end
        start set,  no end    → True iff now >= start
        no start,   end set   → True iff now <= end
        no start,   no end    → True (always open)
    """
    now = datetime.datetime.utcnow()

    if competition.start and competition.end:
        return competition.start <= now <= competition.end
    if competition.start and not competition.end:
        return now >= competition.start
    if competition.end and not competition.start:
        return now <= competition.end
    return True


def ctftime_or_competition():
    """
    Competition-aware replacement for CTFd.utils.dates.ctftime().

    - When a competition is in g.competition_id (set by the competitions
      blueprint): evaluates timing against that Competition row.
    - When an active competition is configured globally: uses that.
    - Otherwise falls back to the global ctftime() (legacy behaviour).
    """
    from CTFd.utils.dates import ctftime as global_ctftime

    competition_id = get_current_competition_id()
    if competition_id is not None:
        from CTFd.models import Competition

        comp = Competition.query.get(competition_id)
        if comp is not None:
            return ctftime_for(comp)
    return global_ctftime()


def ctf_ended_for(competition):
    """
    Return True if the given competition's end time has passed.
    Returns False if no end time is set (competition runs indefinitely).
    """
    if competition.end is None:
        return False
    return datetime.datetime.utcnow() > competition.end


# ---------------------------------------------------------------------------
# Lifecycle management
# ---------------------------------------------------------------------------


def end_competition(comp):
    """
    Transition a competition to the 'ended' lifecycle state.

    - Sets lifecycle → 'ended'
    - Deactivates it as the global active competition if it was set
    - Preserves all challenge and submission data (non-destructive)
    """
    from CTFd.cache import clear_challenges, clear_standings
    from CTFd.models import db
    from CTFd.utils import get_config, set_config

    comp.lifecycle = "ended"
    db.session.commit()
    if get_config("active_competition") == comp.slug:
        set_config("active_competition", None)
        clear_standings()
        clear_challenges()


def archive_competition(comp):
    """
    Transition a competition to the 'archived' lifecycle state.

    - Sets lifecycle → 'archived'
    - Sets state → 'hidden' (removes from all public listings)
    - Deactivates global active competition if needed
    - All historical data is preserved
    """
    from CTFd.cache import clear_challenges, clear_standings
    from CTFd.models import db
    from CTFd.utils import get_config, set_config

    comp.lifecycle = "archived"
    comp.state = "hidden"
    db.session.commit()
    if get_config("active_competition") == comp.slug:
        set_config("active_competition", None)
        clear_standings()
        clear_challenges()


def unarchive_competition(comp):
    """
    Restore an archived competition to 'ended' state.

    Does NOT change visibility (state) — admin controls that separately.
    """
    from CTFd.models import db

    comp.lifecycle = "ended"
    db.session.commit()


def clone_competition(source, new_slug, new_name):
    """
    Clone a competition's metadata into a new competition shell.

    Creates a new Competition row with the same structural settings as the
    source (user_mode, team_size, description) but:
      - New slug and name
      - lifecycle = 'draft'  (fresh, not yet started)
      - state = 'hidden'     (hidden until admin makes it visible)
      - No start/end times   (admin sets dates for the new run)
      - No challenges        (admin assigns them after cloning)
      - No solve data        (clean slate)

    This is safe and non-destructive — the source competition is untouched.

    Returns the new Competition instance.
    """
    from CTFd.models import Competition, db

    clone = Competition(
        slug=new_slug,
        name=new_name,
        description=source.description,
        state="hidden",
        lifecycle="draft",
        user_mode=source.user_mode,
        team_size=source.team_size,
        start=None,
        end=None,
        freeze=None,
    )
    db.session.add(clone)
    db.session.commit()
    return clone


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


# ---------------------------------------------------------------------------
# Explicit competition registration helpers
# ---------------------------------------------------------------------------


def can_register(competition, admin_override=False):
    """
    Return True if registration is currently open for this competition.

    Policy:
      draft     → blocked  (competition is not yet published)
      scheduled → open     (pre-registration before start date is allowed)
      active    → open
      ended     → closed   (pass admin_override=True to bypass)
      archived  → always closed

    Rationale: allowing pre-registration (scheduled state) lets competitors
    prepare teams and plan participation before the start gun.  Closing
    registration after end prevents late sign-ups that would corrupt history.
    """
    if admin_override:
        return True
    lc = competition.lifecycle or "draft"
    return lc in ("scheduled", "active")


def get_registration(user_id, competition_id):
    """Return the CompetitionUser row for (user_id, competition_id), or None."""
    from CTFd.models import CompetitionUser

    return CompetitionUser.query.filter_by(
        competition_id=competition_id, user_id=user_id
    ).first()


def get_registration_status(user_id, competition_id):
    """
    Return the canonical registration state for a user in a competition:

      'not_joined'   — no CompetitionUser row exists
      'pending_team' — CompetitionUser row exists but team not yet chosen
                       (only possible in teams-mode competitions)
      'joined'       — fully registered and may participate
    """
    reg = get_registration(user_id, competition_id)
    if reg is None:
        return "not_joined"
    return reg.status  # "pending_team" or "joined"


def is_registered(user_id, competition_id):
    """True iff the user is fully registered (status == 'joined')."""
    return get_registration_status(user_id, competition_id) == "joined"


def get_competition_team(user_id, competition_id):
    """
    Return the CompetitionTeamMember row for this user in this competition,
    or None if the user has no team assignment for this competition.
    """
    from CTFd.models import CompetitionTeamMember

    return CompetitionTeamMember.query.filter_by(
        competition_id=competition_id, user_id=user_id
    ).first()


def register_user(user_id, competition_id, force=False):
    """
    Register a user for a competition by creating a CompetitionUser row.

    - users-mode competitions:  status is set to 'joined' immediately.
    - teams-mode competitions:  status is set to 'pending_team'; the user
      must then create or join a competition team to become fully 'joined'.

    If the user is already registered, the existing row is returned with no
    error (idempotent).

    Returns (CompetitionUser | None, error_str | None).
    Pass force=True to bypass the can_register() timing check (admin use).
    """
    from sqlalchemy.exc import IntegrityError

    from CTFd.models import Competition, CompetitionUser, db

    comp = Competition.query.filter_by(id=competition_id).first()
    if comp is None:
        return None, "Competition not found"

    existing = get_registration(user_id, competition_id)
    if existing is not None:
        return existing, None

    if not force and not can_register(comp):
        return None, "Registration is currently closed for this competition"

    initial_status = "pending_team" if comp.user_mode == "teams" else "joined"
    reg = CompetitionUser(
        competition_id=competition_id,
        user_id=user_id,
        status=initial_status,
    )
    db.session.add(reg)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Concurrent insert — return existing row
        reg = CompetitionUser.query.filter_by(
            competition_id=competition_id, user_id=user_id
        ).first()
    return reg, None


def create_competition_team(user_id, competition_id, team_name, team_password=None):
    """
    Create a new team for a competition and register the user on it.

    Steps:
      1. Create a global Teams row (teams are global objects).
      2. Create a CompetitionTeam row (enroll team in competition).
      3. Create a CompetitionTeamMember row (user → team for this competition).
      4. Set CompetitionUser.status = 'joined'.

    Returns (Teams | None, error_str | None).
    """
    from sqlalchemy.exc import IntegrityError

    from CTFd.models import (
        Competition,
        CompetitionTeam,
        CompetitionTeamMember,
        CompetitionUser,
        Teams,
        db,
    )

    comp = Competition.query.filter_by(id=competition_id).first()
    if comp is None:
        return None, "Competition not found"

    reg = get_registration(user_id, competition_id)
    if reg is None:
        return None, "You must join the competition before creating a team"

    if get_competition_team(user_id, competition_id) is not None:
        return None, "You are already on a team in this competition"

    team_name = (team_name or "").strip()
    if not team_name:
        return None, "Team name is required"

    # Enforce team name uniqueness within this competition
    name_conflict = (
        Teams.query.join(CompetitionTeam, Teams.id == CompetitionTeam.team_id)
        .filter(CompetitionTeam.competition_id == competition_id)
        .filter(Teams.name == team_name)
        .first()
    )
    if name_conflict is not None:
        return None, f"A team named '{team_name}' already exists in this competition"

    try:
        from CTFd.utils.crypto import hash_password

        team = Teams(name=team_name, captain_id=user_id)
        if team_password:
            team.password = hash_password(team_password)
        db.session.add(team)
        db.session.flush()  # materialise team.id

        db.session.add(CompetitionTeam(competition_id=competition_id, team_id=team.id))
        db.session.add(
            CompetitionTeamMember(
                competition_id=competition_id,
                team_id=team.id,
                user_id=user_id,
            )
        )
        reg.status = "joined"
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "Team name conflict — please choose a different name"

    return team, None


def join_competition_team(user_id, competition_id, team_id, team_password=None):
    """
    Join an existing team in a competition.

    Prerequisites:
      - User has a CompetitionUser row for this competition.
      - User is not already on a team in this competition.
      - The team has a CompetitionTeam row for this competition.
      - Team is not full (respects competition.team_size when > 0).
      - Correct team password is provided if the team is password-protected.

    Returns (CompetitionTeamMember | None, error_str | None).
    """
    from sqlalchemy.exc import IntegrityError

    from CTFd.models import (
        Competition,
        CompetitionTeam,
        CompetitionTeamMember,
        CompetitionUser,
        Teams,
        db,
    )

    comp = Competition.query.filter_by(id=competition_id).first()
    if comp is None:
        return None, "Competition not found"

    reg = get_registration(user_id, competition_id)
    if reg is None:
        return None, "You must join the competition before joining a team"

    if get_competition_team(user_id, competition_id) is not None:
        return None, "You are already on a team in this competition"

    comp_team = CompetitionTeam.query.filter_by(
        competition_id=competition_id, team_id=team_id
    ).first()
    if comp_team is None:
        return None, "That team is not enrolled in this competition"

    team = Teams.query.filter_by(id=team_id).first()
    if team is None:
        return None, "Team not found"

    if team.password:
        from CTFd.utils.crypto import verify_password

        if not team_password:
            return None, "This team requires a password"
        if not verify_password(team_password, team.password):
            return None, "Incorrect team password"

    if comp.team_size and comp.team_size > 0:
        current_count = CompetitionTeamMember.query.filter_by(
            competition_id=competition_id, team_id=team_id
        ).count()
        if current_count >= comp.team_size:
            return None, f"This team is full (max {comp.team_size} members)"

    try:
        membership = CompetitionTeamMember(
            competition_id=competition_id,
            team_id=team_id,
            user_id=user_id,
        )
        db.session.add(membership)
        reg.status = "joined"
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "Failed to join team — you may already be on a team in this competition"

    return membership, None


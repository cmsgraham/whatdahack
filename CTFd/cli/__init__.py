import datetime
import shutil
from pathlib import Path

import click
from flask import Blueprint, current_app

from CTFd.utils import get_config as get_config_util
from CTFd.utils import set_config as set_config_util
from CTFd.utils.config import ctf_name
from CTFd.utils.exports import export_ctf as export_ctf_util
from CTFd.utils.exports import import_ctf as import_ctf_util
from CTFd.utils.exports import set_import_end_time, set_import_error

_cli = Blueprint("cli", __name__)


def jsenums():
    import json
    import os

    from CTFd.constants import JS_ENUMS

    path = os.path.join(current_app.root_path, "themes/core/assets/js/constants.js")

    with open(path, "w+") as f:
        for k, v in JS_ENUMS.items():
            f.write("const {} = Object.freeze({});".format(k, json.dumps(v)))


BUILD_COMMANDS = {"jsenums": jsenums}


@_cli.cli.command("get_config")
@click.argument("key")
def get_config(key):
    print(get_config_util(key))


@_cli.cli.command("set_config")
@click.argument("key")
@click.argument("value")
def set_config(key, value):
    print(set_config_util(key, value).value)


@_cli.cli.command("build")
@click.argument("cmd")
def build(cmd):
    cmd = BUILD_COMMANDS.get(cmd)
    cmd()


@_cli.cli.command("export_ctf")
@click.argument("path", default="")
def export_ctf(path):
    backup = export_ctf_util()

    if path:
        with open(path, "wb") as target:
            shutil.copyfileobj(backup, target)
    else:
        name = ctf_name()
        day = datetime.datetime.now().strftime("%Y-%m-%d_%T")
        full_name = f"{name}.{day}.zip"

        with open(full_name, "wb") as target:
            shutil.copyfileobj(backup, target)

        print(f"Exported {full_name}")


@_cli.cli.command("import_ctf")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--delete_import_on_finish",
    default=False,
    is_flag=True,
    help="Delete import file when import is finished",
)
def import_ctf(path, delete_import_on_finish=False):
    try:
        import_ctf_util(path)
    except Exception as e:
        from CTFd.utils.dates import unix_time

        set_import_error("Import Failure: " + str(e))
        set_import_end_time(value=unix_time(datetime.datetime.utcnow()))

    if delete_import_on_finish:
        print(f"Deleting {path}")
        Path(path).unlink()


@_cli.cli.command("init-default-competition")
@click.option(
    "--slug",
    required=True,
    help="URL-safe competition identifier, e.g. wdh-2026",
)
@click.option(
    "--name",
    required=True,
    help="Human-readable competition name, e.g. 'Whatdahack 2026'",
)
def init_default_competition(slug, name):
    """
    Create the initial Competition row and backfill all existing data into it.

    This command is idempotent-safe: it will exit with an error if a competition
    with the given slug already exists rather than overwriting data.

    Run AFTER applying the three Phase 1 migrations:
        flask db upgrade 7e4d2c6a8f1b
        flask init-default-competition --slug wdh-2026 --name "Whatdahack 2026"
    """
    from CTFd.models import (
        Awards,
        Challenges,
        Competition,
        CompetitionTeam,
        Submissions,
        Teams,
        db,
    )

    # --- Idempotency guard ---
    existing = Competition.query.filter_by(slug=slug).first()
    if existing:
        click.echo(
            f"ERROR: A competition with slug '{slug}' already exists "
            f"(id={existing.id}). Aborting to prevent data corruption.",
            err=True,
        )
        raise SystemExit(1)

    click.echo(f"Creating competition: name='{name}', slug='{slug}'")

    # --- Inherit timing and mode from global config ---
    start_ts = get_config_util("start")
    end_ts = get_config_util("end")
    freeze_ts = get_config_util("freeze")
    user_mode = get_config_util("user_mode") or "teams"

    comp = Competition(slug=slug, name=name, state="visible", user_mode=user_mode)

    if start_ts:
        comp.start = datetime.datetime.utcfromtimestamp(int(start_ts))
        click.echo(f"  Copied start time: {comp.start}")
    if end_ts:
        comp.end = datetime.datetime.utcfromtimestamp(int(end_ts))
        click.echo(f"  Copied end time:   {comp.end}")
    if freeze_ts:
        comp.freeze = datetime.datetime.utcfromtimestamp(int(freeze_ts))
        click.echo(f"  Copied freeze time: {comp.freeze}")

    db.session.add(comp)
    # Flush to get comp.id without committing — lets us roll back everything on error.
    db.session.flush()
    click.echo(f"  Competition row inserted with id={comp.id}")

    # --- Backfill existing rows (only rows where competition_id IS NULL) ---
    challenge_count = Challenges.query.filter(
        Challenges.competition_id.is_(None)
    ).update({"competition_id": comp.id}, synchronize_session=False)
    click.echo(f"  Backfilled {challenge_count} challenges")

    submission_count = Submissions.query.filter(
        Submissions.competition_id.is_(None)
    ).update({"competition_id": comp.id}, synchronize_session=False)
    click.echo(f"  Backfilled {submission_count} submissions")

    award_count = Awards.query.filter(
        Awards.competition_id.is_(None)
    ).update({"competition_id": comp.id}, synchronize_session=False)
    click.echo(f"  Backfilled {award_count} awards")

    # --- Create CompetitionTeam membership rows for all existing teams ---
    teams = Teams.query.all()
    for team in teams:
        ct = CompetitionTeam(competition_id=comp.id, team_id=team.id)
        db.session.add(ct)
    click.echo(f"  Created {len(teams)} competition_team membership rows")

    db.session.commit()

    click.echo(
        f"\nDone. Competition '{name}' (slug='{slug}', id={comp.id}) is ready.\n"
        f"To make it the active competition for legacy routes, run:\n"
        f"  flask set_config active_competition {slug}"
    )

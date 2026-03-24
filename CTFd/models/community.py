import datetime

from CTFd.models import db


class CommunityChallenge(db.Model):
    __tablename__ = "community_challenges"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(80), nullable=False, index=True)
    difficulty = db.Column(db.String(20), nullable=False, default="medium")
    points = db.Column(db.Integer, nullable=False, default=100)
    flag = db.Column(db.Text, nullable=False)
    case_insensitive = db.Column(db.Boolean, default=False)
    state = db.Column(db.String(20), nullable=False, default="draft", index=True)
    tags = db.Column(db.Text, default="")
    attachment_url = db.Column(db.Text, nullable=True)
    banner_url = db.Column(db.Text, nullable=True)

    # Denormalized counters
    solve_count = db.Column(db.Integer, default=0)
    attempt_count = db.Column(db.Integer, default=0)
    thumbs_up = db.Column(db.Integer, default=0)
    thumbs_down = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # Relationships
    author = db.relationship(
        "Users", backref=db.backref("community_challenges", lazy="dynamic")
    )
    solves = db.relationship(
        "CommunitySolve",
        backref="challenge",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    attempts = db.relationship(
        "CommunityAttempt",
        backref="challenge",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    ratings = db.relationship(
        "CommunityRating",
        backref="challenge",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def success_rate(self):
        if self.attempt_count == 0:
            return 0
        return round(self.solve_count / self.attempt_count * 100)

    @property
    def rating_percent(self):
        total = self.thumbs_up + self.thumbs_down
        if total == 0:
            return 0
        return round(self.thumbs_up / total * 100)

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def community_difficulty(self):
        total_votes = self.thumbs_up + self.thumbs_down
        if total_votes < 5 or self.attempt_count < 3:
            return self.difficulty
        sr = self.success_rate
        if sr < 10:
            return "insane"
        elif sr < 25:
            return "hard"
        elif sr < 50:
            return "medium"
        else:
            return "easy"

    def __repr__(self):
        return f"<CommunityChallenge {self.id} {self.title!r}>"


class CommunitySolve(db.Model):
    __tablename__ = "community_solves"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("community_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    solved_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_first_blood = db.Column(db.Boolean, default=False)
    award_id = db.Column(
        db.Integer, db.ForeignKey("awards.id", ondelete="SET NULL"), nullable=True
    )

    user = db.relationship(
        "Users", backref=db.backref("community_solves", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint("challenge_id", "user_id", name="uq_community_solve"),
    )


class CommunityAttempt(db.Model):
    __tablename__ = "community_attempts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("community_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_correct = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship(
        "Users", backref=db.backref("community_attempts", lazy="dynamic")
    )


class CommunityRating(db.Model):
    __tablename__ = "community_ratings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("community_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value = db.Column(db.Integer, nullable=False)  # 1 = thumbs up, -1 = thumbs down
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship(
        "Users", backref=db.backref("community_ratings", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint("challenge_id", "user_id", name="uq_community_rating"),
    )


def init_community_tables(app):
    """Create community tables if they don't exist."""
    with app.app_context():
        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(db.engine)
        existing = set(inspector.get_table_names())
        tables_needed = [
            CommunityChallenge.__table__,
            CommunitySolve.__table__,
            CommunityAttempt.__table__,
            CommunityRating.__table__,
        ]
        tables_to_create = [t for t in tables_needed if t.name not in existing]
        if tables_to_create:
            db.metadata.create_all(db.engine, tables=tables_to_create)

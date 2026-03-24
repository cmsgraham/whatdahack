import datetime
import json

from CTFd.models import db


class SocialPost(db.Model):
    __tablename__ = "social_posts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(
        db.String(20), nullable=False, default="text", index=True
    )  # text, solve, discussion, question
    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("community_challenges.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tags = db.Column(db.Text, default="")
    image_url = db.Column(db.Text, nullable=True)
    images = db.Column(db.Text, nullable=True)  # JSON list of image URLs
    link_url = db.Column(db.Text, nullable=True)

    # Denormalized counters
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)

    pinned = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False, index=True)

    created_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    author = db.relationship(
        "Users", backref=db.backref("social_posts", lazy="dynamic")
    )
    challenge_ref = db.relationship(
        "CommunityChallenge",
        backref=db.backref("social_posts", lazy="dynamic"),
    )
    likes = db.relationship(
        "SocialLike",
        backref="post",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    comments = db.relationship(
        "SocialComment",
        backref="post",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def image_list(self):
        if not self.images:
            return []
        try:
            return json.loads(self.images)
        except (json.JSONDecodeError, TypeError):
            return []

    def __repr__(self):
        return f"<SocialPost {self.id}>"


class SocialComment(db.Model):
    __tablename__ = "social_comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("social_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content = db.Column(db.Text, nullable=False)
    like_count = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, index=True
    )

    author = db.relationship(
        "Users", backref=db.backref("social_comments", lazy="dynamic")
    )
    replies = db.relationship(
        "SocialComment",
        backref=db.backref("parent", remote_side="SocialComment.id"),
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<SocialComment {self.id}>"


class SocialLike(db.Model):
    __tablename__ = "social_likes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    comment_id = db.Column(
        db.Integer,
        db.ForeignKey("social_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("Users", backref=db.backref("social_likes", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "post_id", name="uq_social_like_post"),
        db.UniqueConstraint("user_id", "comment_id", name="uq_social_like_comment"),
    )


class SocialFollow(db.Model):
    __tablename__ = "social_follows"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    follower_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    following_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    follower = db.relationship(
        "Users",
        foreign_keys=[follower_id],
        backref=db.backref("following", lazy="dynamic"),
    )
    following_user = db.relationship(
        "Users",
        foreign_keys=[following_id],
        backref=db.backref("followers", lazy="dynamic"),
    )

    __table_args__ = (
        db.UniqueConstraint("follower_id", "following_id", name="uq_social_follow"),
    )


class SocialNotification(db.Model):
    __tablename__ = "social_notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    verb = db.Column(
        db.String(30), nullable=False
    )  # liked_post, commented, followed, liked_comment
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=True,
    )
    comment_id = db.Column(
        db.Integer,
        db.ForeignKey("social_comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, index=True
    )

    user = db.relationship(
        "Users",
        foreign_keys=[user_id],
        backref=db.backref("social_notifications", lazy="dynamic"),
    )
    actor = db.relationship("Users", foreign_keys=[actor_id])

    def __repr__(self):
        return f"<SocialNotification {self.id} {self.verb}>"


class SocialReport(db.Model):
    __tablename__ = "social_reports"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reporter_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=True,
    )
    comment_id = db.Column(
        db.Integer,
        db.ForeignKey("social_comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    reason = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    reporter = db.relationship("Users", backref=db.backref("social_reports", lazy="dynamic"))


def init_social_tables(app):
    """Create social tables if they don't exist."""
    with app.app_context():
        from sqlalchemy import inspect as sa_inspect, text

        inspector = sa_inspect(db.engine)
        existing = set(inspector.get_table_names())
        tables_needed = [
            SocialPost.__table__,
            SocialComment.__table__,
            SocialLike.__table__,
            SocialFollow.__table__,
            SocialNotification.__table__,
            SocialReport.__table__,
        ]
        tables_to_create = [t for t in tables_needed if t.name not in existing]
        if tables_to_create:
            db.metadata.create_all(db.engine, tables=tables_to_create)

        # Auto-add images column if missing (migration for existing installs)
        if "social_posts" in existing:
            cols = {c["name"] for c in inspector.get_columns("social_posts")}
            if "images" not in cols:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE social_posts ADD COLUMN images TEXT"))
                    conn.commit()

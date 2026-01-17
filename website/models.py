from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import JSON

# View analytics
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    posts = db.relationship('Post', backref='user', passive_deletes=True)
    comments = db.relationship('Comment', backref='user', passive_deletes=True)
    admin = db.Column(db.Boolean, default=False)

class poker_members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    course = db.Column(db.String(150), nullable=False)
    year = db.Column(db.String(150), nullable=False)
    sex = db.Column(db.String(150), nullable=False)

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('quiz_results', lazy=True))
    session_data = db.Column(JSON, nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    comments = db.relationship('Comment', backref='post', passive_deletes=True)
    file_data = db.Column(db.LargeBinary, nullable=True)  # New field for file contents
    data_frame = db.Column(db.Text, nullable=True)  # Field for DataFrame JSON string
    data_frame_results = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # New field for category
    stake = db.Column(db.String(50), nullable=False)
    game_type = db.Column(db.String(20), nullable=True)  # 'cash' or 'tournament'
    table_size = db.Column(db.String(20), nullable=True)  # e.g., '6-max', '9-max', 'full ring'
    game_name = db.Column(db.String(100), nullable=True)  # Name of the game
    buy_in = db.Column(db.Float, nullable=True)  # Buy-in amount
    cash_out = db.Column(db.Float, nullable=True)  # Cash-out amount
    currency = db.Column(db.String(10), nullable=True, default='USD')  # Currency code

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author = db.Column(db.Integer, db.ForeignKey(
        'user.id', ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey(
        'post.id', ondelete="CASCADE"), nullable=False)

class SharedPassword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(150), nullable=False)


class QuantMathResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    total_time = db.Column(db.Float, nullable=False)
    mean_bayes_time = db.Column(db.Float, nullable=False)
    mean_coupon_time = db.Column(db.Float, nullable=False)
    mean_option_time = db.Column(db.Float, nullable=False)
    mean_ev_time = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=func.now(), nullable=False)

class LiveSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    session_date = db.Column(db.DateTime(timezone=True), nullable=False)
    location = db.Column(db.String(200), nullable=True)  # Casino/venue name
    game_type = db.Column(db.String(20), nullable=True)  # 'cash' or 'tournament'
    table_size = db.Column(db.String(20), nullable=True)  # e.g., '6-max', '9-max', 'full ring'
    game_name = db.Column(db.String(100), nullable=True)  # Name of the game
    stakes = db.Column(db.String(50), nullable=False)  # e.g., "1/2", "2/5", "5/10"
    buy_in = db.Column(db.Float, nullable=False)  # Amount bought in for
    cash_out = db.Column(db.Float, nullable=False)  # Amount cashed out
    currency = db.Column(db.String(10), nullable=True, default='USD')  # Currency code
    hours_played = db.Column(db.Float, nullable=True)  # Optional hours played
    notes = db.Column(db.Text, nullable=True)  # Optional notes
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    
    @property
    def profit_loss(self):
        """Calculate profit/loss for this session"""
        return self.cash_out - self.buy_in
    
    @property
    def is_winning_session(self):
        """Check if session was profitable"""
        return self.profit_loss > 0
    
    def get_big_blind(self):
        """Extract big blind from stakes string (e.g., '1/2' -> 2, '2/5' -> 5)"""
        if not self.stakes:
            return None
        try:
            # Split by '/' and take the second part as big blind
            parts = self.stakes.split('/')
            if len(parts) == 2:
                return float(parts[1])
        except (ValueError, IndexError):
            pass
        return None
    
    @property
    def profit_loss_bb(self):
        """Calculate profit/loss in big blinds"""
        big_blind = self.get_big_blind()
        if big_blind and big_blind > 0:
            return self.profit_loss / big_blind
        return None
    
    @property
    def bb_per_hour(self):
        """Calculate BB/hour for this session"""
        if self.hours_played and self.hours_played > 0:
            profit_bb = self.profit_loss_bb
            if profit_bb is not None:
                return profit_bb / self.hours_played
        return None

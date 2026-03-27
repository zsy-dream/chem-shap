from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='researcher')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Sample(db.Model):
    __tablename__ = 'samples'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.String(64), unique=True, nullable=False)
    experiment_round = db.Column(db.Integer)
    experiment_group = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    records = db.relationship('ExperimentRecord', backref='sample', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('OptimizationReport', backref='sample', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def display_name(self):
        return self.sample_id


class ExperimentRecord(db.Model):
    __tablename__ = 'experiment_records'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), nullable=False)
    feature_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MLModel(db.Model):
    __tablename__ = 'models'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    model_type = db.Column(db.String(64))
    file_path = db.Column(db.String(256), nullable=False)
    metrics = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=False)
    reports = db.relationship('OptimizationReport', backref='model', lazy='dynamic', cascade='all, delete-orphan')


class OptimizationReport(db.Model):
    __tablename__ = 'optimization_reports'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('models.id'), nullable=False)
    success_probability = db.Column(db.Float)
    shap_values = db.Column(db.JSON)
    top_features = db.Column(db.JSON)
    expert_advice = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def result_level(self):
        probability = self.success_probability or 0
        if probability >= 0.75:
            return 'excellent'
        if probability >= 0.5:
            return 'good'
        return 'needs_optimization'


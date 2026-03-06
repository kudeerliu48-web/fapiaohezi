# -*- coding: utf-8 -*-
"""用户与发票解析记录模型"""
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask import current_app

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), default="user", nullable=False)  # user | admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InvoiceRecord(db.Model):
    __tablename__ = "invoice_records"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    task_id = db.Column(db.String(64), nullable=False, index=True)
    source = db.Column(db.String(32), nullable=False)  # upload | email
    file_count = db.Column(db.Integer, default=0)
    excel_key = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default="done")  # running | done | error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("invoice_records", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "task_id": self.task_id,
            "source": self.source,
            "file_count": self.file_count,
            "excel_key": self.excel_key,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

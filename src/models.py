from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), unique=False, nullable=False)
    email = db.Column(db.String(150), unique=False, nullable=False)
    agenda_slug = db.Column(db.String(150), unique=False, nullable=False)
    address = db.Column(db.String(150), unique=False, nullable=False)
    phone = db.Column(db.String(20), unique=False, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.email

    def serialize(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "agenda_slug": self.agenda_slug,
            "address": self.address,
            "phone": self.phone
            # do not serialize the password, its a security breach
        }
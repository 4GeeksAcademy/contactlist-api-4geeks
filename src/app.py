"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os, re
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, Contact
from sqlalchemy import and_

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

## START -- API POST -- START ##
@app.route('/contacts', methods=['POST'])
def create_one_contact():
    # We verify that all the data necessary to create a contact can be obtained.
    full_name = email = agenda_slug = address = phone = None
    try:
        full_name = request.json["full_name"]
        email = request.json["email"]
        agenda_slug = request.json["agenda_slug"]
        address = request.json["address"]
        phone = request.json["phone"]
    except KeyError as e:
        raise APIException(f"You need specify the contact's {e.args[0]}.", status_code=400)

    # We run the different verifications, depending on the data we have.
    values = {"full_name": full_name, "email": email, "agenda_slug": agenda_slug, "address": address, "phone": phone}
    execute_verifications(values)

    # We create the new contact and return a message.
    new_contact = Contact(full_name=full_name, email=email, agenda_slug=agenda_slug, address=address, phone=phone)

    db.session.add(new_contact)
    db.session.commit()
    return jsonify({"message": f"Contact {full_name} is added succesfully to {agenda_slug} agenda."}), 200
## END -- API POST -- END ##

## START -- API GET -- START ##
@app.route('/contacts/agendas', methods=['GET'])
def get_agendas():
    # We get all the agendas available so far.
    agendas = Contact.query.with_entities(Contact.agenda_slug).all()
    
    if len(agendas) == 0:
        raise APIException('Not found', status_code=404)
    
    results = list(map(lambda item: dict(item)["agenda_slug"], agendas))
    return jsonify(results), 200

@app.route('/contacts/agenda/<string:agenda_slug>', methods=['GET'])
def get_contacts_from_agenda(agenda_slug):
    # We obtain all the contacts of a specific agenda.
    contacts = Contact.query.filter_by(agenda_slug=agenda_slug).all()
    
    if len(contacts) == 0:
        raise APIException(f'No contacts found in the {agenda_slug} agenda.', status_code=404)
    
    results = list(map(lambda item: item.serialize(), contacts))
    return jsonify(results), 200

@app.route('/contacts/<int:contact_id>', methods=['GET'])
def get_one_contact_by_id(contact_id):
    # We obtain a contact with specific id.
    contact = Contact.query.filter_by(id=contact_id).first()
    
    if contact is None:
        raise APIException(f'The contact with the id {contact_id} was not found.', status_code=404)
    
    result = contact.serialize()
    return jsonify(result), 200
## END -- API GET -- END ##

## START -- API PUT -- START ##
@app.route('/contacts/<int:contact_id>', methods=['PUT'])
def modify_one_contact_by_id(contact_id):
    # We modify a contact with specific id.
    body = request.json
    contact = Contact.query.filter_by(id=contact_id).first()
    
    if contact is None:
        raise APIException(f'The contact with the id {contact_id} was not found.', status_code=404)

    execute_verifications(body)
    for key in body:
        for col in contact.serialize():
            if key == col and key != "id":
                setattr(contact, col, body[key])
    
    db.session.commit()

    return jsonify({"message": f"The contact with the id {contact_id} modified succesfully."}), 200
## END -- API PUT -- END ##

## START -- API DELETE -- START ##
@app.route('/contacts/<int:contact_id>', methods=['DELETE'])
def delete_one_contact_by_id(contact_id):
    # We delete a contact with specific id.
    contact = Contact.query.filter_by(id=contact_id).first()
    
    if contact is None:
        raise APIException(f'The contact with the id {contact_id} was not found.', status_code=404)

    Contact.query.filter_by(id=contact_id).delete()
    db.session.commit()

    return jsonify({"message": f"The contact with the id {contact_id} deleted succesfully."}), 200
## END -- API DELETE -- END ##


def verify_regex(key, value, regex):
    if not re.match(regex, value):
        raise APIException(f'You need specify a valid {key}.', status_code=400)

def verify_length(value, key, min, max):
    if len(value) < min:
        raise APIException(f"The minimum length for contact's {key} is {min} characters.", status_code=400)
    
    if len(value) > max:
        raise APIException(f"The maximum length for contact's {key} is {max} characters.", status_code=400)


def verify_many_empty(values):
    for key in values:
        if values[key] is None or values[key] == "":
            raise APIException(f"The contact's {key} cannot be empty.", status_code=400)

def verify_email_exist_in_agenda(agenda_slug, email):
        contact = Contact.query.filter(and_(Contact.agenda_slug == agenda_slug, Contact.email == email)).first()
        if contact:
            raise APIException(f"The contact with the email {email} already exist in {agenda_slug} agenda.", status_code=403)

def execute_verifications(values):
    allowed_keys = ['full_name', 'email', 'agenda_slug', 'address', 'phone']
    for key in values:
        if key not in allowed_keys:
            raise APIException(f"The {key} is not a valid key.", status_code=400)
    
    verify_many_empty(values)
    
    if 'email' in values and 'agenda_slug' in values:
        verify_email_exist_in_agenda(values['agenda_slug'], values['email'])
    
    if 'email' in values:
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        verify_regex('email address', values['email'], email_regex)
    
    if 'phone' in values:
        phone_regex = r'^[0-9]+$'
        verify_regex('phone number', values['phone'], phone_regex)
        verify_length(values['phone'], 'phone', 3, 20)
    
    if 'agenda_slug' in values:
        if re.search(r"\s", values['agenda_slug']):
            raise APIException(f"The agenda_slug must not contain spaces.", status_code=400)
    

# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)

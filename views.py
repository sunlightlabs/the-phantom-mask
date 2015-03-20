from flask import render_template
from flask import jsonify
import forms
from flask import request
from postmark_inbound import PostmarkInbound
from sqlalchemy import func

def index():
    # create a list of dictionaries
    #data = [{'name':'olivia','color':'red', 'age':26},
    #         {'name':'tom','color':'green', 'age':34}]
    # add values from URL if present
    #if name is not None:
    #    data.append({'name':name,'color': color, 'age':age})
    # renders index.html from templates directory, passing in the names variable
    return render_template('index.html')

def verify_message(verification_token):
    from models import Message
    msg = Message.query.filter_by(verification_token=verification_token).first()
    form = forms.RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        pass
    else:
        if msg is not None:
            return render_template("verify.html", context={'message': msg, 'form':form})
        else:
            return render_template("verify.html", context={})

def postmark():
    from models import db
    from models import Message
    from models import Legislator
    from models import MessageLegislator
    try:
        inbound = PostmarkInbound(json=request.get_data())
        if Message.query.filter_by(email_uid=inbound.message_id()).first() is None:
            new = Message(sent_at=inbound.send_date(),
                          from_email=inbound.sender()['Email'],
                          subject=inbound.subject(),
                          body=inbound.text_body(),
                          email_uid=inbound.message_id())
            db.session.add(new)
            for person in inbound.to():
                leg = Legislator.query.filter(func.lower(Legislator.oc_email) == func.lower(person['Email'])).first()
                if leg is not None and leg.contactable:
                    ml = MessageLegislator(message_id=new.id, legislator_id=leg.bioguide_id)
                    db.session.add(ml)
                else:
                    print 'Not contactable'
                    pass # TODO send error message back to user
            db.session.commit()
        return jsonify({'status': 'successfully received postmark message'})
    except:
        return "Unable to parse postmark message.", 500
        # TODO send admin error message
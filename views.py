from flask import render_template
from flask import jsonify
import forms
from flask import request
from postmark_inbound import PostmarkInbound
from sqlalchemy import func
import traceback
from services import zip_inferrence_service
import json
from lib.usps import CODE_TO_STATE
import emailer

def legislator_index():
    from models import Legislator
    return render_template('pages/legislator_index.html', context={'legislators': Legislator.query.all(),
                                                                   'states': CODE_TO_STATE })

def verify_message(verification_token):
    from models import Message

    # verify that message with uid exists
    msg = Message.query.filter_by(verification_token=verification_token).first()
    if msg is None:
        return render_template("pages/verify.html", context={})

    # verify that the associated user matches
    msg_email = msg.user_message_info.user.email
    email_param = request.args.get('email', None)
    if email_param is None or msg_email != email_param:
        # email param not provided or doesn't message uid of message, return error page
        return render_template("pages/verify.html", context={})

    form = forms.RegistrationForm(request.form)
    context = {'message':msg, 'form':form, 'verification_token':verification_token, 'msg_email':msg_email}

    if request.method == 'POST':
        from models import db
        # get zip4 so user doesn't have to look it up
        form.zip4.data = zip_inferrence_service.zip4_lookup(request.form.get('street_address'),
                                                            request.form.get('city'),
                                                            request.form.get('state'),
                                                            request.form.get('zip5'))

        # check if user is trying to message somebody from outside their state/district
        #does_not_represent = form.validate_district(msg.get_legislators())
        #if does_not_represent is None or len(does_not_represent) > 0:
        #    return render_template("verify.html", context=dict(context,**{'does_not_rep': does_not_represent}))

        if form.validate():
            form.save_to_models(msg)
            return json.dumps([[x,y.json] for x,y in msg.send().iteritems()])
        else:
            return "doesn't work"

            # TODO 1) validate address matches correct representative
            # 2) notify user if it doesn't
            # 3) create redis entry to make API call to phantom-on-the-capitol
            # 4) receive result and save to database
    else:
        return render_template("pages/verify.html", context=context)

def postmark():
    """
    View to handle inbound postmark e-mails.

    @return:
    """
    from models import db
    from models import Message
    from models import Legislator
    from models import MessageLegislator
    from models import User
    from models import UserMessageInfo
    try:
        # parse inbound postmark JSON
        inbound = PostmarkInbound(json=request.get_data())

        # get existing user or create new one
        sender = User.query.filter_by(email=inbound.sender()['Email']).first()
        if sender is None:
            sender = User(email=inbound.sender()['Email'])
            db.session.add(sender) and db.session.commit()

        newinfo = UserMessageInfo(user_id=sender.id)
        db.session.add(newinfo) and db.session.commit()

        # check if message exists already
        if Message.query.filter_by(email_uid=inbound.message_id()).first() is None:
            new = Message(sent_at=inbound.send_date(),
                          subject=inbound.subject(),
                          msgbody=inbound.text_body(),
                          email_uid=inbound.message_id(),
                          user_message_info_id=newinfo.id)
            db.session.add(new) and db.session.commit()

            legs = {True: [], False: []}
            for person in inbound.to():
                # insure legislator exists and is contactable
                leg = Legislator.query.filter(func.lower(Legislator.oc_email) == func.lower(person['Email'])).first()
                if leg is None or not leg.contactable:
                    legs[False].append(person['Email'].lower())
                else:
                    legs[True].append(leg)

            for leg in legs[True]:
                ml = MessageLegislator(message_id=new.id, legislator_id=leg.bioguide_id)
                db.session.add(ml)
            db.session.commit()

            # create outbound to send to user to confirm their information
            if inbound.sender()['Email'] == 'rioisk@gmail.com':
                emailer.complete_message(inbound,legs[True],new).send()
            else:
                print "not rioisk"

        return jsonify({'status': 'successfully received postmark message'})
    except:
        print traceback.format_exc()
        return "Unable to parse postmark message.", 500
        # TODO send admin error message
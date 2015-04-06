from flask import render_template
from flask import jsonify
import forms
from flask import request
from postmark_inbound import PostmarkInbound
import traceback
import json
from lib.usps import CODE_TO_STATE
import emailer

def legislator_index():
    from models import Legislator
    from models import User
    print User.query.first().should_rate_limit()
    return render_template('pages/legislator_index.html', context={'legislators': Legislator.query.all(),
                                                                   'states': CODE_TO_STATE })

def verify_message(verification_token):
    from models import Message

    # verify that message with uid exists
    msg = Message.query.filter_by(verification_token=verification_token).first()
    if msg is None:
        return render_template("pages/verify.html", context={})
    else: # verify that the associated user matches
        msg_email = msg.user_message_info.user.email
        email_param = request.args.get('email', None)
        if email_param is None or msg_email != email_param:
            # email param not provided or doesn't message uid of message, return error page
            return render_template("pages/verify.html", context={})
    #### END SANITIZING ####

    form = forms.RegistrationForm(request.form)
    context = {
        'message': msg,
        'form': form,
        'verification_token': verification_token,
        'msg_email': msg_email
    }

    if request.method == 'POST':
        # get zip4 so user doesn't have to look it up
        form.resolve_zip4()

        # check if user is trying to message somebody from outside their state/district
        #does_not_represent = form.validate_district(msg.get_legislators())
        #if does_not_represent is None or len(does_not_represent) > 0:
        #    return render_template("verify.html", context=dict(context,**{'does_not_rep': does_not_represent}))

        if form.validate():
            form.save_to_models(msg)
            # TODO need to handle case where recipient legislators don't match represent address

            return json.dumps([[x,y.json] for x,y in msg.send().iteritems()])
        else:
            return "doesn't work"

            # TODO 1) validate address matches correct representative
            # 2) notify user if it doesn't
            # 3) create redis entry to make API call to phantom-on-the-capitol
            # 4) receive result and save to database
    else:
        form.populate_data_from_message(msg)
        return render_template("pages/verify.html", context=context)

def postmark():
    """
    View to handle inbound postmark e-mails.

    @return:
    """
    from models import db
    from models import db_add_and_commit
    from models import db_first_or_create
    from models import Message
    from models import Legislator
    from models import MessageLegislator
    from models import User
    from models import UserMessageInfo
    try:
        # parse inbound postmark JSON
        inbound = PostmarkInbound(json=request.get_data())

        user = db_first_or_create(User, email=inbound.sender()['Email'].lower())
        umi = db_first_or_create(UserMessageInfo, user_id=user.id, default=True)

        # check if message exists already
        if Message.query.filter_by(email_uid=inbound.message_id()).first() is None:
            new_msg = Message(sent_at=inbound.send_date(),
                              subject=inbound.subject(),
                              msgbody=inbound.text_body(),
                              email_uid=inbound.message_id(),
                              user_message_info_id=umi.id)
            db_add_and_commit(new_msg)

            if not umi.check_for_validate_tos():
                emailer.NoReply.validate_user(user.email, new_msg.verification_link()).send()
                return jsonify({'status': 'user must first accept tos'})
            else:
                permitted_legs = umi.members_of_congress
                legs = {'contactable': [], 'non_existent': [], 'uncontactable': [], 'does_not_represent': []}

                # maximize error messages for users
                for recipient in inbound.to():
                    recip_email = recipient['Email'].lower()
                    leg = Legislator.query.filter_by(oc_email=recip_email).first()
                    if leg is None:
                        leg['contactable'].append(recip_email)  # TODO refer user to index
                    elif not leg.contactable:
                        leg['uncontactable'].append(leg)
                    elif leg not in permitted_legs:
                        leg['does_not_represent'].append(leg)
                    else:
                        leg['contactable'].append(leg)

                # only associate members of congress that this user is allowed to contact
                for leg in legs['contactable']:
                    ml = MessageLegislator(message_id=new_msg.id, legislator_id=leg.bioguide_id)
                    db.session.add(ml)
                db.session.commit()

                # send different email depending on the status of the rate limiting...
                message = {
                    'free': emailer.NoReply.message_receipt(user.email, legs,
                                                            new_msg.verification_link()),
                    'captcha': emailer.NoReply.message_receipt(user.email, legs,
                                                               new_msg.verification_link()),
                    'block': emailer.NoReply.message_receipt(user.email, legs,
                                                             new_msg.verification_link())
                }.get(user.rate_limit_status())

                if message is not None: message.send()

                return jsonify({'status': 'successfully received postmark message'})
        else:
            return jsonify({'status': 'message already received'})
    except:
        print traceback.format_exc()
        return "Unable to parse postmark message.", 500
        # TODO send admin error message
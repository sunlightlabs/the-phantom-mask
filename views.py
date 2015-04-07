from flask import render_template, jsonify, redirect, request, url_for
import forms
from postmark_inbound import PostmarkInbound
import traceback
import json
from lib.usps import CODE_TO_STATE
import emailer
import urllib2
from phantom_mask import db
from models import Legislator, Message, MessageLegislator, User, UserMessageInfo, db_first_or_create, db_add_and_commit

def token_to_message(verification_token, email_param):
    """
    Converts a verification token string and email to message entry in the database.

    @param verification_token: the verification token in the url
    @type verification_token: string
    @param email_param: the email GET parameter
    @type email_param: string
    @return: the message instance or None
    @rtype: models.Message, None
    """
    msg = Message.query.filter_by(verification_token=verification_token).first()
    # verify that message with uid exists
    if msg is None or email_param is None or email_param != msg.user_message_info.user.email:
        return None
    return msg

def legislator_index():
    return render_template('pages/legislator_index.html', context={'legislators': Legislator.query.all(),
                                                                   'states': CODE_TO_STATE })


def confirm_reps(verification_token):

    msg = token_to_message(verification_token, request.args.get('email', None))
    if msg is None or msg.user_message_info.accept_tos is None:
        return "Msg is none or accept_tos is none"

    form = forms.MessageForm(request.form)

    print "Size of members of congress " + str(len(msg.user_message_info.members_of_congress))
    context = {
        'form': form,
        'message': msg,
        'umi': msg.user_message_info,
        'legislators': msg.user_message_info.members_of_congress,
        'uncontactable': ['test@example.com','test@example.com','test@example.com','test@example.com','test@example.com']
    }

    if request.method == 'POST':
        return 'it work'
    else:
        form.populate_data_from_message(msg)
        return render_template('pages/confirm_reps.html', context=context)


def register_user(verification_token):


    msg = token_to_message(verification_token, request.args.get('email', None))
    if msg is None:
        return render_template("pages/register_user.html", context={})

    form = forms.RegistrationForm(request.form)
    context = {
        'message': msg,
        'form': form,
        'verification_token': verification_token,
        'msg_email': msg.user_message_info.user.email
    }

    if request.method == 'POST':
        # get zip4 so user doesn't have to look it up
        form.resolve_zip4()

        # check if user is trying to message somebody from outside their state/district
        #does_not_represent = form.validate_district(msg.get_legislators())
        #if does_not_represent is None or len(does_not_represent) > 0:
        #    return render_template("verify.html", context=dict(context,**{'does_not_rep': does_not_represent}))

        if form.validate_and_save_to_db(msg):
            district = msg.user_message_info.determine_district()
            if district is None:
                context['district_error'] = True
                return render_template("pages/register_user.html", context=context)
            else:
                return redirect(url_for('app_router.confirm_reps', verification_token=verification_token) +
                                '?email=' + urllib2.quote(context['msg_email']))
        else:
            print 'ERROR 1'
            return render_template("pages/register_user.html", context=context)
    else:
        return render_template("pages/register_user.html", context=context)


def postmark_inbound():
    """
    View to handle inbound postmark e-mails.

    @return:
    """
    try:
        # parse inbound postmark JSON
        inbound = PostmarkInbound(json=request.get_data())

        user = db_first_or_create(User, email=inbound.sender()['Email'].lower())
        umi = db_first_or_create(UserMessageInfo, user_id=user.id, default=True)

        # check if message exists already
        if Message.query.filter_by(email_uid=inbound.message_id()).first() is None:
            new_msg = Message(sent_at=inbound.send_date(),
                              to=json.dumps([r['Email'].lower() for r in inbound.to()]),
                              subject=inbound.subject(),
                              msgbody=inbound.text_body(),
                              email_uid=inbound.message_id(),
                              user_message_info_id=umi.id)
            db_add_and_commit(new_msg)

            # first time user or it has been a long time since they've updated their address info
            if umi.should_update_address_info():
                emailer.NoReply.validate_user(user.email, new_msg.verification_link()).send()
                return jsonify({'status': 'user must accept tos / update their address info'})
            else:
                permitted_legs = umi.members_of_congress
                legs = {label: [] for label in ['contactable','non_existent','uncontactable','does_not_represent']}

                # maximize error messages for users
                for recipient in inbound.to():
                    recip_email = recipient['Email'].lower()
                    leg = Legislator.query.filter_by(oc_email=recip_email).first()
                    if leg is None:
                        leg['non_existent'].append(recip_email)  # TODO refer user to index
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

                rls = user.rate_limit_status()
                if user.rate_limit_status() == 'free':
                    pass  # TODO send to phantom of the capitol

                emailer.NoReply.message_receipt(user.email, legs, new_msg.verification_link(), rls).send()

                return jsonify({'status': 'successfully received postmark message'})
        else:
            return jsonify({'status': 'message already received'})
    except:
        print traceback.format_exc()
        return "Unable to parse postmark message.", 500
        # TODO send admin error message
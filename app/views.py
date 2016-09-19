from app import app, helpers
from app.forms import SignupForm, UnsubscribeForm
from flask import render_template, flash, redirect
import logging
import random
from twilio import TwilioRestException
#from misc.twilio_test import TwilioRestClient
from twilio.rest import TwilioRestClient


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    """
    Renders the backend of the index page and returns template
    """
    form = SignupForm()
    # If the form has been submitted
    if form.validate_on_submit():
        # Open db connection
        conn, cur = helpers.get_db_conn_and_cursor(app.config)

        # If all data is valid
        phone = helpers.is_valid_number(form.phone.data)
        if phone:
            # If phone number does not already exist as a verified user
            cur.execute('SELECT * FROM verified WHERE phone=%s;', [phone])
            if not cur.fetchone():
                logging.info({'func': 'index', 'fname': form.fname.data ,
                              'lname': form.lname.data, 'phone': phone,
                              'msg': 'user signup'})
                # If phone number does not already exist as an unverified user
                cur.execute("SELECT * FROM unverified WHERE phone=%s;", [phone])
                if not cur.fetchone():
                    # Add user to unverified signups table
                    confcode = random.getrandbits(128)
                    flashmsg = helpers.sign_up_user(cur, phone,
                                                    form.lname.data.upper(),
                                                    form.fname.data.upper(),
                                                    confcode)

                    # Send Text Message via Twilio
                    smstxt = "Welcome to VT-3 Notifications. Please click the link to confirm your registration. %s%s%d" \
                             % (app.config['BASE_URL'], '/verify/', confcode)
                    account_sid = app.config['TWILIO_ACCOUNT_SID']
                    auth_token = app.config['TWILIO_AUTH_TOKEN']
                    client = TwilioRestClient(account_sid, auth_token)
                    try:
                        message = client.messages.create(body=smstxt, to=phone,
                                                         from_='+17089288210')
                    except TwilioRestException as e:
                        print(e)

                # TODO Should I resend a new confirmation code here?
                else:
                    flashmsg = 'This phone number has already signed up but has not been verified. Please check your phone for your confirmation code.'
            else:
                flashmsg = 'This phone number has already been signed up.'

            flash(flashmsg)

        else:
            flash('Invalid phone number. Please try again.')
            form.phone.errors.append("Invalid format.")

        conn.commit()
        cur.close()
        conn.close()

        return redirect('/')

    return render_template("index.html", form=form)


@app.route('/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
    """
    Process a request to unsubscribe and return the template
    """
    form = UnsubscribeForm()
    # If the form has been submitted
    if form.validate_on_submit():
        # Open db connection
        conn, cur = helpers.get_db_conn_and_cursor(app.config)

        # If all data is valid
        phone = helpers.is_valid_number(form.phone.data)
        print(phone)
        if phone:
            # If phone number does not already exist as a verified user
            cur.execute('SELECT * FROM verified WHERE phone=%s AND fname=%s and lname=%s;',
                        [phone, form.fname.data.upper(), form.lname.data.upper()])
            if cur.fetchone():
                # Process unsubscribe request
                confcode = random.getrandbits(128)
                flashmsg = helpers.unsubscribe_user(cur, phone, confcode)
                smstxt = "Unsubscribe request received. Please click the link to verify. %s%s%d" \
                         % (app.config['BASE_URL'], '/unsubscribe/', confcode)
                # Send Text Message via Twilio
                account_sid = app.config['TWILIO_ACCOUNT_SID']
                auth_token = app.config['TWILIO_AUTH_TOKEN']
                client = TwilioRestClient(account_sid, auth_token)
                try:
                    message = client.messages.create(body=smstxt, to=phone,
                                                     from_='+17089288210')
                except TwilioRestException as e:
                    print(e)

                #flash(flashmsg)
                #return redirect('/')
            else:
                # Alert user this was an invalid unsubscribe request
                flashmsg = 'Data does not match anyone in our database. Please confirm name spelling and phone number.'

        else:
            flashmsg = 'Invalid phone number. Please try again.'
            form.phone.errors.append("Invalid format.")

        flash(flashmsg)
        conn.commit()
        print('committing')
        cur.close()
        conn.close()

    return render_template("unsubscribe.html", form=form)

@app.route('/unsubscribe/<confcode>')
def verify_unsubscribe(confcode):
    logging.debug({'func': 'verify_unsubscribe', 'confcode': confcode})

    conn, cur = helpers.get_db_conn_and_cursor(app.config)

    cur.execute("SELECT (phone) FROM unsubscribe WHERE confcode=%s", [confcode])
    d = cur.fetchone()
    if d:
        cur.execute('DELETE FROM verified WHERE phone=%s', [d[0]])
        cur.execute('DELETE FROM unsubscribe WHERE phone=%s', [d[0]])
        conn.commit()
        logging.info({'func': 'verify_unsubscribe', 'phone': d[0],
                      'msg': 'successfully unsubscribed'})
        msg = "You have been successfully unsubscribed."
    else:
        logging.info({'func': 'verify_unsubscribe', 'confcode': confcode,
                      'msg': 'invalid unsubscribe code'})
        msg = "ERROR: The supplied confirmation code is not valid."

    cur.close()
    conn.close()

    return render_template("unsubscribe.html", form=UnsubscribeForm(), msg=msg)

@app.route('/verify/<confcode>')
def verify(confcode):
    logging.debug({'func': 'verify', 'confcode': confcode})
    conn, cur = helpers.get_db_conn_and_cursor(app.config)

    cur.execute(
        "SELECT (phone, lname, fname) FROM unverified WHERE confcode=%s",
        [confcode])
    d = cur.fetchone()
    if d:
        d = d[0].lstrip('(').rstrip(')').split(',')
        cur.execute(
            'INSERT INTO verified (phone, lname, fname) VALUES (%s, %s, %s)',
            [d[0], d[1], d[2]])
        cur.execute("DELETE FROM unverified WHERE confcode=%s", [confcode])

        # TODO Make an initial push message when confirmed (e.g. what if they
        # sign up at night and need tomorrows schedule)
        msg = "Congratulations! You have successfully been signed up. You " \
              "will begin receiving messages at the next run."
        helpers.welcome_message(d[0], ', '.join((d[1], d[2])))
        logging.info({'func': 'verify', 'fname':d[2], 'lname': d[1],
                      'phone': d[0], 'msg': 'signup confirmation successful'})

    else:
        logging.info({'func': 'verify', 'confcode': confcode,
                       'msg': 'invalide confirmation code'})
        msg = "ERROR: The supplied confirmation code is not valid."

    conn.commit()
    cur.close()
    conn.close()

    return render_template("verify.html", msg=msg)

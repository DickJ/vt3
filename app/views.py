import random
from flask import render_template, flash, redirect
from twilio import TwilioRestException
from app import app, helpers
from app.forms import SignupForm
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
                    smstxt = "Welcome to VT-3 Notifications. Please click the link to confirm your registration. http://127.0.0.1:5000/verify/%d" \
                             % confcode
                    client = TwilioRestClient(
                        account_sid=app.config['TWILIO_ACCOUNT_SID'],
                        auth_token=app.config['TWILIO_AUTH_TOKEN'])
                    try:
                        message = client.messages.create(body=smstxt, to=phone,
                                                         from_='+17085555555')
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

        return redirect('/index')

    return render_template("index.html", form=form)


@app.route('/unsubscribe')
def unsubscribe():
    return render_template("unsubscribe.html")


@app.route('/verify/<confcode>')
def verify(confcode):
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
    else:
        msg = "ERROR: The supplied confirmation code is not valid."

    conn.commit()
    cur.close()
    conn.close()

    return render_template("verify.html", msg=msg)

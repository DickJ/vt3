from app import app
from app.forms import SignupForm
from flask import render_template, flash, redirect, session
import psycopg2
import random
import re

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    '''
    Index page
    '''

    form = SignupForm()
    if form.validate_on_submit():
        # Open db connection
        conn = psycopg2.connect(
            database=app.config['PG_URL'].path[1:],
            user=app.config['PG_URL'].username,
            password=app.config['PG_URL'].password,
            host=app.config['PG_URL'].hostname,
            port=app.config['PG_URL'].port
        )
        cur = conn.cursor()

        # If all data is valid
        regex = re.match('.*(\d{3}).*(\d{3}).*(\d{4})', form.phone.data)
        if regex:
            phone = regex.group(1) + regex.group(2) + regex.group(3)

            # If phone number does not already exist
            cur.execute("SELECT * FROM verified WHERE phone = %s;", [phone])
            if not cur.fetchone():
                cur.execute("SELECT * FROM unverified WHERE phone = %s;", [phone])
                if not cur.fetchone():
                    confcode = random.getrandbits(128)
                    cur.execute(
                        "INSERT INTO unverified (phone, lname, fname, confcode) VALUES (%s, %s, %s, %s);",
                        [form.phone.data, form.lname.data.upper(),
                         form.fname.data.upper(), confcode]
                    )
                    msg = 'Signup requested for %s. You should receive a text' \
                        ' message shortly' % (form.phone.data)

                    #TODO TWILIO CODE HERE
                    #######################
                    print("Welcome to VT-3 Notifications. Please click the" \
                          " link to confirm your registration. http://127.0.0.1:5000/verify/%s" % (str(confcode)))
                    #######################

                # Should I resend a new confirmation code here?
                else:
                    msg = 'This phone number has already signed up but has' \
                    ' not been verified yet. Check your phone for your ' \
                    'confirmation code.'
            else:
                msg = 'This phone number has already been signed up.'

            flash(msg)

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
    conn = psycopg2.connect(
        database=app.config['PG_URL'].path[1:],
        user=app.config['PG_URL'].username,
        password=app.config['PG_URL'].password,
        host=app.config['PG_URL'].hostname,
        port=app.config['PG_URL'].port
    )
    cur = conn.cursor()

    cur.execute("SELECT (phone, lname, fname) FROM unverified where confcode = %s", [confcode])
    d = cur.fetchone()
    if d:
        d = d[0].lstrip('(').rstrip(')').split(',')
        cur.execute("INSERT INTO verified (phone, lname, fname) VALUES (%s, %s, %s)",
                    [d[0], d[1], d[2]])
        cur.execute("DELETE FROM unverified WHERE confcode = %s", [confcode])
        conn.commit()

        # TODO Make an initial push message when confirmed (e.g. what if they
        # sign up at night and need tomorrows schedule)
        msg = "Congratulations! You have successfully been signed up. You " \
            "will begin receiving messages at the next run."
    else:
        msg = "ERROR: The supplied confirmation code is not valid."

    cur.close()
    conn.close()

    return render_template("verify.html", msg = msg)
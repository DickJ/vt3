from app import app, helpers
from app.forms import SignupForm, UnsubscribeForm, BugReportForm, HolidayPartyTickets, DuesForm, MugsForm, DiningInForm
from classes.TextClient import TextClient
from flask import render_template, flash, redirect
import logging
import os
import random
import sendgrid
from sendgrid.helpers.mail import *
import stripe


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
                              'provider': form.provider.data,
                              'msg': 'user signup'})
                # If phone number does not already exist as an unverified user
                cur.execute("SELECT * FROM unverified WHERE phone=%s;", [phone])
                if not cur.fetchone():
                    # Add user to unverified signups table
                    confcode = random.getrandbits(16)
                    flashmsg = helpers.sign_up_user(cur, phone,
                                                    form.provider.data,
                                                    form.lname.data.upper(),
                                                    form.fname.data.upper(),
                                                    confcode)

                    # Send Text Message via SendBox
                    subject = 'VT-3 Notifications'
                    smstxt = "Click the link to confirm. %s%s%d" \
                             % (app.config['BASE_URL'], '/verify/', confcode)
                    client = TextClient(debug=app.config['DEBUG'])
                    response = client.send_message(phone, form.provider.data,
                                                  subject, smstxt)


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


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/bugs', methods=['GET', 'POST'])
def bug_report():
    form = BugReportForm()

    if form.validate_on_submit():
        sg = sendgrid.SendGridAPIClient(apikey=app.config['SENDGRID_API_KEY'])
        to_email = sendgrid.helpers.mail.Email(app.config['BUG_REPORTING_EMAIL'])
        from_email = sendgrid.helpers.mail.Email('BugReport@vt3notifications.com')
        subject = form.subject.data
        if not form.name.data:
            form.name.data = 'anonymous'
        if not form.email.data:
            form.email.data = 'anon@ymou.se'
        message = sendgrid.helpers.mail.Content("text/plain",
                        ('%s (%s) \n\n %s' % (form.name.data, form.email.data,
                                              form.message.data)))
        mail = sendgrid.helpers.mail.Mail(from_email, subject, to_email, message)
        response = sg.client.mail.send.post(request_body=mail.get())
        logging.debug(response)
        flash("Your bug report has been submitted. Thank you.")
        return redirect('/bugs')

    return render_template('bugs.html', form=form)


@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')


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
            cur.execute('SELECT provider FROM verified WHERE phone=%s AND fname=%s and lname=%s;',
                        [phone, form.fname.data.upper(), form.lname.data.upper()])
            user = cur.fetchone()
            if user:
                # Process unsubscribe request
                confcode = random.getrandbits(16)
                flashmsg = helpers.unsubscribe_user(cur, phone, confcode)
                subject = 'VT-3 Notifications'
                smstxt = "Click the link to unsubscribe. %s%s%d" \
                         % (app.config['BASE_URL'], '/unsubscribe/', confcode)
                # Send Text Message
                tc = TextClient(debug=app.config['DEBUG'])
                response = tc.send_message(phone, user[0], subject, smstxt)

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
        "SELECT (phone, lname, fname, provider) FROM unverified WHERE confcode=%s",
        [confcode])
    d = cur.fetchone()
    if d:
        #TODO Why am I stripping and splitting? cur.fetchone returns a tuple,
        # not a string. ref: http://initd.org/psycopg/docs/cursor.html#fetch
        d = d[0].lstrip('(').rstrip(')').split(',')

        cur.execute("SELECT phone FROM verified WHERE phone = %s", [d[0]])
        already_added = cur.fetchone()
        if not already_added:
            cur.execute(
                'INSERT INTO verified (phone, lname, fname, provider) VALUES (%s, %s, %s, %s)',
                [d[0], d[1], d[2], d[3]])

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

#TODO Remove all payment code
# @app.route('/holiday', methods=['GET', 'POST'])
# def holiday_party():
#     form = HolidayPartyTickets()
#
#     if form.validate_on_submit():
#         # Set your secret key: remember to change this to your live secret key in production
#         # See your keys here: https://dashboard.stripe.com/account/apikeys
#         stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
#
#         # Get the credit card details submitted by the form
#         token = form.stripeToken.data
#
#         if form.category.data == 'mil':
#             price_per_ticket = 2500
#         elif form.category.data == 'civ':
#             price_per_ticket = 1500
#
#         cost = int(price_per_ticket * int(form.tickets.data))
#         cost = cost + 30 # $0.30 per transaction
#
#         price = int(cost / .971)
#
#         print("name: " + form.name.data)
#         print("email: " + form.email.data)
#         print("tickets: " + form.tickets.data)
#         print("category: " + form.category.data)
#         print("token: " + form.stripeToken.data)
#         print("price: " + str(price))
#
#         # Create a charge: this will charge the user's card
#         try:
#             charge = stripe.Charge.create(
#                 amount=price,  # Amount in cents
#                 currency="usd",
#                 source=token,
#                 description="%s %s tickets for %s" % (form.tickets.data, form.category.data, form.name.data)
#             )
#
#             sg = sendgrid.SendGridAPIClient(
#                 apikey=os.environ.get('SENDGRID_API_KEY'))
#             from_email = Email(os.environ.get('BUG_REPORTING_EMAIL'))
#             to_email = Email(form.email.data)
#             subject = "2016 VT-3 Holiday Party Ticket Purchase Confirmation"
#             msg = "Thank you for purchasing your holiday party tickets. Please " \
#                   "retain this email for your records.\n" \
#                   "Name: %s\nTickets Purchased: %s\nTotal Cost: $%.2f\n" % \
#                   (form.name.data, form.tickets.data, float(price / 100))
#             content = Content("text/plain", msg)
#             mail = Mail(from_email, subject, to_email,
#                         content)  # Send as receipt
#             response1 = sg.client.mail.send.post(request_body=mail.get())
#             mail = Mail(from_email, subject, from_email, content)  # Send to me
#             response2 = sg.client.mail.send.post(request_body=mail.get())
#
#             flash('Payment successful, you will receive a confirmation email shortly.')
#
#
#         except stripe.error.CardError as e:
#             flash("Payment has been declined")
#             pass
#
#     return render_template('holiday.html', form=form)


# @app.route('/dues', methods=['GET', 'POST'])
# def pay_dues():
#     form = DuesForm()
#
#     if form.validate_on_submit():
#         stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
#         token = form.stripeToken.data
#         amount = form.amount.data
#         desc = {'15479': 'Landing Fees',
#                 '3120': '3 Month Mess Dues',
#                 '6210': '6 Month Mess Dues',
#                 '9300': '9 Month Mess Dues',
#                 '12389': '12 Month Mess Dues',
#                 '5141': 'Dining In Ticket'}
#
#         try:
#             charge = stripe.Charge.create(
#                 amount=int(amount),
#                 currency='usd',
#                 source=token,
#                 description = desc[amount]
#             )
#
#             flash('Payment successful, you will receive a confirmation email shortly.')
#         except stripe.error.CardError as e:
#             flash("Payment has been declined")
#             pass
#
#     return render_template('dues.html', form=form)


# @app.route('/mugs', methods=['GET', 'POST'])
# def mugs():
#     form = MugsForm()
#
#     if form.validate_on_submit():
#         stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
#         token = form.stripeToken.data
#
#         price = int(float(form.amount.data) * 100)
#
#         print("name: " + form.name.data)
#         print("email: " + form.email.data)
#         print("callsign: " + form.callsign.data)
#         print("mug_qty: " + form.mug_qty.data)
#         print("stein_qty: " + form.stein_qty.data)
#         print("branch of service: " + form.branchofservice.data)
#         print("amount: " + form.amount.data)
#
#         try:
#             charge = stripe.Charge.create(
#                 amount=price,  # Amount in cents
#                 currency="usd",
#                 source=token,
#                 description="%s mug(s)/%s stein(s) for %s" % (
#                 form.mug_qty.data, form.stein_qty.data, form.name.data)
#             )
#
#             sg = sendgrid.SendGridAPIClient(
#                 apikey=os.environ.get('SENDGRID_API_KEY'))
#             from_email = Email(os.environ.get('BUG_REPORTING_EMAIL'))
#             to_email = Email(form.email.data)
#             subject = "2017 VT-3 Mugs and Steins Order"
#             msg = "Thank you for purchasing your Mug(s)/Stein(s). Please " \
#                   "retain this email for your records.\n" \
#                   "Name: %s\nName on Glassware: %s\nMugs Purchased: %s\nSteins Purchased: %s\nTotal Cost: $%.2f\n" % \
#                   (form.name.data, form.callsign.data, form.mug_qty.data, form.stein_qty.data, float(form.amount.data))
#             content = Content("text/plain", msg)
#             mail = Mail(from_email, subject, to_email,
#                         content)  # Send as receipt
#             response1 = sg.client.mail.send.post(request_body=mail.get())
#             mail = Mail(from_email, subject, from_email, content)  # Send to me
#             response2 = sg.client.mail.send.post(request_body=mail.get())
#
#             flash(
#                 'Payment successful, you will receive a confirmation email shortly.')
#
#         except stripe.error.CardError as e:
#             flash("Payment has been declined")
#             pass
#
#     return render_template('mugs.html', form=MugsForm(), stripe_pk=os.environ.get('STRIPE_PUB_KEY'))

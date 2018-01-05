import logging
import random
import re

from flask import flash

from app import app
from utils import u_db
from .TextClient import TextClient


def run_signup_form(form):
    # Open db connection
    conn, cur = u_db.get_db_conn_and_cursor(app.config)

    # FIXME: What do we do if user selects invalid phone provider?
    # FIXME: How will this fix play into the eventual switch to TWILIO?
    # If all data is valid
    phone = is_valid_number(form.phone.data)
    if phone:
        # If phone number does not already exist as a verified user
        cur.execute('SELECT * FROM verified WHERE phone=%s;', [phone])
        if not cur.fetchone():
            logging.info({'func': 'run_signup_form', 'fname': form.fname.data,
                          'lname': form.lname.data, 'phone': phone,
                          'provider': form.provider.data,
                          'msg': 'user signup'})
            # If phone number does not already exist as an unverified user
            cur.execute('SELECT confcode FROM unverified WHERE phone=%s;', [phone])
            unverified_user = cur.fetchone()
            if not unverified_user:
                #  Add user to unverified signups table
                flashmsg = sign_up_user(cur, conn, phone, form.provider.data,
                                        form.lname.data.upper().rstrip(),
                                        form.fname.data.upper().rstrip())

            else:
                confcode = int(unverified_user[0])
                send_conf_code(phone, form.provider.data,
                               'VT-3 Notifications Signup', confcode)
                flashmsg = 'This phone number has already signed up but has not been verified. We have re-sent your confirmation code.'
        else:
            flashmsg = 'This phone number has already been signed up.'

        flash(flashmsg)

    else:
        flash('Invalid phone number. Please try again.')
        form.phone.errors.append("Invalid format.")

    cur.close()
    conn.close()


def is_valid_number(number):
    """
    Determines if a given phone number is valid or not

    This function takes a phone number as a string and queries the Twilio API
    to determine if the phone number is a valid phone number. If so, it returns
    the phone number in E.164 format.

    Args:
        number: (str) a phone number as submitted by a user from a web form

    Returns:
        Either a string containing the phone number converted to E.164, or False
        if the phone number is determined to be invalid by the Twilio API

    """

    '''
    client = TwilioLookupsClient()
    try:
        response = client.phone_numbers.get(number, include_carrier_info=True)
        response.phone_number  # If invalid, throws an exception.
        return response.phone_number
    except TwilioRestException as e:
        if e.code == 20404:
            return False
        else:
            raise e
    '''

    if re.match('\d{9}', number):
        return "+1" + number
    else:
        return False


def sign_up_user(cur, conn, phone, provider, lname, fname):
    """
    Adds a user to the unverified users table

    Params:
        cur: (psycopg2.extensions.cursor) A cursor to the database
        conn: (psycopg2.extensions.connection) A connecton to the database
        phone: (str) phone number in E.164 format
        provider: (str) a wireless provider
        lname: (str) user's last name
        fname: (str) user's first name

    Returns
        (str) a response message to the user to be flashed on the webpage
    """
    assert re.match('^\+1\d{10}$', phone), "Invalid phone number format: %r" % phone
    assert type(fname == str), 'Invalid data type for first name: %r' % type(fname)
    assert type(lname == str), 'Invalid data type for last name: %r' % type(lname)
    assert fname != '', 'Last name is blank.'
    assert lname != '', 'First name is blank.'

    confcode = random.getrandbits(16)

    cur.execute(
        "INSERT INTO unverified (phone, provider, lname, fname, confcode, datetime) VALUES (%s, %s, %s, %s, %s, current_timestamp);",
        [phone, provider, lname, fname, confcode]
    )

    send_conf_code(phone, provider, 'VT-3 Notifications Signup', confcode)

    conn.commit()

    return 'Signup requested for %s. You should receive a text message shortly' % phone


def send_conf_code(phone, provider, subject, confcode):
    """
    Send a confirmation code to the user.

    #TODO In the future, this code could probably be changed so that it can be
    # the function used by worker to send out the schedule as well. This would
    # make converting to Twilio down the road easier, as there will only be one
    # function to change.

    :param phone: (str) phone number in E.164 format
    :param provider: (str) a wireless provider
    :param subject: (str) message subject (basically subscribe or unsubscribe)
    :param confcode: 16 bit confirmation code
    :return: the sendgrid response
    """
    smstxt = 'Click the link to confirm %s%s%d' \
             % (app.config['BASE_URL'], '/verify/', confcode)
    client = TextClient(debug=app.config['DEBUG'])
    return client.send_message(phone, subject, smstxt, provider)


def unsubscribe_user(cur, phone, confcode):
    """
    Adds a user to the unsubscribe table

    Params:
        cur: (psycopg2.extensions.cursor) A Cursor to the database
        phone: (str) phone number in E.164 format
        confcode: (int) randome 128-bit code

    Returns:
        (str) a response message to the user to be flashed on the webpage
    """
    assert re.match('\+\d{9}', phone), "Invalid phone number format: %r" % phone
    assert type(confcode) == int, "Invalid confirmation code: %r" % confcode
    print((phone, confcode))
    cur.execute("INSERT INTO unsubscribe (phone, confcode) VALUES (%s, %s);", [phone, confcode])

    return 'Unsubscribe requested for %s. You should receive a text message shortly to confirm unsubscribe' % (phone)

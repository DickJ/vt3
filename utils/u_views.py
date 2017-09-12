import logging
import random
import re

import psycopg2
from flask import flash

from app import app
from utils import u_db
from utils.classes.TextClient import TextClient


def run_signup_form(form):
    # Open db connection
    conn, cur = u_db.get_db_conn_and_cursor(app.config)

    # If all data is valid
    phone = is_valid_number(form.phone.data)
    if phone:
        # If phone number does not already exist as a verified user
        cur.execute('SELECT * FROM verified WHERE phone=%s;', [phone])
        if not cur.fetchone():
            logging.info({'func': 'index', 'fname': form.fname.data,
                          'lname': form.lname.data, 'phone': phone,
                          'provider': form.provider.data,
                          'msg': 'user signup'})
            # If phone number does not already exist as an unverified user
            cur.execute("SELECT * FROM unverified WHERE phone=%s;", [phone])
            if not cur.fetchone():
                # Add user to unverified signups table
                confcode = random.getrandbits(16)
                flashmsg = sign_up_user(cur, phone, form.provider.data,
                                        form.lname.data.upper(),
                                        form.fname.data.upper(), confcode)

                # Send Text Message via SendBox
                subject = 'VT-3 Notifications'
                smstxt = 'Click the link to confirm. %s%s%d' \
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

    # TODO Should the commit be moved into helpers.sign_up_user()?
    # -> would need to pass conn
    conn.commit()
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

def get_db_conn_and_cursor(config):
    """
    Obtains a connection and cursor object to the PostgresSQL database

    Args:
        config: (dict) Contains configuration variables

    Returns: psycopg2.extensions.connection, psycopg2.extensions.cursor
    """
    conn = psycopg2.connect(
        database=config['PG_URL'].path[1:],
        user=config['PG_URL'].username,
        password=config['PG_URL'].password,
        host=config['PG_URL'].hostname,
        port=config['PG_URL'].port
    )
    cur = conn.cursor()

    return conn, cur

def sign_up_user(cur, phone, provider, lname, fname, confcode):
    """
    Adds a user to the unverified users table

    Params:
        cur: (psycopg2.extensions.cursor) A cursor to the database
        phone: (str) phone number in E.164 format
        provider: (str) a wireless provider
        lname: (str) user's last name
        fname: (str) user's first name
        confcode: (str) random 6-digit code

    Returns
        (str) a response message to the user to be flashed on the webpage
    """
    assert re.match('\+\d{9}', phone), "Invalid phone number format: %r" % phone
    assert type(confcode) == str and len(confcode) == 6, "Invalid confirmation code: %r" % confcode
    assert type(fname == str), 'Invalid data type for first name: %r' % type(fname)
    assert type(lname == str), 'Invalid data type for last name: %r' % type(lname)
    assert fname != '', 'Last name is blank.'
    assert lname != '', 'First name is blank.'

    cur.execute(
        "INSERT INTO unverified (phone, provider, lname, fname, confcode, datetime) VALUES (%s, %s, %s, %s, %s, current_timestamp);",
        [phone, provider, lname, fname, confcode]
    )

    return 'Signup requested for %s. You should receive a text message shortly' % (phone)

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

def welcome_message(phone, name):
    """
    """
    pass

import psycopg2
import random
import re
from twilio.rest.lookups import TwilioLookupsClient
from twilio.rest.exceptions import TwilioRestException


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
        confcode: (int) random 128-bit code

    Returns
        (str) a response message to the user to be flashed on the webpage
    """
    assert re.match('\+\d{9}', phone), "Invalid phone number format: %r" % phone
    assert type(confcode) == int, "Invalid confirmation code: %r" % confcode
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

from bs4 import BeautifulSoup
from worker import helpers
from datetime import datetime, timedelta, time
import logging
import os
import re
from urllib import request, parse
import ssl
from twilio.rest import TwilioRestClient


def sched_uploaded(c, d):
    """
    Checks to see if the schedule has already been processed

    Params:
        c: (psycopg2.extensions.cursor)
        d: (datetime.datetime) containing the date we desire to check

    Returns:
        True if the date "dt" has already been processed, else returns False
    """
    c.execute("SELECT id FROM schedule WHERE date=%s", [d.strftime("%B %-d")])
    return bool(c.fetchone())

def get_schedule_page(url, dt):
    """
    """
    context = ssl._create_unverified_context()
    f = request.urlopen(url, context=context)
    soup = BeautifulSoup(f, "lxml")

    # Retrieve the page for the proper date
    calvar = soup.find("a", {"title": dt.strftime("%B %-d")}).get('href')
    et, ea = calvar.lstrip('javascript:__doPostBack(').rstrip(')').split(',')
    et = et.strip("'")
    ea = ea.strip("'")
    viewstate = soup.findAll("input", {"type": "hidden", "name": "__VIEWSTATE"})
    eventvalidation = soup.findAll("input", {"type": "hidden",
                                             "name": "__EVENTVALIDATION"})
    dateForm = {
        '__EVENTTARGET': et,
        '__EVENTARGUMENT': ea,
        '__EVENTVALIDATION': eventvalidation[0]['value'],
        '__VIEWSTATE': viewstate[0]['value'],
    }
    encodedDate = parse.urlencode(dateForm).encode('ascii')
    soup = BeautifulSoup(request.urlopen(url, encodedDate, context=context), "lxml")

    # Now that we have the proper date, retrieve the schedule
    viewstate = soup.findAll("input", {"type": "hidden", "name": "__VIEWSTATE"})
    eventvalidation = soup.findAll("input", {"type": "hidden",
                                             "name": "__EVENTVALIDATION"})
    formData = {
        '__EVENTVALIDATION': eventvalidation[0]['value'],
        '__VIEWSTATE': viewstate[0]['value'],
        'btnViewSched': 'View Schedule',
    }
    encodedFields = parse.urlencode(formData).encode('ascii')

    return BeautifulSoup(request.urlopen(
        url, encodedFields, context=context), 'lxml')


def process_raw_schedule(sp):
    #TODO verify columns in case of underlying page change
    daily_sched = []
    try:
        raw_data = sp.find("table", {'id': 'dgEvents'}).findAll('tr')
        # TYPE, VT, BRIEF, EDT, RTB, INSTRUCTOR, STUDENT, EVENT, HRS, REMARKS, LOCATION
        for row in raw_data[1:]:
            d = row.findAll('td')
            assert (
            len(d) == 11), "Error: There are not enough columns in the data"
            daily_sched.append({"type": d[0].text,
                                "vt": d[1].text,
                                "brief": d[2].text,
                                "edt": d[3].text,
                                "rtb": d[4].text,
                                "instructor": d[5].text,
                                "student": d[6].text,
                                "event": d[7].text,
                                "hrs": d[8].text,
                                "remarks": d[9].text,
                                "location": d[10].text
                                })
    except AttributeError:
        # Schedule not yet published
        pass
    return daily_sched


def insert_in_pg(cr, s, d):
    """
    Upload the daily schedule to the schedule table

    Params:
        cr: (psycopg2.extensions.cursor) Cursor to database
        s: (list of dicts) Daily schedule
        d: (datetime.datetime) Schedule date

    Returns: None
    """
    for row in s:
        cr.execute("INSERT INTO schedule (type, brief, edt, rtb, "
                    "instructor, student, event, remarks, location, date) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [row['type'],
                     row['brief'],
                     row['edt'],
                     row['rtb'],
                     row['instructor'],
                     row['student'],
                     row['event'],
                     row['remarks'],
                     row['location'],
                     d.strftime('%B %-d')])


def delete_old_sched(cur, dt):
    """
    Delete the schdule from the schedule table for the provided date

    Params:
        cur: (psycopg2.extensions.cursor) Database cursor
        dt: (datetime.datetime) date to be deleted

    Returns: None
    """
    cur.execute("DELETE FROM schedule WHERE date = %s",
                [dt.strftime('%B %-d')])


def send_all_texts(cur, dt):
    """
    Send out text messages to registered users

    Now here's some interesting stuff. Should we pass the schedule as a dict, or
    make all queries from Postgres? This app isn't going to be so big that I
    need to worry about the size of the schedule. Nor do we need it to run so
    quickly that I should worry about all the calls to Postgres. This function
    can actually run very lazily and it won't make a difference.

    Consider running a join to elminiate multiple calls to Postgres
    """
    client = TwilioRestClient(os.environ["TWILIO_ACCOUNT_SID"],
                              os.environ["TWILIO_AUTH_TOKEN"])

    cur.execute("SELECT lname, fname, phone FROM verified")
    all_users = [(str(x[0]+', '+x[1]), x[2]) for x in cur.fetchall()]

    for user in all_users:
        # Ugly SQL, but this just says "Find user's schedule for a date'
        cur.execute("SELECT * FROM schedule WHERE date=%s and (instructor LIKE %s or student LIKE %s);",
                    [dt.strftime("%B %-d"), ''.join(('%',user[0],'%')), ''.join(('%',user[0],'%'))])

        client.messages.create(body=generate_message(user, cur.fetchall()),
                               to=user[1], from_='+17089288210')


def generate_message(user, data):
    """

    Params:
        user: (str) user's name as it appears on the schedule
        data: (list of tuples) (id, type, brief, edt, rtb, instructor, student,
              event, remarks, location, date)

    Returns:
        A str containing the body of the text message to be sent.
    """
    type_of_day = tuple([d[1] for d in data])
    msg = '%s: ' % data[0][10]

    if len(type_of_day) == 0:
        msg = "You are not scheduled for anything on %s" % data[0][10]
    else:
        datadict = []
        for d in data:
            datadict.append({'type': d[1], 'brief': d[2], 'edt': d[3],
                             'rtb': d[4], 'instructor': d[5], 'student': d[6],
                             'event': d[7], 'remarks': d[8], 'location': d[9],
                             'date': d[10]})

        for event in datadict:
            msg = ''.join((msg, '%s, ' % (event['event'])))
            if event['brief'] != u'\xa0':
                msg = ''.join((msg, '%s, ' % event['brief']))
            elif event['edt'] != u'\xa0':
                msg = ''.join((msg, '%s, ' % event['edt']))
            else:
                # TODO Raise or Report an error
                pass

            if event['instructor'] != u'\xa0' and event['student'] != u'\xa0':
                msg = ''.join((msg, '%s/%s' % (event['instructor'], event['student'])))
            elif event['instructor'] != u'\xa0':
                msg = ''.join((msg, '%s' % (event['instructor'])))
            elif event['student'] != u'\xa0':
                msg = ''.join((msg, '%s' % (event['student'])))
            else:
                #TODO Raise or report an error
                pass

            if event['remarks'] != u'\xa0':
                msg = ''.join((msg, ', %s' % event['remarks']))

            if event['location'] != u'\xa0':
                msg = ''.join((msg, ', %s' % event['location']))

            msg = ''.join((msg, '; '))
        msg = msg.rstrip('; ') # Remove '; ' from end of message

    return msg


if __name__ == '__main__':
    print("Starting Worker")
    # Define Vars
    conn, cur = helpers.get_db_conn_and_cursor()
    url = 'https://www.cnatra.navy.mil/scheds/schedule_data.aspx?sq=vt-3'
    tomorrow = datetime.now() - timedelta(hours=5) + timedelta(days=1) # adjust timezone

    if tomorrow.weekday() == 5: # If it is Friday and we're looking for Sat's sched
        dates = (tomorrow, tomorrow+timedelta(days=1), tomorrow+timedelta(days=2))
    else:
        dates = (tomorrow, )

    for dt in dates:
        print("Checking schedule for %r" % tomorrow)

        # Download Schedule
        try:
            sched = process_raw_schedule(get_schedule_page(url, dt))

            # If schedule has been posted on cnatra or uploaded to postgress yet
            if sched and not sched_uploaded(cur, dt):
                #TODO What we insert will change over weekends
                insert_in_pg(cur, sched, dt)
                if dt.weekday() == 0:
                    delete_old_sched(cur, dt - timedelta(days=2))
                    delete_old_sched(cur, dt - timedelta(days=3))
                    delete_old_sched(cur, dt - timedelta(days=4))
                elif dt.weekday not in (6, 0):
                    delete_old_sched(cur, dt - timedelta(days=2))
                conn.commit()
                send_all_texts(cur, dt)
            # If it gets too late and the schedule hasn't been published, send out
            # a text. But only do this once, so let's use 1930L == 0030UTC
            # TODO: What about when DST ends?
            elif not sched and time(0, 29, 0) < datetime.now().time() < time(0, 59, 0):
                client =  TwilioRestClient(os.environ["TWILIO_ACCOUNT_SID"],
                                           os.environ["TWILIO_AUTH_TOKEN"])

                cur.execute("SELECT phone FROM verified;")
                msg = "The schedule has not been published yet. Please call the " \
                      "SDO at (850)623-7323 for tomorrow's schedule."
                for phone in cur.fetchall():
                    client.messages.create(body=msg, to=phone, from_='+17089288210')

        except AttributeError as e:
            print(e)
            print("Schedule not yet published")

    cur.close()
    conn.close()

    print("Worker exiting")

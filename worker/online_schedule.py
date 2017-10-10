import logging
import re
import ssl
from datetime import datetime, timedelta, time
from urllib import request, parse

from bs4 import BeautifulSoup

from utils import u_db
from utils.TextClient import TextClient


def sched_uploaded(c, d):
    """
    Checks to see if the schedule has already been processed

    Params:
        c: (psycopg2.extensions.cursor)
        d: (datetime.datetime) containing the date we desire to check

    Returns:
        True if the date "dt" has already been processed, else returns False
    """
    logging.info({'func': 'sched_uploaded',
                  'msg': 'Checking if schedule has been processed'})
    c.execute("SELECT id FROM schedule WHERE date=%s", [d.strftime("%B %-d")])
    return bool(c.fetchone())


def get_schedule_page(url, dt):
    """
    """
    logging.debug({'func': 'get_schedule_page', 'url': url, 'dt': dt})
    logging.info({'func': 'get_schedule_page', 'msg': 'Downloading Page'})
    context = ssl._create_unverified_context()
    f = request.urlopen(url, context=context)
    soup = BeautifulSoup(f, "lxml")

    # Retrieve the page for the proper date
    logging.info({'func': 'get_schedule_page', 'msg': 'Opening correct date'})
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
    soup = BeautifulSoup(request.urlopen(url, encodedDate, context=context),
                         "lxml")

    # Now that we have the proper date, retrieve the schedule
    logging.info({'func': 'get_schedule_page', 'msg': 'Downloading schedule'})
    viewstate = soup.findAll("input", {"type": "hidden", "name": "__VIEWSTATE"})
    eventvalidation = soup.findAll("input", {"type": "hidden",
                                             "name": "__EVENTVALIDATION"})
    formData = {
        '__EVENTVALIDATION': eventvalidation[0]['value'],
        '__VIEWSTATE': viewstate[0]['value'],
        'btnViewSched': 'View Schedule',
    }
    encodedFields = parse.urlencode(formData).encode('ascii')

    return BeautifulSoup(request.urlopen(url, encodedFields,
                                         context=context), 'lxml')


def process_raw_schedule(sp):
    """
    Convert the daily schedule from bs4 to a list of dicts

    Params:
        sp: (BeautifulSoup) bs4 containing the daily schedule

    Returns:
        the daily schedule processed into a list of dicts
    """
    # TODO verify columns in case of underlying page change
    logging.debug({'func': 'process_raw_schedule'})
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
        logging.info({'func': 'process_raw_schedule',
                      'msg': 'Schedule not yet published'})
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
    # TODO: This function should take the conn and commit() as well
    # TODO: Return something so we know we have successful execution
    logging.debug({'func': 'insert_ing_pg', 'cr': cr, 's': s, 'd': d})
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
    logging.debug({'func': 'delete_old_sched', 'cur': cur, 'dt': dt})
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
    logging.debug({'func': 'send_all_texts', 'dt': dt})

    client = TextClient()

    cur.execute("SELECT lname, fname, phone, provider FROM verified")
    all_users = [(str(x[0] + ', ' + x[1]), x[2], x[3]) for x in cur.fetchall()]

    for user in all_users:
        logging.info({'func': 'send_all_texts', 'user': user})
        # This just says "Find user's schedule for a date'
        cur.execute(
            "SELECT * FROM schedule WHERE date=%s AND (instructor LIKE %s OR student LIKE %s);",
            [dt.strftime("%B %-d"), ''.join(('%', user[0], '%')),
             ''.join(('%', user[0], '%'))])

        all_msg = generate_message(user, cur.fetchall(), dt.strftime('%B %-d'))
        for msg in all_msg:
            response = client.send_message(user[1], dt.strftime('%b %-d'), msg, user[2])

            
def generate_message(user, data, dt):
    """

    Params:
        user: (str) user's name as it appears on the schedule
        data: (list of tuples) (id, type, brief, edt, rtb, instructor, student,
              event, remarks, location, date)

    Returns:
        A str containing the body of the text message to be sent.
    """
    logging.info(
        {'func': 'generate_message', 'user': user, 'data': data, 'dt': dt})
    all_msg = []
    msg = ''
    type_of_day = tuple([d[1] for d in data])

    if len(type_of_day) == 0:
        all_msg.append("You are not scheduled for anything")
    else:
        for d in data:
            msg = ''.join((msg, '%s, ' % (d[7])))
            if d[2] != u'\xa0':
                msg = ''.join((msg, '%s, ' % d[2]))
            elif d[3] != u'\xa0':
                msg = ''.join((msg, '%s, ' % d[3]))
            else:
                # TODO Raise or Report an error
                pass

            if d[5] != u'\xa0' and d[6] != u'\xa0':
                msg = ''.join((msg, '%s/%s' % (d[5], d[6])))
            elif d[5] != u'\xa0':
                msg = ''.join((msg, '%s' % (d[5])))
            elif d[6] != u'\xa0':
                msg = ''.join((msg, '%s' % (d[6])))
            else:
                # TODO Raise or report an error
                pass

            if d[8] != u'\xa0':
                msg = ''.join((msg, ', %s' % d[8]))

            if d[9] != u'\xa0':
                msg = ''.join((msg, ', %s' % d[9]))

            logging.info(
                {'func': 'generate_message', 'user': user, 'msg': msg})

            all_msg.append(msg)
            msg = ''

    return all_msg


def send_squadron_notes(url, dt, cur):
    """
    """
    # TODO Return something! Anything!
    logging.debug({'func': 'get_schedule_page', 'url': url, 'dt': dt})
    logging.info({'func': 'get_schedule_page', 'msg': 'Downloading Page'})
    context = ssl._create_unverified_context()
    f = request.urlopen(url, context=context)
    soup = BeautifulSoup(f, "lxml")

    # Retrieve the page for the proper date
    logging.info({'func': 'get_schedule_page', 'msg': 'Opening correct date'})
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
    soup = BeautifulSoup(request.urlopen(url, encodedDate, context=context),
                         "lxml")

    # Now that we have the proper date, retrieve the schedule
    logging.info({'func': 'get_schedule_page', 'msg': 'Downloading schedule'})
    viewstate = soup.findAll("input", {"type": "hidden", "name": "__VIEWSTATE"})
    eventvalidation = soup.findAll("input", {"type": "hidden",
                                             "name": "__EVENTVALIDATION"})
    formData = {
        '__EVENTVALIDATION': eventvalidation[0]['value'],
        '__VIEWSTATE': viewstate[0]['value'],
        'btnViewSched': 'View Schedule',
    }
    encodedFields = parse.urlencode(formData).encode('ascii')
    notes_page_soup = BeautifulSoup(request.urlopen(
        url, encodedFields, context=context), 'lxml')

    tc = TextClient()
    notes = notes_page_soup.find(id='dgCoversheet')

    if notes:
        text = re.sub(u'\xa0', ' ', notes.text.strip())
        cur.execute("SELECT phone, provider FROM verified;")
        for phone, provider in cur.fetchall():
            tc.send_message(phone, dt.strftime('%B %-d'), text, provider)
    else:
        notes = notes_page_soup.find(id='lblNoCoversheet')

    if not notes:
        # TODO Can't get to this point with the if/else above.
        # TODO This should log, not print
        print("Neither squadron notes, nor no squadron notes message exist.")
        raise ValueError


def run_online_schedule():
    logging.basicConfig(level=logging.DEBUG)
    logging.info({'func': 'run_online_schedule',
                  'msg': "Starting run_online_schedule()"})
    # Define Vars
    conn, cur = u_db.get_db_conn_and_cursor()
    url = 'https://www.cnatra.navy.mil/scheds/schedule_data.aspx?sq=vt-3'
    tomorrow = datetime.now() - timedelta(hours=5) + timedelta(
        days=1)  # adjust timezone

    if tomorrow.weekday() == 5:  # If it is Friday and we're looking for Sat's sched
        dates = (
            tomorrow, tomorrow + timedelta(days=1),
            tomorrow + timedelta(days=2))
    else:
        dates = (tomorrow,)

    logging.info({'func': 'run_online_schedule', 'dates': dates,
                  'msg': 'Dates being processed by run_online_schedule()'})

    for dt in dates:
        logging.info(
            {'func': 'run_online_schedule',
             'msg': "Checking schedule for %r" % tomorrow})

        # Download Schedule
        try:
            sched = process_raw_schedule(get_schedule_page(url, dt))

            # If schedule has been posted on cnatra or uploaded to postgress yet
            if sched and not sched_uploaded(cur, dt):
                insert_in_pg(cur, sched, dt)
                if dt.weekday() == 1:
                    logging.debug({'func': 'run_online_schedule',
                                   'msg': 'Deleting last weeks schedule from database'})
                    delete_old_sched(cur, dt - timedelta(days=2))
                    delete_old_sched(cur, dt - timedelta(days=3))
                    delete_old_sched(cur, dt - timedelta(days=4))
                    delete_old_sched(cur, dt - timedelta(days=5))
                    delete_old_sched(cur, dt - timedelta(days=6))
                    delete_old_sched(cur, dt - timedelta(days=7))
                    delete_old_sched(cur, dt - timedelta(days=8))
                conn.commit()
                send_all_texts(cur, dt)
                send_squadron_notes(url, dt, cur)
            # If it gets too late and the schedule hasn't been published, send out
            # a text. But only do this once, so let's use 1930L == 0030UTC
            # TODO: What about when DST ends?
            elif not sched and time(0, 29, 0) < datetime.now().time() < time(0,
                                                                             59,
                                                                             0):
                logging.warning({'func': 'run_online_schedule',
                                 'msg': 'Schedule was not published by 0100Z'})
                # TODO Only instantiate one TextClient in main.py
                client = TextClient()

                cur.execute("SELECT phone, provider FROM verified;")
                msg = "The schedule has not been published yet. Please call the " \
                      "SDO at (850)623-7323 for tomorrow's schedule."
                for phone, provider in cur.fetchall():
                    client.send_message(phone, dt.strftime('%B %-d'), msg, provider)

        except AttributeError as e:
            logging.debug({'func': 'run_online_schedule', 'error': e})
            logging.info({'func': 'run_online_schedule',
                          'msg': "Schedule not yet published"})

    cur.close()
    conn.close()

    logging.info(
        {'func': 'run_online_schedule', 'msg': "run_online_schedule() exiting"})

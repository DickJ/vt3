from bs4 import BeautifulSoup
from worker import helpers
from datetime import date, timedelta
from urllib import request, parse
import ssl
from twilio.rest import TwilioRestClient


def sched_uploaded(c, d):
    """
    Checks to see if the schedule has already been processed

    Params:
        c: (psycopg2.extensions.cursor)
        d: (datetime.date) containing the date we desire to check

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
        d: (datetime.date) Schedule date

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
        dt: (datetime.date) date to be deleted

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
    account_sid = None
    auth_token = None
    client = TwilioRestClient(account_sid, auth_token)

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
    # TODO if len(users_schedule)==0; send a message that they're not scheduled
    # CAI, GRND SCH, Meetings, MIL, T-6B Flight, T-6B SIMs, Watch, Pre-Flight
    type_of_day = tuple([d[1] for d in data])
    partners = []
    for d in data:
        if d[5] == user:
            if d[6] == u'\xa0':
                partners.append('')
            else:
                partners.append(d[6])
        else:
            if d[5] == u'\xa0':
                partners.append('')
            else:
                partners.append(d[5])

    print(partners)
    print(type_of_day)

    if len(type_of_day) == 0:
        msg = "You are not scheduled for anything tomorrow"
    elif type_of_day == ('T-6B Flight', 'T-6B Flight'):
        msg = "You are scheduled for 2 flights tomorrow. Flight 1 is %s and briefs at %s with %s. Flight 2 is %s and briefs at %s with %s" % (data[0][7], data[0][2], partners[0], data[1][7], data[1][2], partners[1])
    elif type_of_day == ('T-6B SIMs',):
        msg = "You have a %s sim tomorrow. Brief time is %s with %s" % (data[0][7], data[0][2], partners[0])
    elif type_of_day == ('T-6B Flight'):
        msg = "You have a %s flight tomorrow. Brief time is %s with %s" % (d[0][7], d[0][2], partners[0])
    elif type_of_day == ('T-6B SIMs', 'T-6B SIMs'):
        msg = "You have 2 sims tomorrow. Sim 1 is %s with %s and briefs at %s. Sim 2 is %s with %s and briefs at %s."  % (data[0][7], partners[0], data[0][2], data[1][7], partners[1], data[1][2])
    elif type_of_day == ('Meetings',):
        msg = "You are scheduled for a meeting tomorrow at %s: %s" % (data[0][2], data[0][8])
    elif type_of_day == ('Meetings', 'Meetings'):
        msg = "You have two meetings tomorrow. (1) %s: %s and (2) %s: %s" % (data[0][2], data[0][8], data[1][2], data[1][8])
    elif type_of_day == ('Watch',):
        msg = "You are scheduled for watch tomorrow from %s to %s: %s" (data[0][3], data[0][4], data[0][7])
    elif type_of_day == ('GRND SCH', 'GRND SCH', 'GRND SCH', 'GRND SCH', 'GRND SCH'):
        msg = str(data)
    elif type_of_day == ('T-6B Flight', 'T-6B Flight', 'T-6B Flight'):
        msg = (data)
    elif type_of_day == ('GRND SCH', 'GRND SCH', 'GRND SCH', 'GRND SCH', 'GRND SCH', 'GRND SCH'):
        msg = (data)
    else:
        msg = str(data)
        #TODO Send alert email for unseen type of day

    return msg

if __name__ == '__main__':
    print("Starting Worker")
    # Define Vars
    conn, cur = helpers.get_db_conn_and_cursor()
    url = 'https://www.cnatra.navy.mil/scheds/schedule_data.aspx?sq=vt-3'
    dt = date.today() + timedelta(days=1)

    print("Current date: %r" % date.today())
    print("Checking schedule for %r" % dt)

    # Download Schedule
    try:
        sched = process_raw_schedule(get_schedule_page(url, dt))

        # If schedule has been posted on cnatra or uploaded to postgress yet
        if sched and not sched_uploaded(cur, dt):
            #TODO What we insert will change over weekends
            insert_in_pg(cur, sched, dt)
            #TODO delete old will change over weekends
            delete_old_sched(cur, dt - timedelta(days=2))
            conn.commit()
            send_all_texts(cur, dt)
            # Update schedule to not run until tomorrow
    except AttributeError as e:
        print(e)
        print("Schedule not yet published")
    finally:
        cur.close()
        conn.close()

        print("Worker exiting")

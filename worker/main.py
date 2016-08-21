from bs4 import BeautifulSoup
import urllib
import ssl


# url = 'https://www.cnatra.navy.mil/scheds/schedule_data.aspx?sq=vt-3'

def get_schedule_page(url):
    context = ssl._create_unverified_context()
    f = urllib.request.urlopen(url, context=context)
    soup = BeautifulSoup(f, "lxml")

    viewstate = soup.findAll("input", {"type": "hidden", "name": "__VIEWSTATE"})
    eventvalidation = soup.findAll("input", {"type": "hidden",
                                             "name": "__EVENTVALIDATION"})

    formData = {
        '__EVENTVALIDATION': eventvalidation[0]['value'],
        '__VIEWSTATE': viewstate[0]['value'],
        'btnViewSched': 'View Schedule',
    }
    encodedFields = urllib.parse.urlencode(formData).encode('ascii')

    return BeautifulSoup(urllib.request.urlopen(
        url, encodedFields, context=context))


def process_raw_schedule(sp):
    #TODO verify columns in case of underlying page change
    raw_data = sp.find("table", {'id': 'dgEvents'}).findAll('tr')
    # TYPE, VT, BRIEF, EDT, RTB, INSTRUCTOR, STUDENT, EVENT, HRS, REMARKS, LOCATION
    daily_sched = []
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
    return daily_sched

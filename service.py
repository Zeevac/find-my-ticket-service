import json
import re

import mechanize
import tzlocal
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup as bs
from firebase_admin import messaging

from exceptions import TableNotFoundException
from repository import Repository

base_url = "https://ebilet.tcddtasimacilik.gov.tr/view/eybis/tnmGenel/tcddWebContent.jsf"
device_token = "dhVbGt_uTVmywvmANiwi0d:APA91bF6Tg9TQKvjd-1dJlbKahxSgggdfs8KqJQo3LAw9f8i5w0VxN6okLIrQog_Xn01df4MKsPOMHrDmYTwKotoDxNy4sZA0lgnwFb4wGkC4MmRFQwfS2stIKuyEnXnem5gTInGsaoK"
browser = mechanize.Browser()
watching_sessions = {}
repository = Repository()

for item in repository.get_all():
    watching_sessions[item["date"]] = item["sessions"]

print(watching_sessions)
scheduler = BackgroundScheduler(timezone=str(tzlocal.get_localzone()))


def start():
    print("start called")
    scheduler.start()


def is_scheduler_running():
    return scheduler.running


def stop():
    print("stop called")
    if is_scheduler_running():
        scheduler.remove_all_jobs()


def add_job(outgoing_station, destination_station, departure_date):
    args = [outgoing_station, destination_station, departure_date]
    job = scheduler.add_job(scrap_ticket_information, 'interval', args, seconds=5)
    return job


def extract_empty_seats(text):
    return remove_parenthesis(text.split()[-1])


def remove_parenthesis(text):
    text = text.replace("(", "")
    text = text.replace(")", "")
    return text


def simulate_browser_form_submit(outgoing_station, destination_station, departure_date):
    browser.open(base_url)
    browser.select_form(nr=3)
    browser.form["nereden"] = outgoing_station
    browser.form["nereye"] = destination_station
    browser.form["trCalGid_input"] = departure_date
    return browser.submit()


def fetch_table_body(outgoing_station, destination_station, departure_date):
    form_response = simulate_browser_form_submit(outgoing_station, destination_station, departure_date)
    html = form_response.read().decode("utf-8")
    soup = bs(html, "html.parser")
    return soup.find("tbody", {"id": "mainTabView:gidisSeferTablosu_data"})


def fetch_table_body_with_retry(outgoing_station, destination_station, departure_date):
    table_body = fetch_table_body(outgoing_station, destination_station, departure_date)
    retry_counter = 0
    while type(table_body) == type(None) and retry_counter < 3:
        print("table_body is none. retrying...")
        table_body = fetch_table_body(outgoing_station, destination_station, departure_date)
        retry_counter += 1
    return table_body


def scrap_ticket_information(outgoing_station, destination_station, departure_date):
    print("scrap_ticket_information called")
    print(f"Len of watching_sessions: {str(len(watching_sessions))}, outgoing_station: {outgoing_station}, "
          f"destination_station: {destination_station}, departure_date: {departure_date}")
    print(watching_sessions)
    if departure_date not in watching_sessions or departure_date in watching_sessions and len(
            watching_sessions[departure_date]) == 0:
        stop()
        return
    table_body = fetch_table_body_with_retry(outgoing_station, destination_station, departure_date)
    head_ways = []
    trs = table_body.find_all("tr",
                              {"class": ["ui-widget-content ui-datatable-even",
                                         "ui-widget-content ui-datatable-odd"]})
    for tr in trs:
        departure_time = tr.find("span", {"class": "seferSorguTableBuyuk"}).text
        if not is_in_watching_session(departure_date, departure_time):
            continue
        duration = tr.find_all("label", {"class": "ui-outputlabel"})[1].text
        arrival_time = tr.find_all("span", {"class": "seferSorguTableBuyuk"})[1].text
        seat_li_elements = tr.find_all("li", text=re.compile("(Ekonomi)"))
        print(
            f"Current tr:\n\tdeparture_time: {departure_time}\n\tduration: {duration}\n\tarrival: {arrival_time}\n\tseat_li_elements: {len(seat_li_elements)}")
        if len(seat_li_elements) != 0:
            empty_seats = int(extract_empty_seats(seat_li_elements[0].text)) - 2
            if empty_seats < 0:
                empty_seats = 0
            if int(empty_seats) > 0:
                head_ways.append(
                    {"departure": departure_time, "arrival": arrival_time, "duration": duration,
                     "available_seats": str(empty_seats),
                     "is_watching": "true"})
                remove_watching_session_service(departure_date, departure_time)

    print(head_ways)
    if len(head_ways) > 0:
        send_to_device(head_ways)
        stop()


def is_in_watching_session(date, departure_time):
    return date in watching_sessions and departure_time in watching_sessions[date]


def add_to_watching_session_service(date, time):
    if date in watching_sessions:
        watching_sessions[date].append(time)
    else:
        watching_sessions[date] = []
        watching_sessions[date].append(time)
    repository.add(date, time)


def remove_watching_session_service(date, time):
    if date in watching_sessions and time in watching_sessions[date]:
        watching_sessions[date].remove(time)
        repository.remove(date, [time])


def get_sessions_service(outgoing_station, destination_station, departure_date):
    table_body = fetch_table_body_with_retry(outgoing_station, destination_station, departure_date)
    if type(table_body) == type(None):
        return TableNotFoundException()
    head_ways = []
    trs = table_body.find_all("tr",
                              {"class": ["ui-widget-content ui-datatable-even",
                                         "ui-widget-content ui-datatable-odd"]})
    for tr in trs:
        departure_time = tr.find("span", {"class": "seferSorguTableBuyuk"}).text
        duration = tr.find_all("label", {"class": "ui-outputlabel"})[1].text
        arrival_time = tr.find_all("span", {"class": "seferSorguTableBuyuk"})[1].text
        seat_li_elements = tr.find_all("li", text=re.compile("(Ekonomi)"))
        if len(seat_li_elements) != 0:
            empty_seats = int(extract_empty_seats(seat_li_elements[0].text)) - 2
            if empty_seats < 0:
                empty_seats = 0
            is_watching = "false"
            if departure_date in watching_sessions and departure_time in watching_sessions[departure_date]:
                is_watching = "true"
            head_ways.append(
                {"departure": departure_time, "arrival": arrival_time, "duration": duration,
                 "available_seats": str(empty_seats),
                 "is_watching": is_watching})
    return head_ways


def get_watching_sessions_service(date):
    if date in watching_sessions:
        return watching_sessions[date]
    return []


def send_to_device(sessions):
    message = messaging.Message(data={"sessions": json.dumps(sessions)}, token=device_token)
    response = messaging.send(message)
    print('Successfully sent message:', response)


def set_device_token(token):
    global device_token
    device_token = token


def get_current_token_service():
    return device_token

import json
import re

import mechanize
from bs4 import BeautifulSoup as bs
from firebase_admin import messaging

from repository import Repository

base_url = "https://ebilet.tcddtasimacilik.gov.tr/view/eybis/tnmGenel/tcddWebContent.jsf"
device_token = "dhVbGt_uTVmywvmANiwi0d:APA91bF6Tg9TQKvjd-1dJlbKahxSgggdfs8KqJQo3LAw9f8i5w0VxN6okLIrQog_Xn01df4MKsPOMHrDmYTwKotoDxNy4sZA0lgnwFb4wGkC4MmRFQwfS2stIKuyEnXnem5gTInGsaoK"
browser = mechanize.Browser()
watching_sessions = {}
repository = Repository()

for item in repository.get_all():
    watching_sessions[item["date"]] = item["sessions"]

print(watching_sessions)


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


def scrap_ticket_information(outgoing_station, destination_station, departure_date, watching_session):
    add_to_watching_session_service(watching_session)
    table_body = fetch_table_body_with_retry(outgoing_station, destination_station, departure_date)
    head_ways = []
    trs = table_body.find_all("tr",
                              {"class": ["ui-widget-content ui-datatable-even",
                                         "ui-widget-content ui-datatable-odd"]})
    for tr in trs:
        departure = tr.find("span", {"class": "seferSorguTableBuyuk"}).text
        if not is_in_watching_session(departure):
            continue
        duration = tr.find_all("label", {"class": "ui-outputlabel"})[1].text
        arrival = tr.find_all("span", {"class": "seferSorguTableBuyuk"})[1].text
        seat_li_elements = tr.find_all("li", text=re.compile("(Ekonomi)"))
        if len(seat_li_elements) != 0:
            empty_seats = extract_empty_seats(seat_li_elements[0].text)
            if int(empty_seats) > 2:
                head_ways.append(
                    {"departure": departure, "arrival": arrival, "duration": duration, "available_seats": empty_seats,
                     "is_watching": "true"})
    if len(head_ways) > 0:
        send_to_device(head_ways)


def is_in_watching_session(date, searching_session):
    for session in watching_sessions[date]:
        if session == searching_session:
            return True
    return False


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
    else:
        return ""
    repository.remove(date, [time])


def get_sessions_service(outgoing_station, destination_station, departure_date):
    table_body = fetch_table_body_with_retry(outgoing_station, destination_station, departure_date)
    head_ways = []
    trs = table_body.find_all("tr",
                              {"class": ["ui-widget-content ui-datatable-even",
                                         "ui-widget-content ui-datatable-odd"]})
    for tr in trs:
        departure = tr.find("span", {"class": "seferSorguTableBuyuk"}).text
        duration = tr.find_all("label", {"class": "ui-outputlabel"})[1].text
        arrival = tr.find_all("span", {"class": "seferSorguTableBuyuk"})[1].text
        seat_li_elements = tr.find_all("li", text=re.compile("(Ekonomi)"))
        if len(seat_li_elements) != 0:
            empty_seats = int(extract_empty_seats(seat_li_elements[0].text)) - 2
            if empty_seats < 0:
                empty_seats = 0
            is_watching = "false"
            if departure_date in watching_sessions and departure in watching_sessions[departure_date]:
                is_watching = "true"
            head_ways.append(
                {"departure": departure, "arrival": arrival, "duration": duration, "available_seats": str(empty_seats),
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

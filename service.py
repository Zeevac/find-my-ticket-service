import json
import re

import mechanize
from bs4 import BeautifulSoup as bs
from firebase_admin import messaging

base_url = "https://ebilet.tcddtasimacilik.gov.tr/view/eybis/tnmGenel/tcddWebContent.jsf"
device_token = "dhVbGt_uTVmywvmANiwi0d:APA91bF6Tg9TQKvjd-1dJlbKahxSgggdfs8KqJQo3LAw9f8i5w0VxN6okLIrQog_Xn01df4MKsPOMHrDmYTwKotoDxNy4sZA0lgnwFb4wGkC4MmRFQwfS2stIKuyEnXnem5gTInGsaoK"


def extract_empty_seats(text):
    return remove_parenthesis(text.split()[-1])


def remove_parenthesis(text):
    text = text.replace("(", "")
    text = text.replace(")", "")
    return text


def simulate_browser_form_submit(outgoing_station, destination_station, departure_date):
    browser = mechanize.Browser()
    browser.open(base_url)
    browser.select_form(nr=3)
    browser.form["nereden"] = outgoing_station
    browser.form["nereye"] = destination_station
    browser.form["trCalGid_input"] = departure_date
    return browser.submit()


def scrap_ticket_information(outgoing_station, destination_station, departure_date):
    form_response = simulate_browser_form_submit(outgoing_station, destination_station, departure_date)
    html = form_response.read().decode("utf-8")
    soup = bs(html, "html.parser")
    table_body = soup.find("tbody", {"id": "mainTabView:gidisSeferTablosu_data"})
    head_ways = []
    if type(table_body) != type(None):
        trs = table_body.find_all("tr",
                                  {"class": ["ui-widget-content ui-datatable-even",
                                             "ui-widget-content ui-datatable-odd"]})
        for tr in trs:
            departure = tr.find("span", {"class": "seferSorguTableBuyuk"}).text
            duration = tr.find_all("label", {"class": "ui-outputlabel"})[1].text
            arrival = tr.find_all("span", {"class": "seferSorguTableBuyuk"})[1].text
            seat_li_elements = tr.find_all("li", text=re.compile("(Ekonomi)"))
            if len(seat_li_elements) != 0:
                empty_seats = extract_empty_seats(seat_li_elements[0].text)
                head_ways.append(
                    {"departure": departure, "arrival": arrival, "duration": duration, "available_seats": empty_seats})
        send_to_device(head_ways)
    else:
        print("table_body is none")


def send_to_device(sessions):
    message = messaging.Message(data={"sessions": json.dumps(sessions)}, token=device_token)
    response = messaging.send(message)
    print('Successfully sent message:', response)


def set_device_token(token):
    global device_token
    device_token = token

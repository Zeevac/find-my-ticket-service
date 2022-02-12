import re

import mechanize
from bs4 import BeautifulSoup as bs
from flask import Flask, make_response, request
from flask import jsonify

base_url = "https://ebilet.tcddtasimacilik.gov.tr/view/eybis/tnmGenel/tcddWebContent.jsf"
app = Flask(__name__)


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


@app.post("/")
def index():
    outgoing_station = request.json["outgoing"]
    destination_station = request.json["destination"]
    departure_date = request.json["date"]
    form_response = simulate_browser_form_submit(outgoing_station, destination_station, departure_date)
    html = form_response.read().decode("utf-8")
    soup = bs(html, "html.parser")
    table_body = soup.find("tbody", {"id": "mainTabView:gidisSeferTablosu_data"})
    head_ways = []
    trs = table_body.find_all("tr",
                              {"class": ["ui-widget-content ui-datatable-even", "ui-widget-content ui-datatable-odd"]})
    for tr in trs:
        departure = tr.find("span", {"class": "seferSorguTableBuyuk"}).text
        duration = tr.find_all("label", {"class": "ui-outputlabel"})[1].text
        arrival = tr.find_all("span", {"class": "seferSorguTableBuyuk"})[1].text
        seat_li_elements = tr.find_all("li", text=re.compile("(Ekonomi)"))
        if len(seat_li_elements) != 0:
            empty_seats = extract_empty_seats(seat_li_elements[0].text)
            head_ways.append(
                {"departure": departure, "arrival": arrival, "duration": duration, "available_seats": empty_seats})
    return make_response(jsonify(head_ways))


app.run()

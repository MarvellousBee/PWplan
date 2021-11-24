import ast
import json
import asyncio
import datetime
import time
from win10toast import ToastNotifier
import pyttsx3
from threading import Thread
import os
from operator import itemgetter
from rich import print
from rich.panel import Panel
import sys
import aiohttp
import json

import win32api
import win32gui

from requests.exceptions import ConnectionError

from PW_lib import usosapi

Session = usosapi.USOSAPIConnection("https://apps.usos.pw.edu.pl/", "session1", "session2")


tk = None

sprawdziany = None
#"services/examrep/course_edition2"
old_tyl=40

tkn = ""

with open("tkn.txt") as token_txt:
    tkn = token_txt.readlines()



offline_mode = False
while True:
    try:
        while not  Session.set_access_data(tkn[0][:-1], tkn[1]):
            print("AUTORYZUJ")
            print(Session.get_authorization_url())
            Session.authorize_with_pin(input())
            tkn = Session.get_access_data()
            with open("tkn.txt", "w") as token_txt:
                token_txt.write(tkn[0])
                token_txt.write("\n")
                token_txt.write(tkn[1])
        break
    except (ConnectionResetError,ConnectionError):
        offline_mode = True
        with open("lekcje_forward.json", encoding="utf-8") as local_lessons:
            json_lessons = json.loads(local_lessons.read())
        break


w=win32gui
kiedyprzypomiec = 3
wysylaj_do_WF = True
engine = pyttsx3.init()

lesson_aliases = {
"Podstawy organizacji przedsiębiorstwa i systemów informatycznych zarządzania": "Przedsiębiorstwo",
"Techniki informacyjne i komunikacyjne": "informatyka",
"Zajęcia uzupełniające z matematyki": "Matematyka uzu",
"Inżynierskie bazy danych": "Bazy danych",
"Ekonomika i zarządzanie przedsiębiorstwem": "Przedsiębiorstwo",
"Wychowanie fizyczne":"WF",
"Laboratorium technik wytwarzania":"Odlewnictwo"
}


Alexa_titles = ["example fullscreen title", "title2"]
tab = [None, "CANCELLED", "CHANGE", "SHIFTED_SOURCE","ALSO_CANCELLED"]
def Alexa(tekst):
    engine.say(tekst)
    engine.runAndWait()



def datesort(inp):
    leng = len(inp)
    for st in range(0,leng):
        for i in range(1,leng-st):
            if inp[i-1][0]>inp[i][0]:
                inp[i-1], inp[i] = inp[i], inp[i-1]

    return [[i[0].strftime("%d.%m"), i[1]] for i in inp]


def get_notes(start = None):
    curr_year = "&"+str(datetime.datetime.now().year)
    with open("notatki.txt") as notatki:
        notki = notatki.readlines()
    outer = []
    for notka in notki:
        notka = notka.split()
        notka2 = [datetime.datetime.strptime(notka[0]+curr_year, "%d_%m&%Y").date(), " ".join(notka[1:])]
        if start==None or start<=notka2[0]:
            outer.append(notka2)
    return outer

async def fetch_lessons(day=0):
    lesssonstab = Session.get('services/tt/student', start=datetime.date.today() + datetime.timedelta(days=day), days=1, fields="start_time|name|end_time|room_number")
    return lesssonstab


lessonstab, tmrw_lessonstab, exams = None, None, None
async def fetch_both():
    global lessonstab, tmrw_lessonstab, exams, sprawdziany, offline_mode, json_lessons
    lessonstab = False
    trials = False
    if offline_mode:
        lessonstab = json_lessons[0]
        tmrw_lessonstab = json_lessons[1]
        trials = True

    while lessonstab == False or trials:# Could return []
        try:
            lessonstab = await fetch_lessons()
        except RuntimeError:
            return
        offline_mode, trials = False, False
        tmrw_lessonstab = await fetch_lessons(1)

        exams = get_notes(datetime.date.today())

        #SAVE
        print("halo")
        with open("lekcje_forward.json", encoding="utf-8") as local_lessons:
            json_lessons = json.loads(str([lessonstab, tmrw_lessonstab, exams]))
            print(json_lessons)
            exit()



czyJuzSPrawdzono = False
toaster = ToastNotifier()
input = win32api.GetLastInputInfo()
nextlesson = None
czyJuzSPrawdzono = False


interval, step = 6, 0

def main():
    global lessonstab, tmrw_lessonstab, exams, czyJuzSPrawdzono, step

    lastpanel = "first"

    #Main loop
    while True:
        now = datetime.datetime.now()
        now_time = now.time()
        inxmins = (now + datetime.timedelta(minutes=kiedyprzypomiec)).time()
        #Dziś
        panel_to_print = ""
        diff_prynt = False


        #sprawdź notatki




        for i in lessonstab:

            #oddzielanie nazwy od typu
            rozlaczenie = i["name"]["pl"].split(" - ")
            #print(rozlaczenie)

            if rozlaczenie[0] in lesson_aliases:
                i["name"]["pl"] = lesson_aliases[rozlaczenie[0]]
            else:
                i["name"]["pl"] = rozlaczenie[0]

            if isinstance(i["start_time"], str):
                i["start_time"] = datetime.datetime.strptime(i["start_time"], '%Y-%m-%d %H:%M:%S').time()
                i["end_time"] = datetime.datetime.strptime(i["end_time"], '%Y-%m-%d %H:%M:%S').time()
            spacing = old_tyl-(len(i["name"]["pl"])+len(i["room_number"])+len(i["typ_zajęć"]))

            if inxmins >= i["start_time"] >=now_time:
                nextlesson = i
                czyJuzSPrawdzono=True
                diff_prynt = True

            if now_time>=i["end_time"]:
                panel_to_print+=f'[bright_red]{i["start_time"].strftime("%H:%M")}[/bright_red] [magenta1]{i["room_number"]}[/magenta1] [dark_orange]{i["typ_zajęć"]}[/dark_orange] {i["name"]["pl"]} {spacing*" "} [bright_red]{i["end_time"].strftime("%H:%M")}[/bright_red]'#Było
            elif i["end_time"]>=now_time>=i["start_time"]:
                panel_to_print+=f'[bright_yellow]{i["start_time"].strftime("%H:%M")}[/bright_yellow] [magenta1]{i["room_number"]}[/magenta1] [dark_orange]{i["typ_zajęć"]}[/dark_orange] {i["name"]["pl"]} {spacing*" "} [bright_yellow]{i["end_time"].strftime("%H:%M")}[/bright_yellow]'#Trwa
            elif diff_prynt:
                panel_to_print+=f'[cyan]{i["start_time"].strftime("%H:%M")}[/cyan] [magenta1]{i["room_number"]}[/magenta1] [dark_orange]{i["typ_zajęć"]}[/dark_orange] {i["name"]["pl"]} {spacing*" "} [cyan]{i["end_time"].strftime("%H:%M")}[/cyan]'#Zaraz będzie
                diff_prynt = False
            else:
                panel_to_print+=f'[bright_green]{i["start_time"].strftime("%H:%M")}[/bright_green] [magenta1]{i["room_number"]}[/magenta1] [dark_orange]{i["typ_zajęć"]}[/dark_orange] {i["name"]["pl"]} {spacing*" "} [bright_green]{i["end_time"].strftime("%H:%M")}[/bright_green]'#Bedzie

            panel_to_print+="\n"

        #Jutro
        panel_to_print_tmrw = ""
        for i in tmrw_lessonstab:
            spacing = old_tyl-len(i["name"]["pl"])

            #oddzielanie nazwy od typu
            rozlaczenie = i["name"]["pl"].split(" - ")
            #print(rozlaczenie)

            if rozlaczenie[0] in lesson_aliases:
                i["name"]["pl"] = lesson_aliases[rozlaczenie[0]]
            else:
                i["name"]["pl"] = rozlaczenie[0]

            spacing = old_tyl-(len(i["name"]["pl"])+len(i["room_number"])+len(i["typ_zajęć"]))

            if isinstance(i["start_time"], str):
                i["start_time"] = datetime.datetime.strptime(i["start_time"], '%Y-%m-%d %H:%M:%S').time()
                i["end_time"] = datetime.datetime.strptime(i["end_time"], '%Y-%m-%d %H:%M:%S').time()

            panel_to_print_tmrw+=f'[bright_green]{i["start_time"].strftime("%H:%M")}[/bright_green] [magenta1]{i["room_number"]}[/magenta1] [dark_orange]{i["typ_zajęć"]}[/dark_orange] {i["name"]["pl"]} {spacing*" "} [bright_green]{i["end_time"].strftime("%H:%M")}[/bright_green]'#Jutro
            panel_to_print_tmrw+="\n"

        #Sprawdziany

        exams = ""
        notes = get_notes(datetime.date.today())[::-1]

        if notes:
            for nota in notes:
                #zmiana koloru wg odległości

                date_diff = (nota[0]-datetime.datetime.now().date()).days



                if date_diff==0:
                    date_clr = "bright_red"
                elif date_diff==1:
                    date_clr = "bright_yellow"
                elif date_diff<3:
                    date_clr = "bright_cyan"
                else:
                    date_clr = "bright_green"

                exams+=f"[{date_clr}]{nota[0].strftime('%d.%m')}[/{date_clr}] {nota[1]}\n"

        exams = exams[:-1]

        #Wypisz


        if lastpanel != panel_to_print:
            os.system("cls")
            print(Panel(panel_to_print[:-1], title = "[bright_cyan]"+datetime.datetime.now().strftime('%H:%M:%S')+"[/bright_cyan]", expand = False))
            print(Panel(panel_to_print_tmrw[:-1], title = "[bright_cyan]"+"Jutro"+"[/bright_cyan]", expand = False))
            print(Panel(exams, title = "[bright_cyan]"+datetime.date.today().strftime('%d.%m') + " Notatki" +"[/bright_cyan]", expand = False))
            lastpanel = panel_to_print

            if offline_mode:
                print("[red]OFFLINE[/red]")



        input = win32api.GetLastInputInfo()
        now = datetime.datetime.now()
        inxmins_DT = now + datetime.timedelta(minutes=kiedyprzypomiec)
        inxmins = inxmins_DT.time()



        if czyJuzSPrawdzono and not "CANCELLED" in nextlesson["name"]["pl"]:
            #Powiadomienia
            print("ZARA BĘDZIEEEE")
            text = nextlesson["start_time"].strftime("%H:%M")
            toaster.show_toast("ZARAZ " + nextlesson["name"]["pl"], text, duration=3, threaded=True)
            title = w.GetWindowText(w.GetForegroundWindow())
            if title in Alexa_titles:
                Alexa("Zaraz " + nextlesson["name"]["pl"])
            print("czekamy czekamy")
            while nextlesson["start_time"]>datetime.datetime.now().time():
                time.sleep(0.1)

            print("LEEEKCJAAAAAAAAA")
            toaster.show_toast("LEEEKCJAAAAAAAAA " + nextlesson["name"]["pl"], duration=3, threaded=True)
            title = w.GetWindowText(w.GetForegroundWindow())
            if title in Alexa_titles:
                Alexa(nextlesson["name"]["pl"])

            #customowe działania

            czyJuzSPrawdzono=False

        if interval == step:
            step = 0
            breaker = 0
            while True:
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(fetch_both())
                    break
                except ValueError: # I have no idea why 1 in 1000 times it breaks

                    time.sleep(5)
                    if breaker>10:
                        print("BREAKER")
                        os.system(f"python {os.path.abspath(__file__)}")
                        exit()
                    breaker+=1
                except (ConnectionResetError,ConnectionError):
                    os.system(f"python {os.path.abspath(__file__)}")
                    exit()
        else:
            step+=1

        time.sleep(2)


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(fetch_both())
    except Exception as e:
        offline_mode = True
    main()

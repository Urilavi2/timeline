import math
import os
import random
import PySimpleGUI as sg
import datetime
import event
import pymongo
import multiprocessing
import faces

timeline = {}
faces_arr = [faces.ohad_suprised,
             faces.lavi_suck,
             faces.ofek_toung,
             faces.yotam_bugger,
             faces.yuval_hitler,
             faces.shachar_raananim,
             faces.ofekinuo,
             faces.ofek_angle,
             # faces.baroz,
             faces.lior_helmet,
             faces.lior_komta,
             faces.nadav_idiot,
             faces.ofek_purim,
             faces.roi_drunk,
             faces.tom_bunny,
             faces.uri_nerd,
             faces.yotam_light,
             ]


# Hash per year, each hash holds hash per months, each holds hash per days. Each day holds a list of events


def connect_DB():  # add an option to user login an admin login!
    uri = "mongodb+srv://visitor:YIuwTDgfNygklz0X@cluster0.uhhf5bq.mongodb.net/?retryWrites=true&w=majority"

    # Create a new client and connect to the server
    try:
        myclient = pymongo.MongoClient(uri)
    except Exception as e:
        print("Exception encountered! Error info:\n", e)
        print("Exiting...")
        for p in multiprocessing.active_children():
            p.terminate()
            p.join()
        exit("-TIMEOUT-")

    # Send a ping to confirm a successful connection
    try:
        myclient.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        mydb = myclient["timeline"]
        mycol = mydb["events"]
        dblist = myclient.list_database_names()
        if "timeline" in dblist:
            print("The database exists.")
            collist = mydb.list_collection_names()
            if "events" in collist:
                print("The collection exists.")
            else:
                print(f"collection '{mycol.name}' not found!")
                processes = multiprocessing.active_children()
                for process in processes:
                    process.kill()
                sg.popup("collection not found!\n     Exiting...",
                         button_type=5,  # no buttons!
                         no_titlebar=True,
                         auto_close=True,
                         auto_close_duration=2,
                         background_color='red',
                         # non_blocking=True,
                         font=('any', 20, 'bold'),
                         text_color='black')
                # exit(-1)
        else:
            print(f"database '{mydb.name}' not found!")
            processes = multiprocessing.active_children()
            for process in processes:
                process.kill()
            sg.popup("Database not found!\n          Exiting...",
                     button_type=5,  # no buttons!
                     no_titlebar=True,
                     auto_close=True,
                     auto_close_duration=2,
                     background_color='red',
                     # non_blocking=True,
                     font=('any', 20, 'bold'),
                     text_color='black')

            # exit(-1)

        return myclient, mydb, mycol
    except Exception as e:
        print(e)
        exit()


def get_creation_and_modification_dates(file_path):
    try:
        stat_info = os.stat(file_path)
        creation_timestamp = stat_info.st_ctime
        creation_date = datetime.datetime.fromtimestamp(creation_timestamp).strftime("%d-%m-%Y")

        modification_timestamp = stat_info.st_mtime
        modification_date = datetime.datetime.fromtimestamp(modification_timestamp).strftime("%d-%m-%Y")

        return creation_date, modification_date
    except Exception as e:
        return str(e), str(e)


def massupload(folder_path, collection):
    """
    INTERNAL USE!!

    mass upload of photos from the
    :param folder_path:
    :param collection:
    :return:
    """

    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            creation_date, mod_date = get_creation_and_modification_dates(file_path)
            ev = event.TimeEvent(name=file_name[:-4],
                                 date=str(mod_date),
                                 author=None,
                                 summary=None,
                                 pic=event.image_to_bin(file_path))
            print(ev.get_date())
            continue
            try:
                collection.insert_one(ev.mongoready())
            except Exception as e:
                print(str(e))
                return


def add_to_timeline(collection):
    """
    Building the timeline local data-structure.
    A 3-level hash-table. The first level for years, the second for months and the third for days.
    Each level has only the known dates in the collection --> Empty days, months and years will not be part of the
    data-structure.

    :param collection: MongoDB collection
    :return:
    """
    ev = event.add_event()
    if ev:
        date = ev.get_date()
        date = datetime.datetime.strptime(date, '%d-%m-%Y').date()
        year_key = date.strftime("%Y")
        month_key = date.strftime("%m")
        day_key = date.strftime("%d")
        if year_key not in timeline:
            timeline[year_key] = {}
        if month_key not in timeline[year_key]:
            timeline[year_key][month_key] = {}
        if day_key not in timeline[year_key][month_key]:
            timeline[year_key][month_key][day_key] = []
        timeline[year_key][month_key][day_key].append(ev)
        collection.insert_one(ev.mongoready())
        id_obj = collection.find({"date": ev.get_date(), "name": ev.get_name()}, {"_id": 1})
        print("id[0]: ", id_obj[0])
        timeline[year_key][month_key][day_key][-1].set_id(id_obj[0]["_id"])


def get_event_pic(event_id, collection):
    """
    Find a specific event by its id in the database's collection and return event's picture

    :param event_id: Wanted event's id (idObject)
    :param collection: MongoDB collection
    :return: event's picture (binary data)
    """
    temp_pic = collection.find({"_id": event_id}, {"pic": 1})
    if not temp_pic:
        print("Event not found!")
        return -1
    return temp_pic[0]["pic"]
    # the find method returns a cursor that allows to iterate the documents that match the query.
    # Because each document has a unique id, therefore we return temp_pic[0]


def set_pic(eve, collection):
    """
    Assign picture to local event from database
    :param eve: Specific event (event.TimeEvent object)
    :param collection: MongoDB collection
    :return:
    """
    pic = get_event_pic(eve.get_id(), collection)
    eve.set_pic(pic)


def day_chooser(event_days: dict, num_of_days: int, month: str, year: str, collection):
    """
    In this window the user will choose the day on the year and month he chose earlier.
    Each day is marked as an eggplant. To choose a day just press an eggplant! (:

    :param collection: MongoDB collection
    :param year: Chosen year
    :param month: Chosen month
    :param event_days: Dict of days in the chosen month.
    :param num_of_events: number of days in the month with events --> Unused parameter, can be any kind of int..

    :return:
    """
    window_scale = 0.8
    x, y = sg.Window.get_screen_size()
    screen_size = (int(x * window_scale), int(y * window_scale))  # adjust elements!!

    scale_x = x / 1920  # the original program was built on 1920x1080 res
    scale_y = y / 1080

    days = list(event_days.keys())
    days.sort()  # maximum 31 days a month --> O(1)
    page = math.ceil(len(days) / 6)
    current_page = 1
    day_idx_page_counter = 0

    layout = [
        [sg.T("", size=(int(50 * scale_x), 1)), sg.T(f"Year: {year}     ", font=('Algerian', int(30 * scale_x))),
         sg.T(f"month: {month}", font=('Algerian', int(30 * scale_x)))],
        [sg.T("", size=(int(80 * scale_x), 1)), sg.B("change", size=(9, 2))],
        [sg.Graph(canvas_size=(int(1400 * scale_x), int(450 * scale_y)),
                  graph_bottom_left=(0, 0),
                  graph_top_right=(int(1400 * scale_x), int(450 * scale_y)),
                  enable_events=True,
                  key='_GRAPH_')],
        [sg.B("back"),
         sg.T("", size=(int(65 * scale_x), 1)),
         sg.B("Previous", size=(9, 1), visible=False),
         sg.B("Next", size=(9, 1), visible=False)]
    ]

    window = sg.Window("Day picker", layout, no_titlebar=True, finalize=True, keep_on_top=True, grab_anywhere=True)
    graph = window['_GRAPH_']
    graph_x, graph_y = int(150 * scale_x), int(180 * scale_y)
    locations = []
    days_elements = []
    new_graph_y = graph_y + int(180 * scale_y)
    allowed_margin = 60
    for day_idx, day in enumerate(days):
        if day_idx % 6 == 0 and day_idx != 0:
            day_idx_page_counter = day_idx
            break
        new_graph_x = graph_x + int(140 * scale_x)

        day_text = day + '.' + month
        graph.draw_text(day_text, location=(graph_x + 25, graph_y-100), font=('FrankRuehl', 14, 'bold'),)
        locations.append((graph_x + 25, graph_y + 25))

        if day_idx % 2 == 0:  # For an even day, draw an eggplant down --> up
            graph.draw_line((graph_x + int(scale_x * 30), graph_y), (new_graph_x, new_graph_y - int(scale_y * 20)), 'red', 8)
            days_elements.append((graph.draw_image(data=faces.eggplant, location=(graph_x, graph_y)), day))
            graph_y = new_graph_y
        else:                   # For an odd day, draw an eggplant up --> down
            graph_y = new_graph_y - int(180 * scale_y)
            graph.draw_line((graph_x + int(scale_x * 30), new_graph_y - int(scale_y * 20)), (new_graph_x, graph_y), 'red', 8)
            days_elements.append((graph.draw_image(data=faces.eggplant, location=(graph_x, new_graph_y)), day))
        graph_x = new_graph_x

    if page > 1:
        window["Next"].update(visible=True)

    while True:
        events, values = window.read()
        mouse_x, mouse_y = values['_GRAPH_']

        if events == "back":
            break

        if events == "_GRAPH_":
            for location_idx, location in enumerate(locations):
                if abs(mouse_x - location[0]) <= allowed_margin and abs(mouse_y + 50 - location[1]) <= allowed_margin:
                    # THERE WAS A PRESS ON AN ITEM!
                    day = days_elements[location_idx][1]  # [1] is the day event list!
                    window.hide()
                    event_chooser(event_days[day], collection)
                    window.un_hide()

        if events == "Next":
            print("page number: ", current_page)
            window["Next"].update(visible=False)
            window["Previous"].update(visible=True)
            window["Next"].update(visible=True)
            current_page += 1
            if current_page == page:
                window["Next"].update(visible=False)  # hide next button if this is the last page
            graph.erase()
            locations.clear()
            days_elements.clear()
            graph_x, graph_y = int(150 * scale_x), int(180 * scale_y)
            new_day_list = days[day_idx_page_counter:]  # from the current index to the last index
            for day_idx, day in enumerate(new_day_list):
                if day_idx % 6 == 0 and day_idx != 0:  # break condition --> after 6 elements
                    day_idx_page_counter = day_idx
                    break

                new_graph_x = graph_x + int(140 * scale_x)

                day_text = day + '.' + month

                if day_idx % 2 == 0:  # For an even day, draw an eggplant down --> up
                    graph_y = new_graph_y - int(180 * scale_y)
                    graph.draw_line((graph_x + int(scale_x * 30), graph_y),
                                    (new_graph_x, new_graph_y - int(scale_y * 20)), 'red', 8)
                    days_elements.append((graph.draw_image(data=faces.eggplant, location=(graph_x, graph_y)), day))

                else:  # For an odd day, draw an eggplant up --> down
                    graph.draw_line((graph_x + int(scale_x * 30), new_graph_y - int(scale_y * 20)),
                                    (new_graph_x, graph_y), 'red', 8)
                    graph_y = new_graph_y
                    days_elements.append((graph.draw_image(data=faces.eggplant, location=(graph_x, graph_y)), day))
                locations.append((graph_x + 25, graph_y + 25))
                graph.draw_text(day_text, location=(graph_x + 25, graph_y - 100), font=('FrankRuehl', 14, 'bold'), )
                graph_x = new_graph_x

        if events == "Previous":
            window["Next"].update(visible=True)
            current_page -= 1
            if current_page == 1:
                window["Previous"].update(visible=False)
            graph.erase()
            locations.clear()
            days_elements.clear()
            graph_x, graph_y = int(150 * scale_x), int(180 * scale_y)
            day_idx_page_counter -= 12
            new_day_list = days[day_idx_page_counter:]
            for day_idx, day in enumerate(new_day_list):
                if day_idx % 6 == 0 and day_idx != 0:
                    day_idx_page_counter = day_idx
                    break

                new_graph_x = graph_x + int(140 * scale_x)

                day_text = day + '.' + month

                if day_idx % 2 == 0:  # For an even day, draw an eggplant down --> up
                    graph_y = new_graph_y - int(180 * scale_y)
                    graph.draw_line((graph_x + int(scale_x * 30), graph_y),
                                    (new_graph_x, new_graph_y - int(scale_y * 20)), 'red', 8)
                    days_elements.append((graph.draw_image(data=faces.eggplant, location=(graph_x, graph_y)), day))

                else:  # For an odd day, draw an eggplant up --> down
                    graph.draw_line((graph_x + int(scale_x * 30), new_graph_y - int(scale_y * 20)),
                                    (new_graph_x, graph_y), 'red', 8)
                    graph_y = new_graph_y
                    days_elements.append((graph.draw_image(data=faces.eggplant, location=(graph_x, graph_y)), day))
                graph.draw_text(day_text, location=(graph_x + 25, graph_y - 100), font=('FrankRuehl', 14, 'bold'), )
                locations.append((graph_x + 25, graph_y + 25))
                graph_x = new_graph_x
    window.close()


def event_chooser(event_days: list[event.TimeEvent], collection):
    """
    Within a day that was chosen by user, this window will offer events that happened
     on that exact day (as specified by the photo's uploader). Each event is marked by a funny face of a funny guy/girl.

     Press on a face to open event's information.

    :param event_days: A list of events (event.TimeEvent objects!) from the chosen day.
    :param collection: MongoDB collection
    :return:
    """
    window_scale = 0.8
    x, y = sg.Window.get_screen_size()
    screen_size = (int(x * window_scale), int(y * window_scale))  # adjust elements!!

    scale_x = x / 1920  # the original program was built on 1920x1080 res
    scale_y = y / 1080

    page = math.ceil(len(event_days) / 6)
    current_page = 1
    ev_idx_page_counter = 0

    layout = [
        [sg.Graph(canvas_size=(int(1400 * scale_x), int(450 * scale_y)),
                  graph_bottom_left=(0, 0),
                  graph_top_right=(int(1400 * scale_x), int(450 * scale_y)),
                  enable_events=True,
                  key='_GRAPH_')],
        [sg.B("back"),
         sg.T("", size=(int(65 * scale_x), 1)),
         sg.B("Previous", size=(9, 1), visible=False),
         sg.B("Next", size=(9, 1), visible=False)]
    ]

    window = sg.Window("Event picker", layout, no_titlebar=True, finalize=True, keep_on_top=True, grab_anywhere=True,
                       location=(200, 300))
    graph = window['_GRAPH_']
    graph_x, graph_y = int(100 * scale_x), int(180 * scale_y)
    locations = []
    events_elements = []
    new_graph_y = graph_y + int(180 * scale_y)
    allowed_margin = 60

    for ev_idx, ev in enumerate(event_days):
        if ev_idx % 6 == 0 and ev_idx != 0:
            ev_idx_page_counter = ev_idx
            break

        # events_elements.append((graph.draw_image(data=random.choice(faces_arr), location=(graph_x, graph_y)), ev))
        print("face location: ", graph_x, graph_y)
        new_graph_x = graph_x + int(140 * scale_x)

        name_idx = 6
        event_full_name = ev.get_name()
        event_final_name = event_full_name[:6]
        try:
            while event_full_name[name_idx] != ' ' or event_full_name[name_idx] == '':
                event_final_name += event_full_name[name_idx]
                name_idx += 1
        except IndexError:
            print(IndexError)
        graph.draw_text(event_final_name, location=(graph_x + 20 + (name_idx - 5), graph_y - 100), font=('FrankRuehl', 10, 'bold'), )
        locations.append((graph_x + 25, graph_y + 25))

        if ev_idx % 2 == 0:  # even event, draw down --> up
            graph.draw_line((graph_x + int(scale_x * 30), graph_y), (new_graph_x, new_graph_y - int(scale_y * 20)), 'red', 8)
            events_elements.append((graph.draw_image(data=random.choice(faces_arr), location=(graph_x, graph_y)), ev))
            graph_y = new_graph_y
        else:               # odd event, draw up --> down
            graph_y = new_graph_y - int(180 * scale_y)
            graph.draw_line((graph_x + int(scale_x * 30), new_graph_y - int(scale_y * 20)), (new_graph_x, graph_y), 'red', 8)
            events_elements.append((graph.draw_image(data=random.choice(faces_arr), location=(graph_x, new_graph_y)), ev))
        graph_x = new_graph_x

    if page > 1:
        window["Next"].update(visible=True)

    while True:
        events, values = window.read()
        mouse_x, mouse_y = values['_GRAPH_']

        if events == "back":
            break

        if events == "_GRAPH_":
            for location_idx, location in enumerate(locations):
                if abs(mouse_x - location[0]) <= allowed_margin and abs(mouse_y + 50 - location[1]) <= allowed_margin:
                    # THERE WAS A PRESS ON AN ITEM!
                    ev = events_elements[location_idx][1]  # [1] is the an event!

                    window.hide()
                    flag = multiprocessing.Event()
                    if not ev.pic:
                        p = multiprocessing.Process(target=loading,
                                                    args=(line_bubbles,
                                                          flag,
                                                          "Fetching event picture..."))
                        p.start()
                        set_pic(ev, collection)
                    flag.set()
                    edit = ev.show_event(collection=collection, data_struct=timeline)
                    while edit:
                        edit = ev.show_event(collection=collection, data_struct=timeline)
                    window.starting_window_position = (200, 300)
                    window.un_hide()

        if events == "Next":
            print("page number: ", current_page)
            window["Next"].update(visible=False)
            window["Previous"].update(visible=True)
            window["Next"].update(visible=True)
            current_page += 1
            if current_page == page:
                window["Next"].update(visible=False)
            graph.erase()
            locations.clear()
            events_elements.clear()
            graph_x, graph_y = int(150 * scale_x), int(180 * scale_y)
            new_ev_list = event_days[ev_idx_page_counter:]
            for ev_idx, ev in enumerate(new_ev_list):
                if ev_idx % 6 == 0 and ev_idx != 0:
                    ev_idx_page_counter += 6
                    break

                new_graph_x = graph_x + int(140 * scale_x)

                name_idx = 6
                event_full_name = ev.get_name()
                event_final_name = event_full_name[:6]
                try:
                    while event_full_name[name_idx] != ' ' or event_full_name[name_idx] == '':
                        event_final_name += event_full_name[name_idx]
                        name_idx += 1
                except IndexError as e:
                    print(str(e))

                if ev_idx % 2 == 0:  # even event, draw down --> up
                    graph_y = new_graph_y - int(180 * scale_y)
                    graph.draw_line((graph_x + int(scale_x * 30), graph_y),
                                    (new_graph_x, new_graph_y - int(scale_y * 20)), 'red', 8)
                    events_elements.append(
                        (graph.draw_image(data=random.choice(faces_arr), location=(graph_x, graph_y)), ev))

                else:  # odd event, draw up --> down

                    graph.draw_line((graph_x + int(scale_x * 30), new_graph_y - int(scale_y * 20)),
                                    (new_graph_x, graph_y), 'red', 8)
                    graph_y = new_graph_y
                    events_elements.append(
                        (graph.draw_image(data=random.choice(faces_arr), location=(graph_x, graph_y)), ev))

                graph.draw_text(event_final_name, location=(graph_x + 20 + (name_idx - 5), graph_y - 100),
                                font=('FrankRuehl', 10, 'bold'), )
                locations.append((graph_x + 25, graph_y + 25))
                graph_x = new_graph_x

        if events == "Previous":
            print("page number: ", current_page)
            window["Next"].update(visible=True)
            current_page -= 1
            if current_page == 1:
                window["Previous"].update(visible=False)
            graph.erase()
            locations.clear()
            events_elements.clear()
            graph_x, graph_y = int(150 * scale_x), int(180 * scale_y)
            ev_idx_page_counter -= 12
            new_ev_list = event_days[ev_idx_page_counter:]
            for ev_idx, ev in enumerate(new_ev_list):
                if ev_idx % 6 == 0 and ev_idx != 0:
                    ev_idx_page_counter += 6
                    break

                new_graph_x = graph_x + int(140 * scale_x)

                name_idx = 6
                event_full_name = ev.get_name()
                event_final_name = event_full_name[:6]
                try:
                    while event_full_name[name_idx] != ' ' or event_full_name[name_idx] == '':
                        event_final_name += event_full_name[name_idx]
                        name_idx += 1
                except IndexError as e:
                    print(str(e))

                if ev_idx % 2 == 0:  # even event, draw down --> up
                    graph_y = new_graph_y - int(180 * scale_y)
                    graph.draw_line((graph_x + int(scale_x * 30), graph_y),
                                    (new_graph_x, new_graph_y - int(scale_y * 20)), 'red', 8)
                    events_elements.append(
                        (graph.draw_image(data=random.choice(faces_arr), location=(graph_x, graph_y)), ev))

                else:  # odd event, draw up --> down
                    graph.draw_line((graph_x + int(scale_x * 30), new_graph_y - int(scale_y * 20)),
                                    (new_graph_x, graph_y), 'red', 8)
                    graph_y = new_graph_y
                    events_elements.append(
                        (graph.draw_image(data=random.choice(faces_arr), location=(graph_x, graph_y)), ev))

                graph.draw_text(event_final_name, location=(graph_x + 20 + (name_idx - 5), graph_y - 100),
                                font=('FrankRuehl', 10, 'bold'), )
                locations.append((graph_x + 25, graph_y + 25))
                graph_x = new_graph_x

    window.close()


def year_month_chooser(collection):
    """
    Year and month choosing window. Can press the 'cancel' button to return to main menu,
    or press 'GO' and navigate to that date.

    :param collection: MongoDB collection
    :return:
    """
    years = list(timeline.keys())
    years = list(map(int, years))
    years.sort()
    years = list(map(str, years))
    months = []
    layout = [
        [sg.Text("Choose year and month to scout in", font=("any", 20, "underline"))],
        [sg.Col([[sg.T("", size=(10, 1)), sg.Text("Year: ")], [sg.T("", size=(10, 1)), sg.Text("Month: ")]]),
         sg.Col([[sg.Combo(years, key="_YEAR_", default_value=str(min(list(map(int, years)))), size=(20, 7),
                           enable_events=True)],
                 [sg.Combo(months, key="_MONTH_", default_value='', size=(20, 7))]])],
        [sg.T("", size=(17, 1)), sg.B("Cancel", size=(8, 2)), sg.B("GO", size=(8, 2))]
    ]
    date_chooser_window = sg.Window("Scout", layout, finalize=True, no_titlebar=True, keep_on_top=True)
    months = list(timeline[date_chooser_window["_YEAR_"].DefaultValue].keys())
    date_chooser_window["_MONTH_"].update(value=str(min(list(map(int, months)))))
    while True:
        events, values = date_chooser_window.read()

        if events in (sg.WIN_CLOSED, "Cancel"):
            break

        if events == "_YEAR_":
            print(events)
            print(values["_YEAR_"])
            months = list(timeline[values["_YEAR_"]])
            date_chooser_window["_MONTH_"].update(values=months, value=str(min(list(map(int, months)))))

        if events == "GO":
            if len(list(values["_MONTH_"])) < 2:
                month = '0' + values["_MONTH_"]
            else:
                month = values["_MONTH_"]
            chosen_month = timeline[values["_YEAR_"]][month]
            event_days = list(chosen_month.keys())
            num_of_days = len(event_days)
            date_chooser_window.hide()
            day_chooser(chosen_month, int(num_of_days), month, values["_YEAR_"], collection)
            date_chooser_window.un_hide()
    date_chooser_window.close()


def first_info(mycol):
    """
    Recover data from MongoDB cloud and build the local database

    :param mycol: MongoDB collection
    :return:
    """
    for ev in mycol.find({}, {"name": 1, "author": 1, "summary": 1, "date": 1, "_id": 1}):
        try:
            ev["date"] = datetime.datetime.strptime(ev["date"], '%d-%m-%Y').date()
        except Exception as e:
            # After editing an event the date section gone bad, therefore the try except statement.
            # The logic has not changed.
            print("Error: ", e)
            print("Event name: ", ev["name"])
            print("Event date: ", ev["date"])
            ev["date"] = datetime.datetime.strptime(ev["date"], '%Y-%m-%d').date()
        year_key = ev["date"].strftime("%Y")
        month_key = ev["date"].strftime("%m")
        day_key = ev["date"].strftime("%d")
        if year_key not in timeline:
            timeline[year_key] = {}
        if month_key not in timeline[year_key]:
            timeline[year_key][month_key] = {}
        if day_key not in timeline[year_key][month_key]:
            timeline[year_key][month_key][day_key] = []

        timeline[year_key][month_key][day_key].append(event.TimeEvent(name=ev["name"],
                                                                      date=ev["date"],
                                                                      author=ev["author"],
                                                                      summary=ev["summary"],
                                                                      pic=None,
                                                                      id=ev["_id"]))


def loading(gif, flag, message=None):
    """
    Loading screen gif

    :param gif: Chosen gif to use while loading
    :param flag: MultiProcessing flag
    :param message: Wanted message to appear above the gif
    :return:
    """

    layout = [
        [sg.T(message, background_color='white', text_color='black')],
        [sg.Image(data=gif, key="-GIF-", background_color='white')]
    ]
    loading_window = sg.Window(title="loading",
                               layout=layout,
                               no_titlebar=True,
                               keep_on_top=True,
                               background_color='white',
                               alpha_channel=0.75)
    while not flag.is_set():
        e, v = loading_window.read(timeout=25, timeout_key="-TIMEOUT-")
        loading_window.Element('-GIF-').UpdateAnimation(gif, time_between_frames=50)
    loading_window.close()


def main():

    # sg.popup("To make window transparent --> look for \"See-through mode\"\n\n",
    #          no_titlebar=True,
    #          non_blocking=False,
    #          font=("any", 40),
    #          button_type=0,
    #          any_key_closes=True)

    # connecting to database + loading wheel
    flag = multiprocessing.Event()
    p = multiprocessing.Process(target=loading, args=(line_bubbles, flag, "Connecting to database..."))
    p.start()
    myclient, mydb, mycol = connect_DB()
    flag.set()
    p.join()
    # end of connection

    # fetching info from database + loading wheel
    flag.clear()
    p = multiprocessing.Process(target=loading, args=(line_bubbles, flag, "Fetching known events..."))
    p.start()
    first_info(mycol)
    flag.set()
    p.join()
    # end of fetching

    # folder_path = "C:/Users/urila/Desktop/timeline/photos/upload/uploded"
    # massupload(folder_path, mycol)
    # exit()

    window_scale = 0.8
    x, y = sg.Window.get_screen_size()
    print(f"x: {x}, y: {y}")
    screen_size = (int(x * window_scale), int(y * window_scale))  # adjust elements!!

    scale_x = x / 1920  # the original program was built on 1920x1080 res
    scale_y = y / 1080

    groupname = "CosEmek"
    layout = [
        [sg.Text('', size=(int(25 * scale_x), 1)), sg.Text(f"{groupname}'s Timeline",
                                                           font=("Algerian", int(80 * scale_x)),
                                                           text_color="light blue")],
        [sg.Text('', size=(int(8 * scale_x), 1)),
         sg.Text("Choose to scout throughout the timeline or pick a random event",
                 font=("Algerian", int(30 * scale_x)),
                 text_color="light blue")],

        [sg.Text('', size=(int(85 * scale_x), 1)),
         sg.Button("Add Event", key="_ADD_", size=(int(15 * scale_x), int(2 * scale_y)))],

        [sg.Col([[sg.Button("Random Event",
                            button_color=("red", "dark red"),
                            key="-RANDOM-",
                            # size=(int(47 * scale_x), int(scale_y * 20)),
                            size=(int(35 * scale_x), int(scale_y * 15)),
                            font=("Aharoni", int(scale_x * 26)),
                            expand_x=True, expand_y=True)]], expand_x=True, expand_y=True)
            ,

         sg.Col([[sg.Button("Scout Timeline",
                            button_color=("blue", "dark blue"),
                            key="-SCOUT-",
                            # size=(int(47 * scale_x), int(scale_y * 20)),
                            # size=(36, 3),
                            size=(int(35 * scale_x), int(scale_y * 15)),
                            font=("Aharoni", int(scale_x * 26)),
                            expand_x=True, expand_y=True)]], expand_x=True, expand_y=True)
         ],
        [sg.Text('', size=(int(85 * scale_x), 1)), sg.Button("Close", size=(int(15 * scale_x), 1))],
        # change the close button to an image
    ]
    mainwindow = sg.Window("Timeline Application", layout, size=screen_size)

    while True:
        events, values = mainwindow.read()

        if events in (sg.WIN_CLOSED, "Close"):
            break

        if events == "-RANDOM-":
            mainwindow.hide()

            years = timeline.keys()
            random_year = random.choice(list(years))
            months = timeline[random_year].keys()
            random_month = random.choice(list(months))
            days = timeline[random_year][random_month].keys()
            random_day = random.choice(list(days))
            random_event = random.choice(timeline[random_year][random_month][random_day])
            if not random_event.pic:
                #  LOADING WHEEL
                flag.clear()
                p = multiprocessing.Process(target=loading, args=(line_bubbles, flag, "Fetching event information..."))
                p.start()
                set_pic(random_event, mycol)
            flag.set()  # END OF LOADING WHEEL
            edit = random_event.show_event(collection=mycol, data_struct=timeline)
            while edit:
                edit = random_event.show_event(collection=mycol, data_struct=timeline)
            mainwindow.un_hide()

        elif events == "_ADD_":
            mainwindow.hide()
            add_to_timeline(mycol)
            mainwindow.un_hide()

        elif events == "-SCOUT-":
            mainwindow.hide()
            year_month_chooser(mycol)
            mainwindow.un_hide()

    mainwindow.close()

if __name__ == '__main__':
    line_bubbles = b'R0lGODlhoAAUAOMAAHx+fNTS1KSipKyqrPz6/KSmpKyurPz+/P7+/gAAAAAAAAAAAAAAAAAAAAAAAAAAACH/C05FVF' \
                   b'NDQVBFMi4wAwEAAAAh+QQJCQAIACwAAAAAoAAUAAAE/hDJSau9OOvNu/9gKI5kaZ5oqq5s675wLM90bd94ru/jERi' \
                   b'GwEFD+AWHmSJQSDQyk04kRnlsLqUX6nMatVanBYAYMCCAx2RzNjwun9tqC4Etdq/Rdjk9/a7HK3N4fxSBcBgBaGIBh4' \
                   b'kAixeIiY8WkWiTFZVjlxSZioySn5ahmqOeF3tiAhioAKqnja4WrLEVs6uwt4m0FLavurlouxOsAxgCjcUXx4nJFst4x' \
                   b'sjRzNPQytLX1NnWlI2bE52OpeKQ3uPfEuHoCOrn7uWgWQOCGAfzYwaDEwT3YvlT/QD8k4dmoJyABgEh1CeBX0GGCBzi' \
                   b'gyjRH0QEPq542XIh45d6KF0yeORoYSSWkiFBahSZsmNLHjBjypxJs6bNmzhz6tzJs6fPn0BBRAAAIfkECQkAFgAsAAA' \
                   b'AAKAAFACEBAIEhIaETEpM1NbU9Pb0NDI0dHJ0rK6s3N7cFBYU/P78PD48fH58tLa0XFpc3Nrc/Pr8NDY0dHZ0tLK0' \
                   b'5OLkHBoc/v7+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABf6gJY5kaZ5oqq5s675wLM90bd94ru9879OIQKEQoPy' \
                   b'OyKSNUAA4nw6IckqtjiCJpxaQkFq/YJ2iudUWTpBBo/HwohRqtvsEX7dVdTk+fk/l+298cyZ/gyWFJghlZQglEAcBDJIT' \
                   b'hiIQE5KTlRaXmQyUKJ2ZoGiYo5uimqGmqqWepCapn4MGi1sGJQOekg8ougyRvL6SwQy9J7/FxybJmcu5xM7DwNLI0cLW1N' \
                   b'gjC7ZaESUH158o4rsT5bvkJ+av6efv7uzq6PPw9vLc3k/gJKzB9UyYixQpYLhoBd8RXCcQIcOD1BLaW2iQxEBqFUdclDii1' \
                   b'j4AuEj80vZM5LiSI3yabYOmzdg0ZS+rMTsZc6XJliUVfSwpC5YjVrNWvUIF1CeJnkSHCj21tFWsooPG7CtgSMGDCRMGbLI0' \
                   b'ACsgNF0nfI0Vdqyjsls5oVWRxmvatmLfrjVBIMuiBATC6N1Lg0kZAXn5Ch7c4oGBIRJQEl7MuLHjx5AjS55M+UsIACH5BAkJ' \
                   b'AB0ALAAAAACgABQAhAQCBISChERGRMTCxCwuLOTi5LSytBQWFGRmZDw6PPT29Ly6vAwODNza3DQ2NHx6fPz+/AQGBIyOjFRW' \
                   b'VDQyNOTm5LS2tBwaHDw+PPz6/Ly+vNze3Hx+fP7+/gAAAAAAAAX+YCeOZGmeaKqubOu+cCzPdG3feK7vfO//pYKEQpFUgMi' \
                   b'kcgQZCCIRwQByUlAA2Cwis+x6bxlCNkvgkhSH8fhg/rrfKohYjSVQRZArnXyCNDQaDXcofoCCcX+Bg32JhymFioiGiyaQjo' \
                   b'SNlCIDe1kDIxudYxslEAscARwcC22lFqmoFq0kEK+qAbKEtrGzTLu4vXi/uX3DwR21sMAmGKIAGCMPzlgPJQ2qqKoNKNfZq' \
                   b'Nsn3crgJuK35Na359zq3+zeAegk5u4lEc4RI83TDiUW2akCGEDxL6CqgScKPoCF0IRChgRRLTwYMcBEDg39SYSYcCNFe84Y' \
                   b'6JsGoB+JVwvHH3x0qAxVxpPwMBK0CPDliILqbIpAWbNizpkqA9pM4CxBNJLV5mELKG+EOJUcmoowl0pqB3pR3xm0ipWruqp' \
                   b'asTXV4EwDKJKkSGSwlYqYibUGWaGAG9TAMbjZ5J6g6/Iu21V+aQoMnLeXnE52mMxBrMnPAguX9jZYsKDBMTyTK2tSm9myig' \
                   b'ydN48ATdlzCtKaP3e+u5jMLDSdDiiAQ7t2KQ0CsGDQsFlBaywTLtseTrzEBg4UCHBIW7y58+fQo0ufTr26dR4hAAAh+QQJC' \
                   b'QAhACwAAAAAoAAUAIUEAgSEgoREQkTEwsQsLizk4uSkpqRsbmwUEhRUUlT09vTc2tw0NjS0trQMDgyUkpRMTkwcGhz8/vy8' \
                   b'vrwEBgSEhoRERkTExsQ0MjTk5uR8fnwUFhRcXlz8+vzc3tw8Ojy8urz+/v4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAG/sCQcEgsGo' \
                   b'/IpHLJbDqf0Kh0Sq1ar9isdsvter/VwoPBeGTA6HRWoVhKLhAKBXKRHDsEgH5/6Kj/gG4TCHoIE3ZGHRh7ewR+RAobjIwbj' \
                   b'4GXgRIJkwAJiEMSeZwABJ8Si6N6BEcSHhMDC5+srrCyRq2vsUq4tbu0ukm8wEjCtkMTqSBFF6l6F0MFzXseRRIgARrZIMZC' \
                   b'HSAa2BrbSN7g2twh5eHjd9/r6Orn5O7y1YSjCLIW0hZDGtJ6NBRZkA0btgVICBoEh/CIQnMBGhp5aFDiQIgME2KMqHEhxyI' \
                   b'KpLUZQkEahSH7AH4o0mAhuAZIvpnLBvOIzJk1jdwMl7PI406aMbPhDFoQKEiRREo2c4ASIICVRFoW1dCTCD1wAaoOkbpQq5' \
                   b'Cr2LyGAEs1aLiwZotqlXCPkwNZAqQJ8OdUIBGKGR1O1WDx7syDGjH2HUJQcOCFg4UURnzEQCoDRQZIGzDEg1NqRKzNBGGpmk' \
                   b'xsnIldDc1qdOfMpkVvPg0q9a2UjCzYCpWqFChRtY1JWAACxALWmXn7Bg5K+O9dxokL2d37eLDkyJsrl9DgnoMG3PBwcgRSE' \
                   b'r6RmMIHYrOkwwAIeiwMAK4A9x4OysXLn+/EQwAyATDT38+/v///AAYo4IAE0hcEACH5BAkJACEALAAAAACgABQAhQQCBISC' \
                   b'hERCRMTCxCwuLOTi5KSmpGxubBQSFFRSVPT29Nza3DQ2NLS2tAwODJSSlExOTBwaHPz+/Ly+vAQGBISGhERGRMTGxDQyNOT' \
                   b'm5Hx+fBQWFFxeXPz6/Nze3Dw6PLy6vP7+/gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAb+wJBwSCwaj8ikcslsOp/QqHRKrVqv2Kx2y' \
                   b'+16v+Bi4cFgPDLhtNqqUCwlFwiFArlIjh0CYM8/dNaAgUgSEwh7CBN3Rh0YfHwEf0QKG46OG5GCmVYSHhMDC4pGEgmVAAmh' \
                   b'QhJ6pQAEoRKNrHsER5yeoEq2n6iinbu5vrhJusKDwbxEEiAaARoaIMghILIgRReyexdDBdh8HkXKzc7QSB3L4uR45+PRIeb' \
                   b'M7OXrz+3v6O0L8M0BC6KGrAhQWehmYYiGbns0FMmnT0O/I/n2MXtoJKI+igsb8kNicR9GIh0nIlkGz1kDIwq6uRlCoRuFIQ' \
                   b'MRfijSQCKzk0dIitOA0wjpyZI9i/wUF5TIUJMjnQFFUtPZvqLuVBJpic0BTIQAZhJpujRnyQABoAppKlGstK88k4prZnYeW' \
                   b'44aP7pzIMsBKgHdBBjEqhBkXLglHcJdKxiiU3hyhTCUmDjEYsSD5oHARMSALANFBnQbMMQD1m/JJFMOfXhy5JKma4k+jW70' \
                   b'EGWoXb9eAALEAtkhJMR0ZIGXKlmuXq8CjkwCbdu4Ux2/nWt58tzOm9dmPiw6FgkN/jloEC1PKUhFJslCsFKT+TVtlnQYAGG' \
                   b'PhQGyFQznw+H5+fv4lXgIUCYA6PwABijggAQWaOCBCCYoRRAAIfkECQkAIQAsAAAAAKAAFACFBAIEhIKEREJExMLELC4s5O' \
                   b'LkpKakbG5sFBIUVFJU9Pb03NrcNDY0tLa0DA4MlJKUTE5MHBoc/P78vL68BAYEhIaEREZExMbENDI05ObkfH58FBYUXF5c/' \
                   b'Pr83N7cPDo8vLq8/v7+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABv7AkHBILBqPyKRyyWw6n9CodEqtWq/YrHbL7Xq/4GrhwWA8MuG' \
                   b'02qpQLCUXCIUCuUiOHQJgzz901oCBSBITCHsIE3dGHRh8fAR/RAobjo4bkYKZRhIeEwMLioOdn6FFEgmVAAmlIRJ6qQAEoR' \
                   b'KNsHsER5yeoEq6pL2jvEm+wqK7rEQSIBoBGhogyEIdy83P0SC2IEUXtnsXQwXdfB6mINXWSNPMztDp1OzRIerV7Xjv6EcL6' \
                   b'80BC0j6/Jj5M2UIFoJSFsRZGKJB3B4NRfTt0zDQCMB9FSNO7PdvY0YiF/l9HLJsnbMGSEqaRFlEgTg3QyiIozAkocMPRRoE' \
                   b'ZMbSSOvJcz2LqKwWlMjQkymdrUSi0xm/oiRNNoPa4SURmd0c1HQIACeRpkuP3AsQAKqQpgHNhhirQS1btSEFdpw4soMDWw5' \
                   b'KCRAngCFXiCA9zj03UsjFdYVDSAyYeDHiQfdAYCoyj93kIQZsGSgyQNyAIR64kksW+fIQZU6fmRaCmt7qVqUhm5Q8bAEIEA' \
                   b'tes7aN+7UEm44ssHJlS9bpV8WRSeCduxdz3a2eO7/dvDZ16F8kNCjooEG0PKkgtaRkEKam82vaLOkwAMIeCwNWK0DOhwN29' \
                   b'PjzJ/EQoEyA0foFKOCABBZo4IEIJqigEEEAACH5BAkJACEALAAAAACgABQAhQQCBISChERCRMTCxCwuLOTi5KSmpGxubBQSF' \
                   b'FRSVPT29Nza3DQ2NLS2tAwODJSSlExOTBwaHPz+/Ly+vAQGBISGhERGRMTGxDQyNOTm5Hx+fBQWFFxeXPz6/Nze3Dw6PLy6v' \
                   b'P7+/gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAb+wJBwSCwaj8ikcslsOp/QqHRKrVqv2Kx2y+16v+AwsfBgMB4ZsXo9VSiWkguEQoFcJ' \
                   b'McOAcDvHzpsgYJFEhMIfAgTeEYdGH19BIBEChuPjxuSg10SHhMDC4tInJ6gSqOfoYQJlgAJqSESe6wABKESjrN8BEenpUm9r' \
                   b'4SdqKbDvrwgGgEaGiDBQh3Jy83PIdHKzM5HILkgRRe5fBdDBeF9HoQg09RI19PaedLZ1e7zSAvYywEL9/nK/Efw6ftnRMKhW' \
                   b'QhSWTBnYYgGc3w0FMHnD6ARgfksTvS3r9/AjtuYrWuAJJlIZiRDntSQcpK5N0MomKMwZCHED0UaDFTWsojnyZElmWFjGXRlT' \
                   b'yI6TwY4OkQeNqZCnC5j2uElEZnhHNSECAAn0mnToIaQuhRJ0oFipRINyFEjEYoD3Q6Bi01uBwe5HKQSYE6AQ64S37btN1SDX' \
                   b'CEY6xKOK8opiExF6jWDTESCY8pCDOQyUGSAuQFDPHBFV/ly45OPT7/DLMTy0NSiFoAAsYD1EAmyadtunbu2KJuPLLyKlavWb' \
                   b'VnFg+Ge7ftX792wnpuSrumJhAYHHTR4podVpCKUciGAWb28GDdLOgyAwMfCANYKkPfhAN28/ftHPAQwE4A0/v8ABijggAQWa' \
                   b'OCBYAQBACH5BAkJACEALAAAAACgABQAhQQCBISChERCRMTCxCwuLOTi5KSmpGxubBQSFFRSVPT29Nza3DQ2NLS2tAwODJSSl' \
                   b'ExOTBwaHPz+/Ly+vAQGBISGhERGRMTGxDQyNOTm5Hx+fBQWFFxeXPz6/Nze3Dw6PLy6vP7+/gAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'Ab+wJBwSCwaj8ikcslsOp/QqHRKrVqv2Kx2y+16v+AwtfBgMB4ZsXo9VSiWkguEQoFcJMcOAcDvHzpsgYJFEhMIfAgTeEYdG' \
                   b'H19BIBEChuPjxuSg00SHhMDC4tInJ6gSqOfoUenpaoJlgAJqSESe68ABKESjrZ8BKqdqKbArKLDskQSIBoBGhogx0IdyszO0' \
                   b'CHSy83PSNjU20YgvCBFF7x8F0MF5n0ehCDU1dzT2tbd9EgL2cwBC/j6y/2O5NsH0B9BfkYkHLKFIJWFdRaGaFjHR0ORfP8CG' \
                   b'hmoT+PFfwiPKMvWrAGSkSRNimyW8iRLaionrXszhMI6CkMeUvxQpAHuwWUxi4yEF5QISphIfDbbV3TIvGxNhTxlFjXEVA1NO' \
                   b'8wkYtOcg5wUAfAkorTlSmoBAlRVSrAqx30eiWAkGHfI3Gx1hdxlVreDA14OUglYJ0BiWItyQeYNcbfZYo54RT0FkamIPWeVk' \
                   b'U3OPCQZScpHDPAyUGTAugFDPIRtp/kzZyGes4FWtTmJhAUgQCx43Rm3bt6wfe82JZy3BJ2PLMiixQtX51rNj93OPdx2ceLUg' \
                   b'Wu6IqHBQgcNoOl5FakIJV4IaG5fL8bNkg4DIPCxMOC1Auh9OGhnz7//EQ8BmBEAa/4VaOCBCCao4IIMNghFEAAh+QQJCQAhA' \
                   b'CwAAAAAoAAUAIUEAgSEgoREQkTEwsQsLizk4uSkpqRsbmwUEhRUUlT09vTc2tw0NjS0trQMDgyUkpRMTkwcGhz8/vy8vrwEB' \
                   b'gSEhoRERkTExsQ0MjTk5uR8fnwUFhRcXlz8+vzc3tw8Ojy8urz+/v4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAG/sCQcEgsGo/IpHLJb' \
                   b'Dqf0Kh0Sq1ar9isdsvter/gsFhYeDAYj8x4zYYqFEvJBUKhQC6SY4cA6PsPHW2Cg0ISEwh9CBN5Rh0Yfn4EgUQKG5CQG5NsE' \
                   b'h4TAwuMSJyeoEqjn6FHp6VJq6lEEgmXAAmvEnyzAAShEo+5fQSqnaimw6yqIBoBGhogr0MdycvNz0LRyszOSNfT2nrS2dUgv' \
                   b'yBFF799F0MF6H4eRRIg09Tb4PRHC9jLAQtI+fvK+uHTF9AfQX4GASKEhygXglQW2lkYoqFdHw1F8hEUaOSfPo5FkmFj1gCJy' \
                   b'JElj5ycltLISpImmaE0oqAdnCEU2lEYEtHi6IciDQAqaxmS2TyiRIIaHRpz2jKkQ+w9bboUqhCpGqB2sEkkJzoHPC0C+JnUK' \
                   b'UyVIwMEsBrC4z6QRDQChDtELja6Quwuw9t26d5GDn45SCWgnQCKYjHGPcjXLjO+8UaC0FSEWzbKsOxNFqUZ85DI3TyHMPDLQ' \
                   b'JEB7QYM8SD2XWbJokNExrZZ1AIQIBbELnQ7927ZvXWbCv5bAnFRPSFZsIVr1q7PzXM9h3e8VXVC2GE1aOigQbU9zjFX+oXgZ' \
                   b'vbzYN4s6TAAQh8LA0QriN6Hw2/0+PMT8RDgTADX+gUo4IAEFmjggQjmFwQAIfkECQkAIQAsAAAAAKAAFACFBAIEhIKEREJEx' \
                   b'MLELC4s5OLkpKakbG5sFBIUVFJU9Pb03NrcNDY0tLa0DA4MlJKUTE5MHBoc/P78vL68BAYEhIaEREZExMbENDI05ObkfH58F' \
                   b'BYUXF5c/Pr83N7cPDo8vLq8/v7+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABv7AkHBILBqPyKRyyWw6n9CodEqtWq/YrHbL7Xq/4LBYW' \
                   b'ngwGI/MeM2GKhRLyQVCoUAukmOHAOj7Dx1tgoNCEhMIfQgTeUYdGH5+BIFEChuQkBuTVRIeEwMLjEicnqBKo5+hR6elSaupR' \
                   b'q6iCZcACa8SfLQABKESj7p9BKqdqK0gGgEaGiCvQx3HycvNQs/IysxI1dHYetDX0yHa30cgwCBFF8B9F0MF6n4eRRIg0dJIC' \
                   b'9bJAQv3+cj8R/Dp+9dv4L6C+QAaEZgQFiJdCFJZeGdhiIZ3fTQUwedPYZFj1pQ1QAIy5EhyykySTBntpJGSLVcqi1lEwTs4Q' \
                   b'yi8ozBkIuHGD0UaDETmMmg0fUWJeLOWdMjSZE2FPNUQNcTUqlcb3SSiU52DnhgBACUidKZIhPo8EuE4UO0QttbcCoGbTG4Iu' \
                   b'hrs4nXbwQEwB6kEvBNgMazGtf4OqloKQlMRccscE5kXsrEoxpKHUN6WuRDmIwaAGSgy4N2AIR7Cxpv8WdQCECAWdNb8OvbsQ' \
                   b'rVlm8p9O4QE3rth61blE5KFW7lo8dKcXNdyecAJSd/U4KGDBtP2KJdcCRgCnNPDg3mzpMMACH0sDOisoHkfDr3Fy59PxEOAM' \
                   b'wFW09/Pv7///wAGKOAXQQAAIfkECQkAIQAsAAAAAKAAFACFBAIEhIKEREJExMLELC4s5OLkpKakbG5sFBIUVFJU9Pb03NrcN' \
                   b'DY0tLa0DA4MlJKUTE5MHBoc/P78vL68BAYEhIaEREZExMbENDI05ObkfH58FBYUXF5c/Pr83N7cPDo8vLq8/v7+AAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAABv7AkHBILBqPyKRyyWw6n9CodEqtWq/YrHbL7Xq/4LBYXHgwGI/MeM2GKhRLyQVCoUAukmOHAOj7Dx1tg' \
                   b'oNCEhMIfQgTeUYdGH5+BIFEChuQkBuTRRIeEwMLjEicnqBKo5+hR6elSaupRq6mnaiiCZcACa8SfLcABKESj719BLAgGgEaG' \
                   b'iCvQx3HycvNQs/IysxI1dHYetDX0yHa39ne0kcgwyBFF8N9F0MF7X4eRQvWyQELSPb4yPpH/O79MxIQ38B69/ztS5hvYb+Gm' \
                   b'xD1QpDKgjwLQzTI66OhyDFryhog+QhS5DllJUeijGbSCEmWKpXBPCkzpBEF8uAMoSCPwuEQixs/FGkQDV9LjyCTHSVSTqnKo' \
                   b'hqWDmka9WlNqUKoSu2QkwjPdg5+bgQglEhBhQBrJjtoVq0GtkPsJYQrRG4/uiHsWsOrd20jB8McpBIgT0DGsR2JSCgHQlMRc' \
                   b'cscK2YsechikI1FUdaMuXKhzUYMDDNQZIC8AUM8jKW3aQEIEAs8W3YNW3Yh2rFN4bYdQsJu3a9zt/qtCigkC7p43fplWXkv5' \
                   b'oSih5HQQKKDBtP2LJdcaRgCndLDg3mzpMMACH0sDPCswHkfDrzFy59PxEOAMwFY09/Pv7///wAGKOATQQAAIfkECQkAFwAsA' \
                   b'AAAAKAAFACEBAIEnJ6c1NbUREJELC4stLK09PL0vL68DA4MPDo8/Pr8vLq8BAYErK6s3NrcfH58NDI0tLa09Pb0xMLEFBIUP' \
                   b'D48/P78/v7+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABf7gJY5kaZ5oqq5s675wLM90bd94ru987//AoHBILBqFEsPKMqkwG' \
                   b'IOD5UitwiwLCgBAiUxNCsJ2DCAoUBbHYuH4otVs9ym9bqvo8TvcnsLz33VyJn6CIxYDZFsDghZiiVsEhRYFD5UPEWcnChGWl' \
                   b'5lgnJaYKJudo5qhlaegpp8lpaKuJLCqsiIRj1sRJRO5YwcmAp2VDijCw8Unx53JwcMPzSXLltEk08TGz9Uj19BgWrkUcgm+W' \
                   b'wkmqZYFKJTD6yftne8m8ersz/Ml9ZX5JPsP/Ub8CyihHAAJJBgYZEAP3z13D+VFtAfPYUWIFyVmpEiiYDmEIxSWQ2DCgTYUJ' \
                   b'oSRoTx5IiWzlSpbsiw5s4RLaoPAPUIwzuC5V+kW2BJB64FQUkGHXih6FFWnpqwsQQX6VCnToQF8BShxwCCwQXsKkSCkJ1DZP' \
                   b'H3Cnv0zR21as3PIJUrAyNGjSFby6i0xCcEWBAXEhrmrdK/hIwaU3FlQwdyBwocjS55MubLly5gza95cIgQAIfkECQkAEAAsA' \
                   b'AAAAKAAFACEBAIElJaU1NLU9PL0REJEpKak/Pr8rK6sPD48FBIU1NbU9Pb0fH58rKqs/P78tLK0/v7+AAAAAAAAAAAAAAAAA' \
                   b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABf4gJI5kaZ5oqq5s675wLM90bd94ru987//AoHBILBqPq8EAyWwCH' \
                   b'Y8EAJA4OFIOweOhMKiy2+5Xy/ViyeJz2IwCl8dr+Fs9NzkI0zyAcDUZDgyBDAdsJX+Cg4Ukh4KEKIyBjieQiY+AjYojlJJ+l' \
                   b'5GZIpugB3p6BycCiIECKKmqrKiqDLAmroi0JbaCuCS6q62yvCO+s8CvdlKlUwl9JA2yDSjPqtEn04jVJteC2SXbgd3O0NLj1' \
                   b'uXa5yMLynoL6NTk8Oby79jx9vP49dz3/Pn+JNaxm+IulywFxhAhjKVqYa2DCQU5NNgwYqCJvSAyVOgnmTJmnQIFYPAAFAQDD' \
                   b'2VEkjSJUmXJRykZjHw5KeZMljZXwnSJk+dOmTpNBBgYoI2CBw0EmAx1NOnSk02VqjAQ9SlVpFJTXHU6tWpXrFa9TkKgDMFTJ' \
                   b'2jTYimQLEGBZmrjyk2yZK7du3jz6t3Lt6/fv3hDAAA7RUdlR1FOTnV1MlpNRXJFRUNTWTFTTXc3U0diYnV4ejl0aW9mRGhaU' \
                   b'W5WNitjVHJwQTNTYytvb2xUZTdLS2RJQg=='

    main()

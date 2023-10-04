import base64
import datetime
import io
import os

import PIL.Image  # consider from PIL import Image  (PIL.Image)
import PySimpleGUI as sg


class TimeEvent:
    event_counter = 0

    def __init__(self, name, date, author, summary, pic, id=None):
        self.name = name
        self.date = date
        self.author = author
        self.pic = pic
        self.summary = summary
        self.id = id

    def get_name(self):
        return self.name

    def get_date(self):
        return self.date

    def get_author(self):
        return self.author

    def get_pic(self):
        return self.pic

    def get_id(self):
        return self.id

    def get_summary(self):
        return self.summary

    def set_name(self, new_name):
        self.name = new_name

    def set_date(self, new_date):
        self.date = new_date

    def set_pic(self, new_pic):
        self.pic = new_pic

    def set_sum(self, new_sum):
        self.summary = new_sum

    def set_author(self, new_author):
        self.author = new_author

    def set_id(self, new_id):
        self.id = new_id

    def mongoready(self):
        dict = {"name": self.name, "date": self.date, "author": self.author, "summary": self.summary, "pic": self.pic}
        return dict

    def show_event(self, collection, data_struct):
        image_size = (400, 400)
        layout = [
            [sg.T("", size=(20, 1)), sg.T(f"{self.name}", font="FrankRuehl 26 bold underline", justification='center'),
             # sg.T("", size=(5, 1)),
             ],
            [sg.T("", size=(20, 1)), sg.T(f"{self.date}", font="FrankRuehl 18 bold", justification='center'),
             sg.T("", size=(10, 1)), sg.B('edit', size=(5, 3)) ],
            [sg.T("", size=(20, 1)),
             sg.T(f"כותב האירוע: {self.author}", font="FrankRuehl 18 bold", justification='center')],
            [sg.Col([[sg.Image(data=convert_to_bytes(self.pic, image_size), enable_events=True)]]),
             sg.Col([[sg.T(f"תקציר האירוע: {self.summary}")]]),],
            # ADD AN OPTION TO PRESS THE PHOTO AND IT WILL GET BIGGER
            [sg.T("", size=(30, 1)), sg.B("close", size=(5, 2)), ]
        ]

        event_window = sg.Window(f"{self.name}", layout, finalize=True)
        while True:
            wins, events, values = sg.read_all_windows()
            if events in (sg.WIN_CLOSED, None, 'close'):
                break

            if events == 'edit':
                event_window.hide()
                self.edit(collection, data_struct)
                event_window.close()
                return True

        event_window.close()
        return False

    def edit(self, collection, data_struct):
        name = self.name
        date = str(self.date)
        author = self.author
        summary = self.summary
        selfid = self.id
        pic = self.pic
        year = date[:4]
        month = date[5:7]
        day = date[8:10]
        date = day + '-' + month + "-" + year
        ev = add_event(name=name, date=date, author=author, summary=summary, picture=pic, headline=f'Edit {self.name}')
        if not ev:
            return None
        query = {"_id": selfid}
        ev_ready = ev.mongoready()
        collection.update_one(query, {"$set": ev_ready})

        # from here we update the local data structure



        event_day_list = data_struct[year][month][day]
        for ev_idx in range(0, len(event_day_list)):  # --> O(n), while 'n' is the number of events in that exact day
            if event_day_list[ev_idx].get_id() != selfid:
                continue
            else:
                data_struct[year][month][day][ev_idx] = ev
                pass
                return


def delete_event(event_id, collection):  # need to change it. it should be deleted from DB!
    id_query = {"_id": event_id}
    collection.delete_one(id_query)


def image_to_bin(im_path):
    pic1 = open(im_path, 'rb')
    encode_pic = base64.b64encode(pic1.read())
    pic1.close()
    return encode_pic


def add_event(name='', date=None, author='', summary='', picture=None, headline='Add New Event'):
    """
    PySimpleGUI window with browse option to a file, name, author and date.
    the date will be automatically the creation date of the file, and it can be modified"""

    inputs_texts = [[sg.InputText(key="-FILE-", size=(20, 1), readonly=True,),
                     sg.FileBrowse(file_types=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])],
                    [sg.InputText(default_text=name, key="-NAME-", size=(20, 1))],
                    [sg.InputText(default_text=date, key='-DATE-', size=(20, 1), readonly=True),
                     sg.CalendarButton('Calendar', target='-DATE-', format='%d-%m-%Y')],
                    [sg.InputText(default_text=author, key="-AUTHOR-", size=(20, 1))],
                    # [sg.Multiline(key="-SUMMARY-", size=(30, 5), no_scrollbar=True)]
                    ]

    texts = [[sg.T("Image: ", text_color="black")], [sg.T("Event name: ", text_color="black")],
             [sg.T("Date: ", text_color="black")], [sg.T("Author: ", text_color='black')],
             # [sg.T("add context: ", text_color='black')]
             ]

    layout = [
        [sg.T(f"{headline}", text_color='light blue', font='any 30 bold underline')],
        [],
        [sg.Col(texts), sg.Col(inputs_texts)],
        [sg.Col([[sg.T("add context: ", text_color='black'),
                  sg.Multiline(default_text=summary, key="-SUMMARY-", pad=(15, 0), size=(20, 5), no_scrollbar=True)]])],
        [sg.T('', size=(1, 1)), sg.Image(key="-IMAGE-", pad=(0, 0))],
        [sg.T("", key="-BUTTON_OFFSET-"), sg.B("Cancel"), sg.T("           "), sg.B('Submit')]
    ]
    x, y = sg.Window.get_screen_size()
    location = (int(x * 0.4), int(y * 0.2))
    adding_window = sg.Window("Add Event", layout, location=location)
    image_size = (300, 400)
    while True:
        events, values = adding_window.read(timeout=200)
        image_elem = adding_window["-IMAGE-"]
        offset = adding_window["-BUTTON_OFFSET-"]

        if events in (None, "Cancel"):
            adding_window.close()
            return None

        elif events == "Submit":
            print("submit!")
            try:
                if date is None:
                    date = datetime.datetime.strptime(values["-DATE-"], '%d-%m-%Y').date()
                    if date > datetime.date.today():
                        print("undefined date!")
                        sg.popup("WE DONT KNOW THE FUTURE! \ndont pretend to be someone else...",
                                 no_titlebar=True,
                                 font="any 30 bold",
                                 text_color="red",
                                 button_type=5,
                                 background_color="yellow",
                                 auto_close=True, auto_close_duration=1)  # CHANGE IT TO A POPUP WINDOW WITH UNIQUE LAYOUT...
                        continue
            except ValueError:
                print(ValueError)
            date = values["-DATE-"]
            name = values["-NAME-"]
            author = values["-AUTHOR-"]
            summary = values["-SUMMARY-"]
            if picture is None:
                picture = values["-FILE-"]
            if date == '' or name == '' or not picture:
                sg.popup("CAN NOT SUBMIT WITHOUT VALID INFORMATION! \nPlease fill the following:\n--> name\n--> date\n--> picture",
                         no_titlebar=False,
                         font="any 24 bold",
                         text_color="red",
                         button_type=5,
                         background_color="grey",
                         auto_close=True, auto_close_duration=4,
                         title='FALSE INFO')  # CHANGE IT TO A POPUP WINDOW WITH UNIQUE LAYOUT...
                continue
            canon_event = TimeEvent(name, date, author, summary, convert_to_bytes(picture))
            print(f"event {name} has been created locally!")
            adding_window.close()
            return canon_event  # remember to send the event afterwards..

        if values["-FILE-"] != '' and values["-FILE-"]:
            image_elem.update(data=convert_to_bytes(values["-FILE-"], image_size))
            offset.update("                     ")

        if picture is not None:
            image_elem.update(data=convert_to_bytes(picture, image_size))
            offset.update("                     ")
    adding_window.close()


def convert_to_bytes(file_or_bytes, resize=None, form='PNG'):
    '''
    Will convert into bytes and optionally resize an image that is a file or a base64 bytes object.
    Turns into  PNG format in the process so that can be displayed by tkinter
    :param form: input file type
    :param file_or_bytes: either a string filename or a bytes base64 image object
    :type file_or_bytes:  (Union[str, bytes])
    :param resize:  optional new size
    :type resize: (Tuple[int, int] or None)
    :return: (bytes) a byte-string object
    :rtype: (bytes)
    '''
    if isinstance(file_or_bytes, str):
        img = PIL.Image.open(file_or_bytes)
    else:
        try:
            img = PIL.Image.open(io.BytesIO(base64.b64decode(file_or_bytes)))
        except Exception as e:
            dataBytesIO = io.BytesIO(file_or_bytes)
            img = PIL.Image.open(dataBytesIO)

    # f = open("C:/Users/urila/Desktop/hint.txt", 'wb')
    # f.write(img.info["icc_profile"])
    # f.close()
    cur_width, cur_height = img.size
    if resize:
        new_width, new_height = resize
        scale = min(new_height / cur_height, new_width / cur_width)
        # scale = 0.2
        img = img.resize((int(cur_width * scale), int(cur_height * scale)))
    bio = io.BytesIO()
    img.save(bio, format=form)
    del img
    return bio.getvalue()

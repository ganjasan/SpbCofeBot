import requests  
import datetime
from sklearn import neighbors
import numpy as np
import xml.etree.ElementTree as ET
import config
import telebot
import messages

# loader
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

def loadPlacesFromKML(kml_filename):
    tree = ET.parse(kml_filename)
    root = tree.getroot()

    document = root.find("kml:Document", ns)

    folders = document.findall("kml:Folder", ns)

    places = {
        '0': {
            'name': 'Все заведения',
            'list': [],
        },
    }

    places_type_index = 1

    for folder in folders:

        folder_name = folder.find('kml:name',ns).text

        places[str(places_type_index)] = {}
        places[str(places_type_index)]['name'] = folder_name
        places[str(places_type_index)]['list'] = []

        places_in_folder = folder.findall('kml:Placemark', ns)

        for placemark in places_in_folder:
            place = {}
            
            kml_name = placemark.find('kml:name',ns)
            place['name'] = kml_name.text if kml_name is not None else ''

            kml_description = placemark.find('kml:description', ns)
            place['description'] = kml_description.text if kml_description is not None else ''

            point = placemark.find('kml:Point', ns)

            if point is not None:
                kml_coords = point.find('kml:coordinates', ns)
                coords = kml_coords.text.strip().split(',') if kml_coords is not None else [0,0,0]
                place['lat'] = coords[1]
                place['lng'] = coords[0]

            places['0']['list'].append(place)
            places[str(places_type_index)]['list'].append(place)

        places_type_index +=1

    return places


def getKDTrees(places):

    trees = {}

    for place_type_index in places.keys():
        coords = [[i['lat'], i['lng']] for i in places[place_type_index]['list']]
        X = np.array(coords)
        tree = neighbors.KDTree(X, leaf_size=2)

        trees[place_type_index] = tree

    return trees

def getNearestPlacesIndexes(tree, lat, lng, neighbors_k ):

    dist, ind = tree.query([[lat, lng]], k=neighbors_k)

    return ind[0]

bot = telebot.TeleBot(config.token)

places = loadPlacesFromKML(config.places_kml_file)
trees = getKDTrees(places)

def show_main_keyboard(message):
    main_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = telebot.types.KeyboardButton(text="Отправить местоположение", request_location=True)
    main_keyboard.add(button_geo)
    bot.send_message(message.chat.id, 'Отправь мне своё местоположение, или воспользуйся кнопкой ниже, а я поищу интересности рядом с тобой.', reply_markup=main_keyboard)  

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Привет, " + message.from_user.first_name +"!")
    bot.send_message(message.chat.id, messages.repeat_messages['ru']['help'])
    show_main_keyboard(message)

@bot.message_handler(commands=['help'])
def handle_start(message):
    bot.send_message(message.chat.id, messages.repeat_messages['ru']['help'])
    show_main_keyboard(message)


@bot.message_handler(content_types=["text"])
def repeat_all_text_messages(message):
    bot.send_message(message.chat.id, messages.repeat_messages['ru']['no_repeat'])

@bot.message_handler(content_types=["location"])
def send_nearest_places(message):
    location = message.location

    keyboard = telebot.types.InlineKeyboardMarkup()

    for place_type_index in places.keys():
        button = telebot.types.InlineKeyboardButton(text = places[place_type_index]['name'], callback_data = place_type_index + "#" + str(location.latitude) + "#" + str(location.longitude))
        #bot.send_message(message.chat.id, "Все заведения" + "#" + str(59.929065) + "#" + str(30.471106))
        keyboard.add(button)

    bot.send_message(message.chat.id, messages.repeat_messages['ru']['place_type_repeat'], reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):

    data = call.data.split("#")
    place_type_index = data[0]

    lat = data[1]
    lng = data[2]

    bot.send_message(call.message.chat.id, "Ищу " + places[place_type_index]['name'].lower())

    query_k = 5 if len(places[place_type_index]['list']) > 5 else len(places[place_type_index]['list'])
    nearest_places_indexes = getNearestPlacesIndexes(trees[place_type_index], lat , lng, query_k)
    
    for i in nearest_places_indexes:
        nearest_place = places[place_type_index]['list'][i]

        bot.send_message(call.message.chat.id, nearest_place['name'] + '\n' + nearest_place['description'])
        bot.send_location(call.message.chat.id, nearest_place['lat'], nearest_place['lng'])


#main

if __name__ == '__main__':
   bot.polling(none_stop=True)
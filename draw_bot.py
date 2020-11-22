import string
import sys
import time
import webbrowser
from io import BytesIO
from random import choice, randint, shuffle
import argparse

import numpy as np
import requests
import socketio
from bresenham import bresenham

from strokes import *

SETTINGS = {
    'host': 'wss://server3.skribbl.io:5003',
    'join': '',
    'language': 'English',
    'connecting': False
}

USER_DATA = {
    'avatar': [9, 24, 16, -1],
    'code': '',
    'createPrivate': True,
    'join': '',
    'language': 'English',
    'name': 'Skribbl-RNN'
}

GAME_DATA = {'died': False}

COLOR = 1
THICKNESS = 4

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600
HALF_CANVAS_WIDTH = CANVAS_WIDTH / 2
HALF_CANVAS_HEIGHT = CANVAS_HEIGHT / 2

PIXEL_SAMPLE = 5

sio = socketio.Client(logger=False)
"""
Game palette

palette = hitherdither.palette.Palette(
    [0xFFFFFF, 0x000000, 0xC1C1C1, 0x4C4C4C,
     0xEF130B, 0x740B07, 0xFF7100, 0xC23800,
     0xFFE400, 0xE8A200, 0x00CC00, 0x005510,
     0x00B2FF, 0x00569E, 0x231FD3, 0x0E0865,
     0xA300BA, 0x550069, 0xD37CAA, 0xA75574, 
     0xA0522D, 0x63300D]
)
"""


def GenRandomLine(length=8, chars=string.ascii_letters):
    """
    Generate random line
    """
    return ''.join([choice(chars) for i in range(length)])


@sio.on('connect')
def on_connect():
    print('Connection established')


@sio.on('lobbyConnected')
def on_lobbyConnected(data):
    """
    When we connected to the lobby we print out the current round, the number of players, the players names and their score, we also also store that info into GAME_DATA dict
    """
    lobby_url = f"https://skribbl.io/?{data['key']}"
    print(f"Connected to lobby: {lobby_url}")
    if not SETTINGS['join']:
        webbrowser.open(lobby_url)

    # print(f"Round {data['round']} / {data['roundMax']}")
    print(f"There are {len(data['players'])} players : ")
    for player in data['players']:
        print(f"{player['id']} = {player['name']} > {player['score']}")
    GAME_DATA.update({
        'players': {
            player['id']: {
                'name': player['name'],
                'score': player['score'],
                'guessedWord': player['guessedWord']
            }
            for player in data['players']
        }
    })
    GAME_DATA.update({'myID': data['myID']})
    GAME_DATA.update({'round': data['round']})


@sio.on('lobbyCurrentWord')
def on_lobbyCurrentWord(data):
    """
    When lobby updates current word, we want to show that
    """
    print(f"Current word: {data}")


# @sio.on('chat')
# def on_chat(data):
#     """
#     Chat function, prints username or id of user and their message
#     """
#     if 'players' in GAME_DATA.keys():
#         print(f"{GAME_DATA['players'][data['id']]['name']} wrote: {data['message']}")
#     else:
#         print(f"{data['id']} wrote: {data['message']}")


@sio.on('lobbyPlayerConnected')
def on_lobbyPlayerConnected(data):
    """
    When someone enters the lobby, we want to know this, so this is what this function does
    """
    GAME_DATA['players'].update({
        data['id']: {
            'name': data['name'],
            'score': data['score'],
            'guessedWord': data['guessedWord']
        }
    })
    print(f"player connected -> {data['name']}")
    time.sleep(0.5)
    sio.emit("lobbySetDrawTime", "30")
    time.sleep(0.5)
    sio.emit("lobbySetCustomWordsExclusive", True)
    time.sleep(0.5)
    sio.emit("lobbyGameStart", "apple,apple,apple,apple")


@sio.on('lobbyPlayerDisconnected')
def on_lobbyPlayerDisconnected(data):
    """
    When someone leaves the lobby, we want to know this, so this is what this function does
    """
    print(f"player left -> {GAME_DATA['players'][data]['name']}")


@sio.on('lobbyPlayerGuessedWord')
def on_lobbyPlayerGuessedWord(data):
    """
    When someone guesses a word, we want to know it, so this is what this function does
    """
    print(f"{GAME_DATA['players'][data]['name']} guessed the word!")


@sio.on('drawCommands')
def on_drawCommands(data):
    pass


@sio.on('disconnect')
def on_disconnect():
    """
    When we disconnected from server we need explicitly call eio.disconnect or Sio would stuck in forever wait loop
    """
    print('Disconnected from server')
    sio.eio.disconnect(True)


@sio.on('kicked')
def on_kicked():
    """
    The lobby can kick us, we can't do anything about it, at least I have no idea
    """
    print(
        'You either die a hero or you live long enough to see yourself become the villain'
    )
    GAME_DATA['died'] = True


@sio.on('lobbyChooseWord')
def on_lobbyChooseWord(data):
    """
    When the lobby says that someone can choose a word, we check that it is us
    """
    if data['id'] == GAME_DATA["myID"]:
        # We always choose the third word, you can change it the way you want it to work
        GAME_DATA.update({"word": data['words'][2]})
        # print(f"I am drawing {data['words'][2]}")
        sio.emit("lobbyChooseWord", 2)


@sio.on('result')
def on_result(data):
    SETTINGS['host'] = data['host']
    print('Host:', data['host'])
    if SETTINGS['connecting']:
        sio.disconnect()
        SETTINGS['connecting'] = False


def draw_between_points(x1, y1, x2, y2):
    all_points = list(bresenham(x1, y1, x2, y2))
    last_point = all_points[-1]
    all_points = all_points[::PIXEL_SAMPLE]
    all_points.append(last_point)

    for start, end in zip(all_points, all_points[1:]):
        start_x = start[0]
        start_y = start[1]
        end_x = end[0]
        end_y = end[1]

        sio.emit("drawCommands",
                 [[0, COLOR, THICKNESS, start_x, start_y, end_x, end_y]])
        time.sleep(0.005)


@sio.on('lobbyPlayerDrawing')
def on_lobbyPlayerDrawing(data):
    """
    When lobby says that someone is drawing and that one is us, we draw
    """
    if data == GAME_DATA["myID"]:
        print("Starting sketch")
        time.sleep(2)
        draw_strokes(STROKE_A)
    else:
        sio.emit('chat', 'apple')
        time.sleep(1)


def start_server():
    print('Connecting to', SETTINGS['host'])
    sio.connect(SETTINGS['host'])
    sio.emit('userData', USER_DATA)
    sio.wait()


def login():
    sio.connect("https://skribbl.io:4999")
    sio.emit('login', USER_DATA)
    sio.wait()


def get_bounds(data, factor=10):
    """Return bounds of data."""
    min_x = 0
    max_x = 0
    min_y = 0
    max_y = 0

    abs_x = 0
    abs_y = 0
    for i in range(len(data)):
        x = float(data[i, 0]) / factor
        y = float(data[i, 1]) / factor
        abs_x += x
        abs_y += y
        min_x = min(min_x, abs_x)
        min_y = min(min_y, abs_y)
        max_x = max(max_x, abs_x)
        max_y = max(max_y, abs_y)

    return min_x, max_x, min_y, max_y


def draw_strokes(data, factor=0.2, padding=50):
    min_x, max_x, min_y, max_y = get_bounds(data, factor)
    dims = (padding + max_x - min_x, padding + max_y - min_y)
    print('Dimensions:', dims)
    half_width = round(dims[0] / 2.0)
    half_height = round(dims[1] / 2.0)
    scale_width = HALF_CANVAS_WIDTH / half_width
    scale_height = HALF_CANVAS_HEIGHT / half_height

    # Convert relative displacements to absolute local coordinates
    vertices = np.cumsum(data[::, :-1], axis=0) / factor
    pen_states = data[:, -1]

    # Maintain buffer of stroke segments between pen lifts
    buffer = []
    for idx in range(len(vertices)):
        local_x = vertices[idx][0]
        local_y = vertices[idx][1]
        # Convert local coordinates to canvas coordinates
        abs_x = int(round(local_x * scale_width + HALF_CANVAS_WIDTH))
        abs_y = int(round(local_y * scale_height + HALF_CANVAS_HEIGHT))
        # vertices[idx][0] = abs_x
        # vertices[idx][1] = abs_y
        buffer.append((abs_x, abs_y))

        # Pen is lifted
        if pen_states[idx] == 1:
            # Since segments are connected, generate pairwise elements and draw lines between each of them
            pairwise_buffer = list(zip(buffer, buffer[1:]))
            for start, end in pairwise_buffer:
                draw_between_points(start[0], start[1], end[0], end[1])
            buffer = []
            # Pause to simulate pen movement
            time.sleep(0.75)


def runme():
    SETTINGS['connecting'] = True
    login()
    start_server()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Skribbl-RNN')
    parser.add_argument('--join',
                        type=str,
                        default='',
                        help='Private game key')
    args = parser.parse_args()

    SETTINGS['join'] = args.join
    USER_DATA['join'] = args.join
    USER_DATA['createPrivate'] = (args.join == '')

    if args.join != '':
        SETTINGS['connecting'] = True
        login()
    start_server()

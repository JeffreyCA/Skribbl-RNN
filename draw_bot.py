import argparse
import json
import os
import string
import sys
import time
import webbrowser
from io import BytesIO
from random import choice, randint, shuffle
from timeit import default_timer as timer

import numpy as np
import requests
import socketio
import tensorflow.compat.v1 as tf
from bresenham import bresenham

import model as sketch_rnn_model
from sketch_rnn_train import load_checkpoint, load_dataset, reset_graph
from strokes import *
from utils import *

tf.compat.v1.disable_eager_execution()

SETTINGS = {
    'data_dir': 'data',
    'model_dir': 'models/4.0',
    'categories': ['apple', 'bus', 'calculator', 'donut', 'power outlet', 'table'],
    'host': 'wss://server3.skribbl.io:5003',
    'join': '',
    'language': 'English',
    'connecting': False,
    'temperature': 0.01
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
global_sess = None
global_envs = {}


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
    sio.emit("lobbyGameStart", ','.join(SETTINGS['categories']))


@sio.on('lobbyPlayerDisconnected')
def on_lobbyPlayerDisconnected(data):
    """
    When someone leaves the lobby, we want to know this, so this is what this function does
    """
    print(f"Player left: {GAME_DATA['players'][data]['name']}")


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
    print('Disconnected from server')
    sio.eio.disconnect(True)


@sio.on('kicked')
def on_kicked():
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
        # Choose word randomly
        rand_idx = randint(0, len(data['words']) - 1)
        GAME_DATA.update({"word": data['words'][rand_idx]})
        sio.emit("lobbyChooseWord", rand_idx)


@sio.on('result')
def on_result(data):
    SETTINGS['host'] = data['host']
    print('Host:', data['host'])
    if SETTINGS['connecting']:
        sio.disconnect()
        SETTINGS['connecting'] = False


@sio.on('lobbyPlayerDrawing')
def on_lobbyPlayerDrawing(data):
    """
    When lobby says that someone is drawing and that one is us, we draw
    """
    if data == GAME_DATA["myID"]:
        word = GAME_DATA["word"]
        print(f"Starting sketch of {word}")
        if word not in SETTINGS['categories']:
            print(f'{word} is not part of the Sketch-RNN datasets.')
        else:
            strokes = sample_conditional(word)
            draw_strokes(strokes)
    else:
        time.sleep(5)
        sio.emit('chat', 'apple')
        time.sleep(2)
        sio.emit('chat', 'bus')


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
    """Draw strokes (Stroke-3 format) on the Skribbl.io canvas."""
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
        buffer.append((abs_x, abs_y))

        # Pen is lifted
        if pen_states[idx] == 1:
            # Since segments are connected, generate pairwise elements and draw lines between each of them
            # E.g. [A, B, C, D] becomes [(A, B), (B, C), (C, D)]
            pairwise_buffer = list(zip(buffer, buffer[1:]))
            for start, end in pairwise_buffer:
                draw_between_points(start[0], start[1], end[0], end[1])
            buffer = []
            # Pause to simulate pen movement
            time.sleep(0.75)


def draw_between_points(x1, y1, x2, y2):
    """Send draw commands to draw a line from (x1, y1) to (x2, y2)."""
    # Use Bresenham line algorithm to determine the canvas pixels that should be coloured in
    all_points = list(bresenham(x1, y1, x2, y2))
    last_point = all_points[-1]
    # Form line segments by taking every PIXEL_SAMPLEth point
    all_points = all_points[::PIXEL_SAMPLE]
    # Make sure the last point is not left out
    all_points.append(last_point)

    # Loop through pairwise points to form lines segments and send draw commands for each of them
    # E.g. [[x1, y1], [x2, y2], [x3, y3]] becomes [([x1, y1], [x2, y2]), ([x2, y2], [x3, y3])]
    for start, end in zip(all_points, all_points[1:]):
        start_x = start[0]
        start_y = start[1]
        end_x = end[0]
        end_y = end[1]

        sio.emit("drawCommands",
                 [[0, COLOR, THICKNESS, start_x, start_y, end_x, end_y]])
        # Control drawing speed (not very precise for values < 1 second)
        time.sleep(0.005)


def load_env_compatible(data_dir, model_dir, dataset: str, scale: float):
    """Loads environment for inference mode."""
    model_params = sketch_rnn_model.get_default_hparams()
    with tf.gfile.Open(os.path.join(model_dir, 'model_config.json'), 'r') as f:
        data = json.load(f)

    fix_list = [
        'conditional', 'is_training', 'use_input_dropout',
        'use_output_dropout', 'use_recurrent_dropout'
    ]
    for fix in fix_list:
        data[fix] = (data[fix] == 1)

    model_params.parse_json(json.dumps(data))
    model_params.data_set = [dataset + '.npz']
    model_params.scale = scale
    return load_dataset(data_dir, model_params, inference_mode=True)


def init_rnn():
    data_dir = SETTINGS['data_dir']
    model_dir = SETTINGS['model_dir']
    for category in SETTINGS['categories']:
        global_envs[category] = load_env_compatible(data_dir, model_dir,
                                                    category, 1.0)


def sample_conditional(category):
    """Samples a drawing for the given category."""
    def encode(session, eval_model, input_strokes, length):
        strokes = to_big_strokes(input_strokes, length).tolist()
        strokes.insert(0, [0, 0, 1, 0, 0])
        seq_len = [len(input_strokes)]
        return session.run(eval_model.batch_z,
                           feed_dict={
                               eval_model.input_data: [strokes],
                               eval_model.sequence_lengths: seq_len
                           })[0]

    def decode(session,
               eval_model,
               sample_model,
               z_input=None,
               factor=0.2):
        z = None
        if z_input is not None:
            z = [z_input]
        sample_strokes, m = sketch_rnn_model.sample(
            session,
            sample_model,
            seq_len=eval_model.hps.max_seq_len,
            temperature=SETTINGS['temperature'],
            z=z)
        strokes = to_normal_strokes(sample_strokes)
        return strokes

    data_dir, model_dir = SETTINGS['data_dir'], SETTINGS['model_dir']
    [
        train_set, valid_set, test_set, hps_model, eval_hps_model,
        sample_hps_model
    ] = global_envs[category]

    reset_graph()
    model = sketch_rnn_model.Model(hps_model)
    eval_model = sketch_rnn_model.Model(eval_hps_model, reuse=True)
    sampling_model = sketch_rnn_model.Model(sample_hps_model, reuse=True)

    global_sess = tf.InteractiveSession()
    global_sess.run(tf.global_variables_initializer())

    load_checkpoint(global_sess, model_dir)

    strokes_in = test_set.random_sample()
    z = encode(global_sess, eval_model, strokes_in, eval_model.hps.max_seq_len)
    strokes_out = decode(global_sess,
                         eval_model,
                         sampling_model,
                         z)
    return strokes_out


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

    init_rnn()

    if args.join != '':
        SETTINGS['connecting'] = True
        login()
    start_server()

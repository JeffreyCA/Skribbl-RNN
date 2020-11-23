# Skribbl-RNN

Stroke-based Skribbl.io bot, powered by [Sketch-RNN](https://github.com/magenta/magenta/tree/master/magenta/models/sketch_rnn). This was forked from [alekxeyuk/Skribbl.io-Bot](https://github.com/alekxeyuk/Skribbl.io-Bot).

## Dependencies
- `Python 3.4` or higher
- `Asyncio`
- `websockets` [websockets](https://github.com/aaugustin/websockets)
- `aiohttp` [aiohttp](https://github.com/aio-libs/aiohttp/)
- `socketio` [python-socketio](https://github.com/miguelgrinberg/python-socketio)
- `requests` [requests](https://github.com/kennethreitz/requests)
- `pillow` [pillow](https://github.com/python-pillow/Pillow)
- `numpy`

## Installation
1. Clone this repository:
    ```
    git clone https://github.com/JeffreyCA/Skribbl-RNN.git
    ```

2. Create virtual environment:
    ```
    python -m venv env
    ```

3. Activate virtual environment:
    ```
    source env/bin/activate
    ```

4. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

## Usage
To create a new private lobby:
```bash
(env) $ python draw_bot.py
```

To join an existing private lobby:
```bash
(env) $ python draw_bot.py --join <join key>
```

## Configuration
In `draw_bot.py`, you can modify the `SETTINGS` dict:

```python
SETTINGS = {
    # Path to dataset .npz files
    'data_dir': '',
    # Path to Sketch-RNN model/checkpoint files
    'model_dir': '',
    # Names of categories (must match names of .npz in the data_dir)
    'categories': [],
    # Default skribbl.io server host to use for new games
    'host': '',
    # Avatar configuration (must be array of length 4)
    'avatar': [],
    # Bot name
    'name': '',
    # Game language
    'language': '',
    # Sketch-RNN temperature parameter (0 < temp <= 1.0)
    'temperature': 0.01
}
```

## Original License
[MIT](https://github.com/alekxeyuk/Skribbl.io-Bot/blob/master/LICENSE)

"""Local JSON preferences and daily progress. No backend required."""
import json
from datetime import date
from pathlib import Path

PATH = Path.home() / '.anchor_grounding' / 'mobile_preferences.json'
DEFAULT = {
    'onboarded': False, 'needs': [], 'helpful': [], 'avoid': [],
    'guidance': 'Gently, step by step', 'theme': 'Sunrise Warmth',
    'reduced_motion': False, 'sound': True, 'history': {},
}


def load():
    data = {**DEFAULT, 'needs': [], 'helpful': [], 'avoid': [], 'history': {}}
    try:
        saved = json.loads(PATH.read_text(encoding='utf-8'))
        if isinstance(saved, dict):
            for key, default in DEFAULT.items():
                if isinstance(saved.get(key), type(default)):
                    data[key] = saved[key]
    except (OSError, ValueError, TypeError):
        pass
    return data


def save(data):
    try:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = PATH.with_suffix('.tmp')
        temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
        temp.replace(PATH)
    except OSError:
        pass


def record_session(data):
    day = date.today().isoformat()
    data['history'][day] = max(0, int(data['history'].get(day, 0))) + 1
    save(data)

from termcolor import cprint

from openagent.agent.config import config
from openagent.utils import sql
from openagent.utils.popups import CustomPopup, show_popup


class Logger:
    def __init__(self):
        self.log = []

    def add(self, _type, message):
        # Types:
        #  task created
        #  task resumed
        #  task cancelled
        #  task error
        #  task completed
        #  thought
        #  action
        #  observation
        self.log.append((_type, message))

    def print(self):
        for _type, message in self.log:
            print(f'{_type}: {message}')


def insert_log(type, message, print_=True):
    if type == "TASK CREATED":
        pop = show_popup(message=message,
                         backcolor='#8fb7f7',
                         tick_button_func=None,
                         cross_button_func=log_invalid_task_decision)
    try:
        if print_ and config['system']['verbose']: cprint(f'{type}: {message}', 'light_grey')  # print(f'{type}: {message}')
        sql.execute(f"INSERT INTO logs (log_type, message) VALUES (?, ?);", (type, message))

    except Exception as e:
        print('ERROR INSERTING LOG')


def log_invalid_task_decision(popup):
    pass
import time

import openai
from openai import OpenAI
from agentpilot.agent.base import Agent


class OpenAI_Assistant(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = OpenAI()
        self.extra_params = [
            ('Code Interpreter', bool, True),
        ]
        # self.extra_config = {
        #     'assistant.id'
        # }
        self.instance_config = {
            'assistant_id': None,
            'thread_id': None
        }

        self.assistant = None
        self.thread = None

    def load_agent(self):
        super().load_agent()

        # ADD CHECK FOR CHANGED CONFIG, IF INVALID, RECREATE ASSISTANT

        assistant_id = self.config.get('assistant_id', None)
        if assistant_id is not None:
            self.assistant = self.client.beta.assistants.retrieve(assistant_id)
        if self.assistant is None:
            self.assistant = self.create_assistant()

        thread_id = self.config.get('thread_id', None)
        if thread_id is not None:
            self.thread = self.client.beta.threads.retrieve(thread_id)
        if self.thread is None:
            self.thread = self.client.beta.threads.create()

    def create_assistant(self):
        name = self.config.get('general.name', 'Assistant')
        model_name = self.config.get('context.model', 'gpt-3.5-turbo')
        system_msg = self.system_message()

        return openai.beta.assistants.create(
            name=name,
            instructions=system_msg,
            model=model_name,
            tools=[],  # {"type": "code_interpreter"}],
        )

        # # self.update_instance_config('assistant_id', assistant.id)

    # MERGE INTO config
    # - IGNORE INSTANCE PARAMS WHEN update_agent_config IS CALLED
    # - IGNORE AGENT PARAMS WHEN update_instance_config IS CALLED
    # WHEN YOU MODIFY THE PLUGIN CONFIG, IT SHOULD RELOAD THE AGENT

    # def update_instance_config(self, field, value):
    #     self.instance_config['assistant_id'] = value
    #     self.save_config()

    def stream(self, *args, **kwargs):
        messages = kwargs.get('messages', [])
        msg = next((msg for msg in reversed(messages) if msg['role'] == 'user'), None)
        new_msg = self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role=msg['role'],
            content=msg['content'],
        )
        last_msg_id = new_msg.id

        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id
        )

        self.wait_on_run(run, self.thread)

        # Retrieve all the messages added after our last user message
        messages = self.client.beta.threads.messages.list(
            thread_id=self.thread.id, order="asc", after=last_msg_id
        )
        if len(messages.data) == 1:
            yield 'assistant', messages.data[0].content[0].text.value
        elif len(messages.data) > 1:  # can it be?
            # for msg in messages where not the last one
            for msg in messages.data[:-1]:
                msg_content = msg.content[0].text.value
                self.context.save_message('assistant', msg_content)
            yield 'assistant', messages.data[-1].content[0].text.value  # todo - hacky - last msg is saved later
        else:
            yield 'assistant', ''  # can this happen?

    def wait_on_run(self, run, thread):
        while run.status == "queued" or run.status == "in_progress":
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )
            time.sleep(0.5)
        return run

import asyncio
import importlib
import inspect
import json
import os

from agentpilot.utils import sql
from agentpilot.context.member import Member
from agentpilot.context.messages import MessageHistory

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


class Context:
    def __init__(self, main, context_id=None, agent_id=None):
        self.main = main

        self.loop = asyncio.get_event_loop()
        self.responding = False
        self.stop_requested = False

        self.id = context_id
        self.chat_name = ''
        self.chat_title = ''
        self.leaf_id = context_id
        self.context_path = {context_id: None}
        self.members = {}  # {member_id: Member()}
        # self.member_inputs = {}  # {member_id: [input_member_id]}
        self.member_configs = {}  # {member_id: config}
        self.member_outputs = {}

        # self.iterator = SequentialIterator(self)  # 'SEQUENTIAL'  # SEQUENTIAL, RANDOM, REALISTIC
        self.message_history = MessageHistory(self)
        if agent_id is not None:
            context_id = sql.get_scalar("""
                SELECT context_id AS id 
                FROM contexts_members 
                WHERE agent_id = ? 
                  AND context_id IN (
                    SELECT context_id 
                    FROM contexts_members 
                    GROUP BY context_id 
                    HAVING COUNT(agent_id) = 1
                  ) AND del = 0
                ORDER BY context_id DESC 
                LIMIT 1""", (agent_id,))
            if context_id is None:
                pass
                # make new context
            self.id = context_id

        if self.id is None:
            latest_context = sql.get_scalar('SELECT id FROM contexts WHERE parent_id IS NULL ORDER BY id DESC LIMIT 1')
            if latest_context:
                self.id = latest_context
            else:
                # # make new context
                sql.execute("INSERT INTO contexts (id) VALUES (NULL)")
                c_id = sql.get_scalar('SELECT id FROM contexts ORDER BY id DESC LIMIT 1')
                sql.execute("INSERT INTO contexts_members (context_id, agent_id, agent_config) VALUES (?, 0, '{}')", (c_id,))
                self.id = c_id

        self.blocks = {}
        self.roles = {}
        self.models = {}
        self.load()

        if len(self.members) == 0:
            sql.execute("INSERT INTO contexts_members (context_id, agent_id, agent_config) VALUES (?, 0, '{}')", (self.id,))
            self.load_members()

    def load(self):
        self.load_context_settings()
        self.load_members()
        self.message_history.load()

    def load_context_settings(self):
        self.load_blocks()
        self.load_roles()
        self.load_models()
        self.chat_title = sql.get_scalar("SELECT summary FROM contexts WHERE id = ?", (self.id,))

    def load_blocks(self):
        self.blocks = sql.get_results("""
            SELECT
                name,
                text
            FROM blocks""", return_type='dict')

    def load_roles(self):
        self.roles = sql.get_results("""
            SELECT
                name,
                config
            FROM roles""", return_type='dict')
        for k, v in self.roles.items():
            self.roles[k] = json.loads(v)

    def load_models(self):
        self.models = {}
        model_res = sql.get_results("""
            SELECT
                m.model_name,
                m.model_config,
                a.priv_key
            FROM models m
            LEFT JOIN apis a ON m.api_id = a.id""")
        for model_name, model_config, priv_key in model_res:
            if priv_key == '$OPENAI_API_KEY':
                priv_key = os.environ.get("OPENAI_API_KEY", '')
            elif priv_key == '$PERPLEXITYAI_API_KEY':
                priv_key = os.environ.get("PERPLEXITYAI_API_KEY", '')

            model_config = json.loads(model_config)
            if priv_key != '':
                model_config['api_key'] = priv_key

            self.models[model_name] = model_config

    def load_members(self):
        from agentpilot.agent.base import Agent
        # Fetch the participants associated with the context
        context_members = sql.get_results("""
            SELECT 
                cm.id AS member_id,
                cm.agent_id,
                cm.agent_config,
                cm.del
            FROM contexts_members cm
            WHERE cm.context_id = ?
            ORDER BY 
                cm.ordr""",
            params=(self.id,))

        self.members = {}
        self.member_configs = {}
        # self.member_inputs
        unique_members = set()
        for member_id, agent_id, agent_config, deleted in context_members:
            member_config = json.loads(agent_config)
            self.member_configs[member_id] = member_config
            if deleted == 1:
                continue

            # Load participant inputs
            participant_inputs = sql.get_results("""
                SELECT 
                    input_member_id
                FROM contexts_members_inputs
                WHERE member_id = ?""",
                params=(member_id,))

            member_inputs = [row[0] for row in participant_inputs]

            # Instantiate the agent
            use_plugin = member_config.get('general.use_plugin', None)
            kwargs = dict(agent_id=agent_id, member_id=member_id, context=self, wake=True)
            if not use_plugin:
                agent = Agent(**kwargs)
            else:
                agent = next((AC(**kwargs)
                              for AC in importlib.import_module(f"agentpilot.plugins.{use_plugin}.modules.agent_plugin").__dict__.values()
                              if inspect.isclass(AC) and issubclass(AC, Agent) and not AC.__name__ == 'Agent'),
                             None)

            member = Member(self, member_id, agent, member_inputs)
            self.members[member_id] = member
            unique_members.add(agent.name)

        self.chat_name = ', '.join(unique_members)

    def start(self):
        for member in self.members.values():
            member.task = self.loop.create_task(self.run_member(member))

        self.responding = True
        try:
            self.loop.run_until_complete(asyncio.gather(*[m.task for m in self.members.values()]))
        except asyncio.CancelledError:
            pass  # task was cancelled, so we ignore the exception
        except Exception as e:
            self.main.finished_signal.emit()
            raise e

        self.main.finished_signal.emit()

    def stop(self):
        self.stop_requested = True
        for member in self.members.values():
            if member.task is not None:
                member.task.cancel()
        # self.loop.run_until_complete(asyncio.gather(*[m.task for m in self.members.values() if m.task is not None], return_exceptions=True))
        # self.responding = False

    async def run_member(self, member):
        try:
            if member.inputs:
                await asyncio.gather(*[self.members[m_id].task for m_id in member.inputs if m_id in self.members])

            await member.respond()
        except asyncio.CancelledError:
            pass  # task was cancelled, so we ignore the exception
        # except Exception as e:
        #     raise e

    def save_message(self, role, content, member_id=None, log_obj=None):
        if role == 'assistant':
            content = content.strip().strip('"').strip()  # hack to clean up the assistant's messages from FB and DevMode
        elif role == 'output':
            content = 'The code executed without any output' if content.strip() == '' else content

        if content == '':
            return None

        member = self.members.get(member_id, None)
        if member is not None and role == 'assistant':
            member.last_output = content

        return self.message_history.add(role, content, member_id=member_id, log_obj=log_obj)

    def deactivate_all_branches_with_msg(self, msg_id):  # todo - get these into a transaction
        print("CALLED deactivate_all_branches_with_msg: ", msg_id)
        sql.execute("""
            UPDATE contexts
            SET active = 0
            WHERE branch_msg_id = (
                SELECT branch_msg_id
                FROM contexts
                WHERE id = (
                    SELECT context_id
                    FROM contexts_messages
                    WHERE id = ?
                )
            );""", (msg_id,))

    def activate_branch_with_msg(self, msg_id):
        print("CALLED activate_branch_with_msg: ", msg_id)
        sql.execute("""
            UPDATE contexts
            SET active = 1
            WHERE id = (
                SELECT context_id
                FROM contexts_messages
                WHERE id = ?
            );""", (msg_id,))

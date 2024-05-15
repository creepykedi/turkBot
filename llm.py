import os
from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate

load_dotenv()

evaluation_str: str = """Give evaluations based on my answers, in English language(show evaluation subject in response):
        1. User wrote in Turkish - yes or no only.
        2. User was talking about {dialogue_subject} - yes or no only.
        3. Evaluate the user's Turkish grammar on scale from 1 to 10.
        If first is no, score is 0. If second is no, penalize score by 50%, and mention user steered of subject. 
        If score is less than 8, give a hint how to improve it and give at least 1 exact case where user 
        has made a mistake and what it is. If he made several mistakes, walk through all of them.
        Otherwise, say user's language is great and they should keep it up."""


class TurkBot:
    def __init__(
            self,
            openai_key: str = os.getenv("CHAT_API"),
            model_name: str = "gpt-4o",
            temperature: float = .5,
            memory_depth: int = 3,
            dialogue_subject: str = 'Casual'
    ):
        self.dialogue_subject = dialogue_subject
        self.memory_depth = memory_depth
        self.model: ChatOpenAI = self._init_chat_model(openai_key, model_name, temperature)
        self.prompt: ChatPromptTemplate = self._init_prompt()
        self.memory: ConversationBufferWindowMemory = self._init_memory(memory_depth)
        self.bot: LLMChain = self._init_bot()
        self.conversation_ended: bool = False
        self.current_dialogue_length: int = 0

    def _init_chat_model(self,
                         openai_api_key: str,
                         model_name: str,
                         temperature: float
                         ) -> ChatOpenAI:
        self.conversation_ended = False
        model = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=model_name,
            verbose=True,
            temperature=temperature
        )
        return model

    def _init_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
                Your name is Kemal, you're a Turkish AI friend for the user. You need to have conversation with the user
                in TURKISH language only on the subject {dialogue_subject}. You're friendly and polite. Use relatively
                simple language, understandable for medium level Turkish speaker. 
                Reply to the users' messages, ask your own questions within the subject. 
                User will tell you when he wants to end the conversation with words "I decided to end conversation". 
                Once dialogue is finished, do not ask any more questions, 
                instead wrap up conversation with reply to the last message,
                then {evaluation_str}.
                """
                .format(dialogue_subject=self.dialogue_subject, evaluation_str=evaluation_str)
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{inputs}")
        ])
        return prompt

    def _init_memory(self, memory_depth: int) -> ConversationBufferWindowMemory:
        memory = ConversationBufferWindowMemory(
            k=min(max(5, int(memory_depth)), 8),  # store between 5 and 8 last messages
            ai_prefix='AI Turk',
            human_prefix='User',
            llm=self.model,
            memory_key="chat_history",
            input_key='inputs',
            return_messages=True,
        )
        return memory

    def _init_bot(self) -> LLMChain:
        bot = LLMChain(
            llm=self.model,
            prompt=self.prompt,
            memory=self.memory
        )
        self.current_dialogue_length = 0
        return bot

    def end_dialogue(self, last_msg: str | None = None):
        if self.current_dialogue_length > 1:
            evaluation = self.bot.predict(inputs=f"{last_msg if last_msg else ''}"
                                                 f"\nI decided to stop conversation. {evaluation_str}")
        else:
            evaluation = ""
        self.current_dialogue_length = 0
        return evaluation

    def tell(self, user_input: str) -> str:
        if self.conversation_ended:
            return "The conversation has ended. To start a new conversation, please use the /start command."
        if self.current_dialogue_length >= self.memory_depth:
            return self.end_dialogue(user_input)
        answer = self.bot.predict(inputs=user_input)
        self.current_dialogue_length += 1
        return answer

    def show_history(self) -> list:
        return self.memory.buffer

    def __str__(self):
        return f"TurkBot: {self.dialogue_subject}, memory depth: {self.memory_depth}"

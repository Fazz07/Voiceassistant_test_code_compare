import os
import time
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
from langchain.schema import AIMessage

load_dotenv()

class ChatService:
    def __init__(self):
        self.chat = AzureChatOpenAI(
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
            model_name=os.getenv('AZURE_OPENAI_MODEL'),
            openai_api_type=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0,
        )

    async def do_chat(self, question, get_or_create_chat_message_history, session_id, language):
        try:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "You are an Intelligent Assistant"),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{question}"),
                ]
            )
            
            chain = prompt | self.chat
            chain_with_message_history = RunnableWithMessageHistory(
                chain,
                get_or_create_chat_message_history,
                input_messages_key="question",
                history_messages_key="chat_history",
            )
            
            response = chain_with_message_history.invoke(
                {"question": question},
                {"configurable": {"session_id": session_id}}
            )
            
            if hasattr(response, "content"):
                return response.content
            # else:
                # return "It seems like you might be asking how to refer to an ex"
        except Exception as e:
            print(f"Exception in chat: {e}")
            return None

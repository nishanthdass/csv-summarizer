from dotenv import load_dotenv
import os

load_dotenv()

from typing import Annotated
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_core.messages import BaseMessage, HumanMessage
from typing import Literal

# Initialize tools and models
tavily_tool = TavilySearchResults(max_results=5)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

@tool
def translation_tool(
    text: Annotated[str, "The English text to translate to Spanish."],
):
    """Use this tool to translate English text into Spanish."""
    return f"Translation: {llm.predict(text=f'Translate this to Spanish: {text}')}"

def make_system_prompt(suffix: str) -> str:
    return (
        "You are a helpful AI assistant, collaborating with other assistants."
        " Use the provided tools to progress towards answering the question."
        " If you are unable to fully answer, that's OK, another assistant with different tools "
        " will help where you left off. Execute what you can to make progress."
        " If you or any of the other assistants have the final answer or deliverable,"
        " prefix your response with FINAL ANSWER so the team knows to stop."
        f"\n{suffix}"
    )

def get_next_node(last_message: BaseMessage, goto: str):
    if "FINAL ANSWER" in last_message.content:
        return END
    return goto

# Research agent and node
research_agent = create_react_agent(
    llm,
    tools=[tavily_tool],
    state_modifier=make_system_prompt(
        "You can only do research. You are working with a translator colleague."
    ),
)

def research_node(
    state: MessagesState,
) -> Command[Literal["translator", END]]:
    result = research_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "translator")
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content, name="researcher"
    )
    return Command(
        update={
            "messages": result["messages"],
        },
        goto=goto,
    )

# Translator agent and node
translator_agent = create_react_agent(
    llm,
    tools=[translation_tool],
    state_modifier=make_system_prompt(
        "You can only translate English to Spanish. You are working with a researcher colleague."
    ),
)

def translator_node(state: MessagesState) -> Command[Literal["researcher", END]]:
    result = translator_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "researcher")
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content, name="translator"
    )
    return Command(
        update={
            "messages": result["messages"],
        },
        goto=goto,
    )

# State graph setup
from langgraph.graph import StateGraph, START

workflow = StateGraph(MessagesState)
workflow.add_node("researcher", research_node)
workflow.add_node("translator", translator_node)

workflow.add_edge(START, "researcher")
graph = workflow.compile()

# Stream events
events = graph.stream(
    {
        "messages": [
            (
                "user",
                "Translate 'Hello, how are you?' to Spanish.",
            )
        ],
    },
    {"recursion_limit": 150},
)
for s in events:
    print(s)
    print("----")

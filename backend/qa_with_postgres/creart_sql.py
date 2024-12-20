def create_sql_agent(
    llm: BaseLanguageModel,
    toolkit: Optional[SQLDatabaseToolkit] = None,
    agent_type: Optional[
        Union[AgentType, Literal["openai-tools", "tool-calling"]]
    ] = None,
    callback_manager: Optional[BaseCallbackManager] = None,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
    format_instructions: Optional[str] = None,
    input_variables: Optional[List[str]] = None,
    top_k: int = 10,
    max_iterations: Optional[int] = 15,
    max_execution_time: Optional[float] = None,
    early_stopping_method: str = "force",
    verbose: bool = False,
    agent_executor_kwargs: Optional[Dict[str, Any]] = None,
    extra_tools: Sequence[BaseTool] = (),
    *,
    db: Optional[SQLDatabase] = None,
    prompt: Optional[BasePromptTemplate] = None,
    **kwargs: Any,
) -> AgentExecutor:
    """Construct a SQL agent from an LLM and toolkit or database."""
    from langchain.agents import (
        create_openai_functions_agent,
        create_openai_tools_agent,
        create_react_agent,
        create_tool_calling_agent,
    )
    from langchain.agents.agent import (
        AgentExecutor,
        RunnableAgent,
        RunnableMultiActionAgent,
    )
    from langchain.agents.agent_types import AgentType

    if toolkit is None and db is None:
        raise ValueError(
            "Must provide exactly one of 'toolkit' or 'db'. Received neither."
        )
    if toolkit and db:
        raise ValueError(
            "Must provide exactly one of 'toolkit' or 'db'. Received both."
        )
    toolkit = toolkit or SQLDatabaseToolkit(llm=llm, db=db)  # type: ignore[arg-type]
    agent_type = agent_type or AgentType.ZERO_SHOT_REACT_DESCRIPTION
    tools = toolkit.get_tools() + list(extra_tools)
    if prompt is None:
        prefix = prefix or SQL_PREFIX
        prefix = prefix.format(dialect=toolkit.dialect, top_k=top_k)
    else:
        if "top_k" in prompt.input_variables:
            prompt = prompt.partial(top_k=str(top_k))
        if "dialect" in prompt.input_variables:
            prompt = prompt.partial(dialect=toolkit.dialect)
        if any(key in prompt.input_variables for key in ["table_info", "table_names"]):
            db_context = toolkit.get_context()
            if "table_info" in prompt.input_variables:
                prompt = prompt.partial(table_info=db_context["table_info"])
                tools = [
                    tool for tool in tools if not isinstance(tool, InfoSQLDatabaseTool)
                ]
            if "table_names" in prompt.input_variables:
                prompt = prompt.partial(table_names=db_context["table_names"])
                tools = [
                    tool for tool in tools if not isinstance(tool, ListSQLDatabaseTool)
                ]

    if agent_type == AgentType.ZERO_SHOT_REACT_DESCRIPTION:
        if prompt is None:
            from langchain.agents.mrkl import prompt as react_prompt

            format_instructions = (
                format_instructions or react_prompt.FORMAT_INSTRUCTIONS
            )
            template = "\n\n".join(
                [
                    react_prompt.PREFIX,
                    "{tools}",
                    format_instructions,
                    react_prompt.SUFFIX,
                ]
            )
            prompt = PromptTemplate.from_template(template)
        agent = RunnableAgent(
            runnable=create_react_agent(llm, tools, prompt),
            input_keys_arg=["input"],
            return_keys_arg=["output"],
            **kwargs,
        )
    elif agent_type == AgentType.OPENAI_FUNCTIONS:
        if prompt is None:
            messages: List = [
                SystemMessage(content=cast(str, prefix)),
                HumanMessagePromptTemplate.from_template("{input}"),
                AIMessage(content=suffix or SQL_FUNCTIONS_SUFFIX),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
            prompt = ChatPromptTemplate.from_messages(messages)
        agent = RunnableAgent(
            runnable=create_openai_functions_agent(llm, tools, prompt),  # type: ignore
            input_keys_arg=["input"],
            return_keys_arg=["output"],
            **kwargs,
        )
    elif agent_type in ("openai-tools", "tool-calling"):
        if prompt is None:
            messages = [
                SystemMessage(content=cast(str, prefix)),
                HumanMessagePromptTemplate.from_template("{input}"),
                AIMessage(content=suffix or SQL_FUNCTIONS_SUFFIX),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
            prompt = ChatPromptTemplate.from_messages(messages)
        if agent_type == "openai-tools":
            runnable = create_openai_tools_agent(llm, tools, prompt)  # type: ignore
        else:
            runnable = create_tool_calling_agent(llm, tools, prompt)  # type: ignore
        agent = RunnableMultiActionAgent(  # type: ignore[assignment]
            runnable=runnable,
            input_keys_arg=["input"],
            return_keys_arg=["output"],
            **kwargs,
        )

    else:
        raise ValueError(
            f"Agent type {agent_type} not supported at the moment. Must be one of "
            "'tool-calling', 'openai-tools', 'openai-functions', or "
            "'zero-shot-react-description'."
        )

    # Add logic to handle no records found
    def execute_with_no_record_check(*args, **kwargs):
        result = agent.execute(*args, **kwargs)
        if not result:  # Assuming result is a list or similar iterable
            return "No record found"
        return result

    return AgentExecutor(
        name="SQL Agent Executor",
        agent=agent,
        tools=tools,
        callback_manager=callback_manager,
        verbose=verbose,
        max_iterations=max_iterations,
        max_execution_time=max_execution_time,
        early_stopping_method=early_stopping_method,
        execute=execute_with_no_record_check,  # Override the execute method
        **(agent_executor_kwargs or {}),
    )
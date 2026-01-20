import duckdb as db
from sql_ai_agent import prompt_handler as ph
from sql_ai_agent import parse_query as pq
from sql_ai_agent.db_handler import (
    get_tbl_attr,
    query_execute,
    get_character_distinct_values,
)
from sql_ai_agent.sql_validator import (
    SQLValidator,
    ValidationConfig,
    QueryValidationError,
)
from dataclasses import dataclass
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import InMemoryChatMessageHistory

from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)


@dataclass
class QueryOutput:
    success: bool
    validation: bool
    query: str
    data: pd.DataFrame
    error: str


@dataclass
class DebugAttempt:
    query: str
    error: str
    hypothesis: str | None = None


def query_processing(llm_output, con, validator=None, verbose=True):
    """Process LLM output and execute SQL query with validation.

    Args:
        llm_output: Output from LLM containing SQL query
        con: Database connection
        validator: SQLValidator instance for query validation (optional)
        verbose: Whether to print status messages

    Returns:
        QueryOutput with query results or error
    """
    # Extract query from markdown if needed
    if pq.is_markdown_code_chunk(text=llm_output.content):
        query = pq.extract_code_from_markdown(markdown_text=llm_output.content)
    else:
        query = llm_output.content

    # Validate query if validator is provided
    if validator is not None:
        try:
            # Validate query against safety rules
            is_valid, error_msg = validator.validate(query)
            if not is_valid:
                if verbose:
                    print(f"⚠️  Query blocked: {error_msg}")
                return QueryOutput(
                    success=False,
                    validation=False,
                    query=query,
                    data=None,
                    error=f"Validation Error: {error_msg}",
                )

            # Enforce LIMIT if enabled
            if validator.config.enforce_limit:
                original_query = query
                query = validator.enforce_limit(query)
                if query != original_query and verbose:
                    print(
                        f"ℹ️  Query modified to enforce LIMIT: {validator.config.max_limit}"
                    )

        except QueryValidationError as e:
            if verbose:
                print(f"⚠️  Validation error: {str(e)}")
            return QueryOutput(
                success=False,
                validation=False,
                query=query,
                data=None,
                error=f"Validation Error: {str(e)}",
            )

    # Execute query
    try:
        data = query_execute(con=con, query=query)
        success = True
    except Exception as e:
        data = None
        success = False
        error_msg = str(e)

    return QueryOutput(
        success=success,
        validation=True,
        query=query,
        data=data,
        error=error_msg if not success else None,
    )


def sql_agent(
    chain, chat_history, question, tbl_name, db_type, schema, additional_context
):
    llm_output = chain.invoke(
        {
            "question": question,
            "additional_context": additional_context,
            "tbl_name": tbl_name,
            "database": db_type,
            "schema": schema,
            "chat_history": chat_history.messages,
        }
    )
    # Add to history
    chat_history.add_user_message(question)
    chat_history.add_ai_message(llm_output.content)

    return llm_output


def debug_agent(
    chain, question, tbl_name, db_type, schema, query, error_msg, debug_memory
):
    llm_output = chain.invoke(
        {
            "question": question,
            "tbl_name": tbl_name,
            "database": db_type,
            "schema": schema,
            "query": query,
            "error": error_msg,
            "debug_memory": debug_memory,
        }
    )
    return llm_output


class SqlAgent:
    def __init__(
        self,
        api_key,
        base_url,
        model,
        fallback,
        fallback_model,
        con,
        tbl_name,
        temperature=0,
        max_token=5000,
        max_values=50,
        # SQL Validation parameters
        read_only=True,
        max_result_limit=10000,
        enforce_limit=True,
    ):
        """Initialize SQL Agent with LLM and database configuration.

        Args:
            api_key: API key for LLM provider
            base_url: Base URL for LLM API
            model: Model name to use
            fallback: Whether to use fallback model on failure
            fallback_model: Fallback model name
            con: Database connection (ibis connection)
            tbl_name: Table name to query
            temperature: LLM temperature (default: 0)
            max_token: Maximum tokens for LLM response (default: 5000)
            max_values: Max distinct values to fetch for categorical columns (default: 50)
            read_only: Enable read-only mode (only SELECT queries) (default: True)
            max_result_limit: Maximum rows to return from queries (default: 10000)
            enforce_limit: Automatically add/enforce LIMIT clause (default: True)
        """
        self.fallback = fallback
        self.fallback_model = fallback_model
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.tbl_name = tbl_name
        self.max_token = max_token
        self.con = con

        # Initialize SQL validator
        self.validator = SQLValidator(
            ValidationConfig(
                read_only=read_only,
                max_limit=max_result_limit,
                enforce_limit=enforce_limit,
            )
        )

        self.llm = ChatOpenAI(
            base_url=base_url, api_key=api_key, temperature=temperature, model=model
        )

        schema = get_tbl_attr(con=con, tbl_name=tbl_name)
        self.schema = schema.schema
        self.character_distinct_values = get_character_distinct_values(
            con=con, tbl_schema=schema, tbl_name=tbl_name, max_values=max_values
        )
        self.character_distinct_values_reformated = (
            ph.format_distinct_values_for_prompt(self.character_distinct_values)
        )
        self.db_type = schema.db_type
        self.prompt_template = ph.set_prompt_template()
        self.chain = self.prompt_template | self.llm
        self.chat_history = InMemoryChatMessageHistory()

        if fallback:
            self.llm_fallback = ChatOpenAI(
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
                model=self.fallback_model,
            )
            self.fallback_chain = self.prompt_template | self.llm_fallback

        self.debug_prompt_template = ph.debug_prompt_template()
        self.debug_chain = self.debug_prompt_template | self.llm

    def clear_memory(self):
        """Clear the conversation history"""
        self.chat_history.clear()

    def ask_question(
        self,
        question,
        additional_context="",
        distinct_char_values=False,
        verbose=True,
        trials=3,
    ):
        debug_memory: list[DebugAttempt] = []

        if distinct_char_values:
            additional_context = (
                additional_context + "\n" + self.character_distinct_values_reformated
            )

        llm_output = sql_agent(
            chain=self.chain,
            question=question,
            tbl_name=self.tbl_name,
            db_type=self.db_type,
            schema=self.schema,
            additional_context=additional_context,
            chat_history=self.chat_history,
        )
        query = query_processing(
            llm_output=llm_output,
            con=self.con,
            validator=self.validator,
            verbose=verbose,
        )

        # If validation failed in read-only mode, return immediately
        # Don't attempt debug or fallback for security violations
        if not query.validation and self.validator.config.read_only:
            if verbose:
                print(
                    "❌ Query blocked by validator in read-only mode. "
                    "Skipping debug and fallback attempts."
                )
            return query

        if not query.success and query.validation:
            print("Error in the query processing, trying to debug...")
            c = trials
            t = 1
            while c > 0:
                print("Trial: ", t)
                t = t + 1
                print(query.error)
                debug_memory.append(DebugAttempt(query=query.query, error=query.error))

                llm_debug_output = debug_agent(
                    chain=self.debug_chain,
                    question=question,
                    tbl_name=self.tbl_name,
                    db_type=self.db_type,
                    schema=self.schema,
                    query=query.query,
                    error_msg=query.error,
                    debug_memory=debug_memory,
                )

                query = query_processing(
                    llm_output=llm_debug_output,
                    con=self.con,
                    validator=self.validator,
                    verbose=verbose,
                )
                if query.success:
                    c = 0
                else:
                    c = c - 1
        if not query.success and self.fallback and query.validation:
            print("Falling back to the fallback model: ", self.fallback_model)
            llm_fallback_output = sql_agent(
                chain=self.fallback_chain,
                question=question,
                tbl_name=self.tbl_name,
                db_type=self.db_type,
                schema=self.schema,
                additional_context=additional_context,
            )
            query = query_processing(
                llm_output=llm_fallback_output,
                con=self.con,
                validator=self.validator,
                verbose=verbose,
            )

        return query

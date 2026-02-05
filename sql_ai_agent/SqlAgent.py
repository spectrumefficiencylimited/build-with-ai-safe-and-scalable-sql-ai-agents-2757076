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
from sql_ai_agent.skill_manager import SkillManager
from dataclasses import dataclass
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import InMemoryChatMessageHistory

from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
import sqlglot

@dataclass
class QueryOutput:
    success: bool
    validation: bool
    query: str
    data: pd.DataFrame
    error: str
    prompt: str = None  # The full prompt sent to the LLM

    def __repr__(self):
        """Clean string representation for console display."""
        if self.success:
            rows = len(self.data) if self.data is not None else 0
            cols = len(self.data.columns) if self.data is not None else 0
            return f"QueryOutput(success=True, rows={rows}, cols={cols})"
        else:
            error_preview = self.error[:100] + "..." if self.error and len(self.error) > 100 else self.error
            return f"QueryOutput(success=False, error='{error_preview}')"

    def display(self, show_query=True, show_data=True, max_rows=10):
        """Display query results in a clean, readable format.

        Args:
            show_query: Whether to display the SQL query (default: True)
            show_data: Whether to display the result data (default: True)
            max_rows: Maximum rows to display from results (default: 10)
        """
        print("\n" + "=" * 80)

        if not self.validation:
            print("❌ QUERY BLOCKED BY VALIDATOR")
            print("=" * 80)
            print(f"\nReason: {self.error}")
            if show_query:
                # Format SQL query if possible
                try:
                    formatted_query = sqlglot.parse_one(self.query).sql(pretty=True, indent=2)
                except Exception:
                    formatted_query = self.query
                print(f"\nBlocked Query:\n{formatted_query}")
            print("=" * 80)
            return

        if not self.success:
            print("❌ QUERY FAILED")
            print("=" * 80)
            if show_query:
                # Format SQL query if possible
                try:
                    formatted_query = sqlglot.parse_one(self.query).sql(pretty=True, indent=2)
                except Exception:
                    formatted_query = self.query
                print(f"\nQuery:\n{formatted_query}\n")
            print(f"Error: {self.error}")
            print("=" * 80)
            return

        print("✓ QUERY SUCCESSFUL")
        print("=" * 80)

        if show_query:
            # Format SQL query using SqlGlot
            try:
                formatted_query = sqlglot.parse_one(self.query).sql(pretty=True, indent=2)
            except Exception as e:
                # Fallback to original query if formatting fails
                formatted_query = self.query
            print(f"\nSQL Query:\n{formatted_query}\n")

        if show_data and self.data is not None:
            rows = len(self.data)
            print(f"Results ({rows} row{'s' if rows != 1 else ''}):")
            print("-" * 80)

            # Display data
            if rows <= max_rows:
                print(self.data.to_string(index=False))
            else:
                print(self.data.head(max_rows).to_string(index=False))
                print(f"\n... ({rows - max_rows} more rows)")

        print("=" * 80 + "\n")


@dataclass
class DebugAttempt:
    query: str
    error: str
    hypothesis: str | None = None


def query_processing(
    llm_output, con, validator=None, verbose=True, logger=None, prompt=None
):
    """Process LLM output and execute SQL query with validation.

    Args:
        llm_output: Output from LLM containing SQL query
        con: Database connection
        validator: SQLValidator instance for query validation (optional)
        verbose: Whether to print status messages
        logger: SQLAgentLogger instance for structured logging (optional)
        prompt: The full prompt sent to the LLM (optional)

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
                if logger:
                    logger.warning(
                        "Query blocked by validator",
                        extra={
                            "operation_type": "validation",
                            "validation_error": error_msg,
                            "query": query,
                            "read_only": validator.config.read_only,
                        },
                    )
                elif verbose:
                    print(f"⚠️  Query blocked: {error_msg}")
                return QueryOutput(
                    success=False,
                    validation=False,
                    query=query,
                    data=None,
                    error=f"Validation Error: {error_msg}",
                    prompt=prompt,
                )

            # Enforce LIMIT if enabled
            if validator.config.enforce_limit:
                original_query = query
                query = validator.enforce_limit(query)
                if query != original_query:
                    if logger:
                        logger.info(
                            "Query modified to enforce LIMIT",
                            extra={
                                "operation_type": "validation",
                                "original_query": original_query,
                                "modified_query": query,
                                "limit": validator.config.max_limit,
                            },
                        )
                    elif verbose:
                        print(
                            f"ℹ️  Query modified to enforce LIMIT: {validator.config.max_limit}"
                        )

        except QueryValidationError as e:
            if logger:
                logger.warning(
                    "Query validation error",
                    extra={
                        "operation_type": "validation",
                        "error": str(e),
                        "query": query,
                    },
                )
            elif verbose:
                print(f"⚠️  Validation error: {str(e)}")
            return QueryOutput(
                success=False,
                validation=False,
                query=query,
                data=None,
                error=f"Validation Error: {str(e)}",
                prompt=prompt,
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
        prompt=prompt,
    )


def sql_agent(
    chain,
    chat_history,
    question,
    tbl_name,
    db_type,
    schema,
    additional_context,
    use_memory=False,
):
    """Execute SQL agent with optional chat history.

    Args:
        chain: LangChain chain for LLM invocation
        chat_history: InMemoryChatMessageHistory instance
        question: User question
        tbl_name: Table name
        db_type: Database type
        schema: Table schema
        additional_context: Additional context for the query
        use_memory: Whether to use chat history (default: False)

    Returns:
        LLM output
    """
    llm_output = chain.invoke(
        {
            "question": question,
            "additional_context": additional_context,
            "tbl_name": tbl_name,
            "database": db_type,
            "schema": schema,
            "chat_history": chat_history.messages if use_memory else [],
        }
    )

    # Add to history only if memory is enabled
    if use_memory:
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
        # Memory parameters
        memory=False,
        memory_size=10,
        # Logging parameters
        enable_logging=False,
        log_level="INFO",
        log_file=None,
        log_to_console=True,
        log_llm_output=False,
        # Skill parameters
        skill=False,
        skills_dir=None,
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
            memory: Enable conversation memory/chat history (default: False)
            memory_size: Maximum number of message pairs to keep in memory (default: 10)
            enable_logging: Enable structured logging (default: False)
            log_level: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)
            log_file: Path to log file, None for console only (default: None)
            log_to_console: Whether to output logs to console (default: True)
            log_llm_output: Whether to log LLM output content separately from metrics (default: False)
            skill: Enable skill-based context injection (default: False)
            skills_dir: Path to skills directory, None for default location (default: None)
        """
        self.fallback = fallback
        self.fallback_model = fallback_model
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.tbl_name = tbl_name
        self.max_token = max_token
        self.con = con

        # Memory configuration
        self.memory_enabled = memory
        self.memory_size = memory_size
        self.chat_history = InMemoryChatMessageHistory()

        # Initialize logging
        if enable_logging:
            from sql_ai_agent.logger import setup_logging
            from sql_ai_agent.callbacks import LLMMetricsCallback

            self.logger = setup_logging(
                log_level=log_level,
                log_file=log_file,
                console_format="human",
                file_format="json",
                log_to_console=log_to_console,
            )

            # Build agent configuration for callback logging
            agent_config = {
                'model': model,
                'read_only': read_only,
                'enforce_limit': enforce_limit,
                'max_result_limit': max_result_limit,
                'memory_enabled': memory,
                'memory_size': memory_size,
                'skill_enabled': skill,
                'fallback_enabled': fallback,
                'fallback_model': fallback_model if fallback else None,
                'database_type': None,  # Will be set after schema detection
                'table_name': tbl_name,
            }

            # Create LangChain callback for LLM tracking
            self.llm_callback = LLMMetricsCallback(
                logger=self.logger,
                session_id=self.logger.extra["session_id"],
                agent_config=agent_config
            )
        else:
            self.logger = None
            self.llm_callback = None

        # Store logging preferences
        self.log_llm_output = log_llm_output

        # Initialize SQL validator
        self.validator = SQLValidator(
            ValidationConfig(
                read_only=read_only,
                max_limit=max_result_limit,
                enforce_limit=enforce_limit,
            )
        )

        # Create LLM with optional callback
        callbacks = [self.llm_callback] if self.llm_callback else []
        self.llm = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            model=model,
            callbacks=callbacks,
        )

        schema = get_tbl_attr(con=con, tbl_name=tbl_name)
        self.schema = schema.schema
        self.character_distinct_values = get_character_distinct_values(
            con=con, tbl_schema=schema, tbl_name=tbl_name, max_values=max_values
        )
        self.character_distinct_values_reformated = (
            ph.format_distinct_values_for_prompt(self.character_distinct_values)
        )

        # Initialize skill system
        self.skill_enabled = skill
        self.skill_content = None
        if skill:
            skill_manager = SkillManager(skills_dir=skills_dir)
            # Try multiple naming patterns for skill files
            skill_patterns = [
                tbl_name,  # Exact table name
                f"{tbl_name}_context",  # Table name + _context
                f"sfo_{tbl_name}_context",  # SFO prefix (for SFO datasets)
            ]

            skill_loaded = False
            for skill_name in skill_patterns:
                try:
                    self.skill_content = skill_manager.load_skill(skill_name)
                    skill_loaded = True
                    if self.logger:
                        self.logger.info(
                            f"Skill loaded: '{skill_name}'",
                            extra={
                                "operation_type": "skill_loading",
                                "skill_name": skill_name,
                                "skill_size": len(self.skill_content),
                                "table_name": tbl_name,
                            },
                        )
                    break  # Stop trying if skill is found
                except FileNotFoundError:
                    continue  # Try next pattern

            if not skill_loaded:
                # No skill found for any pattern
                if self.logger:
                    self.logger.warning(
                        f"No skill found for table '{tbl_name}' (tried: {', '.join(skill_patterns)})",
                        extra={
                            "operation_type": "skill_loading",
                            "table_name": tbl_name,
                            "patterns_tried": skill_patterns,
                        },
                    )
                else:
                    print(f"⚠️  No skill found for table '{tbl_name}', skill parameter will be ignored")
                self.skill_enabled = False

        self.db_type = schema.db_type

        # Update agent config with database type if logging is enabled
        if self.llm_callback and hasattr(self, 'llm_callback'):
            self.llm_callback.agent_config['database_type'] = self.db_type

        self.prompt_template = ph.set_prompt_template()
        self.chain = self.prompt_template | self.llm

        if fallback:
            self.llm_fallback = ChatOpenAI(
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
                model=self.fallback_model,
                callbacks=callbacks,
            )
            self.fallback_chain = self.prompt_template | self.llm_fallback

        self.debug_prompt_template = ph.debug_prompt_template()
        self.debug_chain = self.debug_prompt_template | self.llm

        # Log successful initialization
        if self.logger:
            self.logger.info(
                "SqlAgent initialized",
                extra={
                    "operation_type": "initialization",
                    "model": model,
                    "fallback_enabled": fallback,
                    "fallback_model": fallback_model if fallback else None,
                    "read_only": read_only,
                    "memory_enabled": memory,
                    "memory_size": memory_size,
                    "table_name": tbl_name,
                    "database_type": self.db_type,
                    "skill_enabled": self.skill_enabled,
                    "skill_loaded": self.skill_content is not None,
                    "log_llm_output": log_llm_output,
                },
            )

    def _trim_memory(self):
        """Trim chat history to keep only the most recent message pairs.

        Keeps the most recent memory_size message pairs (user + assistant).
        A message pair consists of one user message and one assistant response.
        """
        if not self.memory_enabled:
            return

        messages = self.chat_history.messages
        # Each pair is 2 messages (user + assistant)
        max_messages = self.memory_size * 2

        if len(messages) > max_messages:
            # Keep only the most recent messages
            messages_to_keep = messages[-max_messages:]
            self.chat_history.clear()
            for msg in messages_to_keep:
                self.chat_history.add_message(msg)

    def clear_memory(self):
        """Clear the conversation history."""
        self.chat_history.clear()

    def get_memory_info(self):
        """Get information about current memory state.

        Returns:
            dict: Memory statistics including enabled status, size limit,
                current message count, and message pairs count
        """
        message_count = len(self.chat_history.messages)
        pairs_count = message_count // 2

        return {
            "memory_enabled": self.memory_enabled,
            "memory_size_limit": self.memory_size,
            "current_messages": message_count,
            "current_pairs": pairs_count,
            "memory_full": pairs_count >= self.memory_size
            if self.memory_enabled
            else False,
        }

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

        if self.skill_enabled and self.skill_content:
            additional_context = (
                additional_context + "\n" + self.skill_content
            )

        llm_output = sql_agent(
            chain=self.chain,
            question=question,
            tbl_name=self.tbl_name,
            db_type=self.db_type,
            schema=self.schema,
            additional_context=additional_context,
            chat_history=self.chat_history,
            use_memory=self.memory_enabled,
        )

        # Log the LLM output (detailed) - only if log_llm_output is enabled
        if self.logger and self.log_llm_output:
            self.logger.debug(
                "LLM generated SQL query",
                extra={
                    "operation_type": "llm_response",
                    "question": question,
                    "llm_output": llm_output.content,
                    "model": self.model,
                },
            )

        # Trim memory after adding the interaction
        self._trim_memory()

        # Format the prompt for display
        prompt_text = f"""Question: {question}

Table: {self.tbl_name}
Database Type: {self.db_type}
Schema: {self.schema}"""

        if additional_context:
            prompt_text += f"\n\nAdditional Context:\n{additional_context}"

        if self.memory_enabled and self.chat_history.messages:
            prompt_text += (
                f"\n\nChat History: {len(self.chat_history.messages)} messages"
            )

        query = query_processing(
            llm_output=llm_output,
            con=self.con,
            validator=self.validator,
            verbose=verbose,
            logger=self.logger,
            prompt=prompt_text,
        )

        # Log the final result with appropriate level
        if self.logger:
            log_method = self.logger.error if not query.success else self.logger.info
            log_method(
                "Query processing completed" if query.success else "Query processing failed",
                extra={
                    "operation_type": "query_result",
                    "question": question,
                    "query": query.query,
                    "success": query.success,
                    "validation": query.validation,
                    "rows_returned": len(query.data) if query.data is not None else 0,
                    "error": query.error if not query.success else None,
                },
            )

        # If validation failed in read-only mode, return immediately
        # Don't attempt debug or fallback for security violations
        if not query.validation and self.validator.config.read_only:
            if self.logger:
                self.logger.error(
                    "Query blocked in read-only mode",
                    extra={
                        "operation_type": "validation",
                        "reason": "validation_failure",
                        "query": query.query,
                    },
                )
            elif verbose:
                print(
                    "❌ Query blocked by validator in read-only mode. "
                    "Skipping debug and fallback attempts."
                )

            # Display clean output if verbose
            if verbose:
                query.display()

            return query

        if not query.success and query.validation:
            if self.logger:
                self.logger.warning(
                    "Query processing failed, starting debug",
                    extra={
                        "operation_type": "debug",
                        "error": query.error,
                        "trials": trials,
                    },
                )
            elif verbose:
                print("Error in the query processing, trying to debug...")
            c = trials
            t = 1
            while c > 0:
                if self.logger:
                    self.logger.debug(
                        f"Debug trial {t}/{trials}",
                        extra={
                            "operation_type": "debug",
                            "trial_number": t,
                            "total_trials": trials,
                            "error": query.error,
                        },
                    )
                elif verbose:
                    print("Trial: ", t)
                    print(query.error)
                t = t + 1
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

                # Log debug LLM output - only if log_llm_output is enabled
                if self.logger and self.log_llm_output:
                    self.logger.debug(
                        "Debug LLM response",
                        extra={
                            "operation_type": "debug",
                            "trial_number": t - 1,
                            "debug_output": llm_debug_output.content,
                        },
                    )

                # Format debug prompt
                debug_prompt_text = f"""Debug Attempt (Trial {t})

Original Question: {question}
Failed Query: {query.query}
Error: {query.error}

Table: {self.tbl_name}
Database Type: {self.db_type}
Schema: {self.schema}"""

                query = query_processing(
                    llm_output=llm_debug_output,
                    con=self.con,
                    validator=self.validator,
                    verbose=verbose,
                    logger=self.logger,
                    prompt=debug_prompt_text,
                )
                if query.success:
                    c = 0
                else:
                    c = c - 1
        if not query.success and self.fallback and query.validation:
            if self.logger:
                self.logger.warning(
                    "Falling back to fallback model",
                    extra={
                        "operation_type": "fallback",
                        "fallback_model": self.fallback_model,
                        "reason": "query_failure",
                    },
                )
            elif verbose:
                print("Falling back to the fallback model: ", self.fallback_model)
            llm_fallback_output = sql_agent(
                chain=self.fallback_chain,
                question=question,
                tbl_name=self.tbl_name,
                db_type=self.db_type,
                schema=self.schema,
                additional_context=additional_context,
                chat_history=self.chat_history,
                use_memory=False,  # Don't add fallback to memory (it's a retry)
            )

            # Log fallback LLM output - only if log_llm_output is enabled
            if self.logger and self.log_llm_output:
                self.logger.debug(
                    "Fallback LLM response",
                    extra={
                        "operation_type": "fallback",
                        "fallback_model": self.fallback_model,
                        "fallback_output": llm_fallback_output.content,
                    },
                )

            # Format fallback prompt
            fallback_prompt_text = f"""Fallback Model ({self.fallback_model})

Question: {question}

Table: {self.tbl_name}
Database Type: {self.db_type}
Schema: {self.schema}"""

            if additional_context:
                fallback_prompt_text += f"\n\nAdditional Context:\n{additional_context}"

            query = query_processing(
                llm_output=llm_fallback_output,
                con=self.con,
                validator=self.validator,
                verbose=verbose,
                logger=self.logger,
                prompt=fallback_prompt_text,
            )

        # Display clean output if verbose mode is enabled
        if verbose:
            query.display()

        return query

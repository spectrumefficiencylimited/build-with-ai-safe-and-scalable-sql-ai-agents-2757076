import duckdb as db
from sql_ai_agent2 import prompt_handler as ph
from sql_ai_agent2 import parse_query as pq
from sql_ai_agent2.db_handler import get_tbl_attr, query_execute
from dataclasses import dataclass
import pandas as pd
from langchain_openai import ChatOpenAI

from langchain_core.prompts import (
  SystemMessagePromptTemplate,
  HumanMessagePromptTemplate,
  ChatPromptTemplate
)


@dataclass
class QueryOutput:
    success: bool
    query: str
    data: pd.DataFrame
    error: str

@dataclass
class DebugAttempt:
    query: str
    error: str
    hypothesis: str | None = None

def query_processing(llm_output, con):

    if pq.is_markdown_code_chunk(text=llm_output.content):
            query = pq.extract_code_from_markdown(markdown_text=llm_output.content)
    else:
            query = llm_output.content
    try:
        data = query_execute(con = con, query= query)
        success = True
    except Exception as e:
        data = None
        success = False
        error_msg = str(e)
    
    return QueryOutput(
                success =success,
                query=query,
                data = data,
                error = error_msg if not success else None
                )  
def sql_agent(chain, question, tbl_name, db_type, schema, additional_context):
    llm_output = chain.invoke({
                "question": question,
                "additional_context": additional_context,
                "tbl_name": tbl_name,
                "database": db_type,
                "schema": schema
            })
    return llm_output     


def debug_agent(chain, question, tbl_name, db_type, schema, query, error_msg, debug_memory):
    llm_output = chain.invoke({
                "question": question,
                "tbl_name": tbl_name,
                "database": db_type,
                "schema": schema,
                "query": query,
                "error": error_msg,
                "debug_memory": debug_memory

            })
    return llm_output


class SqlAgent2:
    def __init__(self, 
                 api_key, 
                 base_url, 
                 model,
                 fallback,
                 fallback_model, 
                 con,
                 tbl_name, 
                 temperature = 0, 
                 max_token = 5000):
        self.fallback = fallback
        self.fallback_model = fallback_model
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.tbl_name = tbl_name
        self.max_token = max_token
        self.con = con

        self.llm = ChatOpenAI(
            base_url = base_url,
            api_key = api_key,
            temperature = temperature,
            model = model
        )

        

        schema =  get_tbl_attr(con = con, tbl_name = tbl_name) 
        self.schema = schema.schema
        self.db_type = schema.db_type
        self.prompt_template  = ph.set_prompt_template()
        self.chain = self.prompt_template | self.llm

        if fallback:
            self.llm_fallback = ChatOpenAI(
                base_url = base_url,
                api_key = api_key,
                temperature = temperature,
                model = self.fallback_model
            )
            self.fallback_chain = self.prompt_template | self.llm_fallback

        self.debug_prompt_template = ph.debug_prompt_template()
        self.debug_chain = self.debug_prompt_template | self.llm

        

    def ask_question(self, question, additional_context="", verbose=True, trial = 3):
        debug_memory: list[DebugAttempt] = []
        

        llm_output = sql_agent(chain = self.chain, 
                                question = question, 
                                tbl_name = self.tbl_name, 
                                db_type = self.db_type, 
                                schema = self.schema, 
                                additional_context = additional_context)
        query = query_processing(llm_output = llm_output, 
                            con = self.con)
        if not query.success:
            print("Error in the query processing, trying to debug...")
            c = trial
            while c > 0:
                print("Trial: ", c)
                print(query.error)
                debug_memory.append(
                    DebugAttempt(
                        query=query.query,
                        error=query.error)
                )

                llm_debug_output = debug_agent(
                    chain=self.debug_chain,
                    question=question,
                    tbl_name=self.tbl_name,
                    db_type=self.db_type,
                    schema=self.schema,
                    query=query.query,
                    error_msg=query.error,
                    debug_memory=debug_memory
                )
                
                query = query_processing(llm_output = llm_debug_output, 
                            con = self.con)
                if query.success:
                     c = 0
                else:
                     c = c - 1
        if not query.success and self.fallback:
            print("Falling back to the fallback model: ", self.fallback_model)
            llm_fallback_output = sql_agent(chain = self.fallback_chain, 
                                question = question, 
                                tbl_name = self.tbl_name, 
                                db_type = self.db_type, 
                                schema = self.schema, 
                                additional_context = additional_context)
            query = query_processing(llm_output = llm_fallback_output, 
                            con = self.con)
                             

        
        return query
        
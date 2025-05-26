import logging
import time
from functools import wraps
from crewai import Agent, Task
from crewai.project import CrewBase, agent, task
import google.generativeai as genai
from google.generativeai import configure, GenerativeModel, GenerationConfig
from dotenv import load_dotenv
import os
import database as db_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sql_crew.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MacSqlCrew')

def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Starting {func.__name__}")
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Completed {func.__name__} in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

@CrewBase
class MacSqlCrew():
 
    # Load the files from the config directory
    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'
    
    def __init__(self):
        try:
            load_dotenv()
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.error("GOOGLE_API_KEY not found in environment variables")
                raise ValueError("GOOGLE_API_KEY not configured")
            
            # Configure Google AI
            configure(api_key=api_key)
            logger.info("Configured Google AI API")
            
            # Initialize LLM with proper model name and timeout
            self.llm = GenerativeModel(
                model_name="gemini-2.0-flash",
                generation_config=GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            # Test model with timeout
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self.llm.generate_content, "Test connection")
                    response = future.result(timeout=30)  # 30 seconds timeout
                if response and hasattr(response, 'text'):
                    logger.info("LLM model validated successfully")
                else:
                    raise ValueError("Model validation failed - invalid response format")
            except concurrent.futures.TimeoutError:
                logger.error("Model validation timed out")
                raise TimeoutError("Model validation timed out after 30 seconds")
            except Exception as e:
                logger.error(f"Model validation failed: {e}")
                raise

            logger.info("LLM model initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing MacSqlCrew: {str(e)}", exc_info=True)
            raise
            
    @log_execution_time
    def _execute_with_timeout(self, func, *args, timeout=60):
        """Execute a function with timeout"""
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(func, *args)
                return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logger.error(f"Operation timed out after {timeout} seconds")
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

    @log_execution_time
    @agent
    def selector_agent(self) -> Agent:
        logger.info("Creating selector agent")
        a = Agent(
            config=self.agents_config['selector_agent'],
            llm=self.llm,
            allow_delegation=False,
            verbose=True,
            tools=[db_tools.get_tables_from_database]  # Add schema tools
        )
        return a

    @log_execution_time
    @agent
    def decomposer_agent(self) -> Agent:
        logger.info("Creating decomposer agent")
        a = Agent(
            config=self.agents_config['decomposer_agent'],
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )
        return a

    @log_execution_time
    @agent
    def refiner_agent(self) -> Agent:
        logger.info("Creating refiner agent")
        a = Agent(
            config=self.agents_config['refiner_agent'],
            llm=self.llm,
            allow_delegation=False,
            verbose=True
        )
        return a

    @log_execution_time
    @task
    def select_relevant_schema_task(self) -> Task:
        logger.info("Creating schema selection task")
        t = Task(
            config=self.tasks_config['select_relevant_schema_task'],
            agent=self.selector_agent()
        )
        return t
    
    @log_execution_time
    @task
    def select_relevant_column_values(self) -> Task:
        logger.info("Creating column values selection task")
        t = Task(
            config=self.tasks_config['select_relevant_column_values'],
            agent=self.selector_agent(),
            tools=[
                db_tools.get_distinct_column_values,
                db_tools.get_schema_of_given_table
            ]
        )
        return t
    
    @log_execution_time
    @task
    def decompose_question_task(self) -> Task:
        logger.info("Creating question decomposition task")
        t = Task(
            config=self.tasks_config['decompose_question_task'],
            agent=self.decomposer_agent(),
            context=[
                self.select_relevant_schema_task(), 
                self.select_relevant_column_values()
            ]
        )
        return t
    
    @log_execution_time
    @task
    def refine_sql_task(self) -> Task:
        logger.info("Creating SQL refinement task")
        t = Task(
            config=self.tasks_config['refine_sql_task'],
            agent=self.refiner_agent(),
            tools=[
                db_tools.query_database,
                db_tools.get_distinct_column_values
            ],
            context=[
                self.select_relevant_schema_task(), 
                self.select_relevant_column_values(),
                self.decompose_question_task()
            ]
        )
        return t

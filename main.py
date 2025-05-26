from crewai import Crew
from agent import MacSqlCrew
import signal
import sys
import logging
import time

logger = logging.getLogger('MacSqlCrew.main')

def signal_handler(signum, frame):
    logger.error("Operation timed out")
    sys.exit(1)

def main():
    start_time = time.time()
    logger.info("Starting SQL Crew execution")
    
    # Set timeout handler with longer duration
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(600)  # 10 minute timeout
    
    try:
        # Initialize the crew
        sql_crew = MacSqlCrew()
        
        # Define a test question
        question = "What is the name of our customers?"
        logger.info(f"Processing question: {question}")
        
        # Create tasks with the context and timeouts
        tasks = [
            sql_crew.select_relevant_schema_task(),
            sql_crew.select_relevant_column_values(),
            sql_crew.decompose_question_task(),
            sql_crew.refine_sql_task()
        ]
        
        crew = Crew(
            agents=[
                sql_crew.selector_agent(),
                sql_crew.decomposer_agent(),
                sql_crew.refiner_agent()
            ],
            tasks=tasks,
            verbose=True
        )
        
        # Run the crew with timeout and progress tracking
        logger.info("Starting crew execution")
        result = crew.kickoff(
            inputs={'user_question': question},
        )
        
        execution_time = time.time() - start_time
        logger.info(f"Crew execution completed in {execution_time:.2f} seconds")
        print("\nFinal Result:")
        print(result)
        
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Critical error during execution: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        signal.alarm(0)

if __name__ == "__main__":
    main()

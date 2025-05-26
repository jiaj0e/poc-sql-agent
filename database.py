from crewai.tools import tool
from sqlalchemy import text
from util import ENGINE
import re


@tool('query_database')
def query_database(query: str) -> str:
    """Query the PIRLS postgres database and return the results as a string.

    Args:
        query (str): The SQL query to execute.

    Returns:
        str: The results of the query as a string, where each row is separated by a newline.

    Raises:
        Exception: If the query is invalid or encounters an exception during execution.
    """
 
    with ENGINE.connect() as connection:
        try:
            res = connection.execute(text(query))
        except Exception as e:
            return f'Wrong query, encountered exception {e}.'

    max_result_len = 3_000
    ret = '\n'.join(", ".join(map(str, result)) for result in res)
    if len(ret) > max_result_len:
        ret = ret[:max_result_len] + '...\n(results too long. Output truncated.)'
    print(f'Query: {query}\nResult: {ret}')
    return f'Query: {query}\nResult: {ret}'


@tool('get_tables_from_database')
def get_tables_from_database() -> str:
    """
    Retrieves a list of table names from the public schema of the connected database.

    Returns:
        str: A string containing a list of table names, each on a new line in the format:
             (Table: table_name)
             If an error occurs during execution, it returns an error message instead.

    Raises:
        Exception: If there's an error executing the SQL query, the exception is caught
                   and returned as a string message.
    """
    
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    with ENGINE.connect() as connection:
        try:
            res = connection.execute(text(query))
        except Exception as e:
            return f'Wrong query, encountered exception {e}.'
        
    tables = []
    for table in res:
        table = re.findall(r'[a-zA-Z]+', str(table))[0]
        tables.append(f'(Table: {table})\n')
    result = ''.join(tables)
    print(f'Result: {result}')
    return result


@tool('get_schema_of_given_table')
def get_schema_of_given_table(
    table_name: str
) -> str:
    """
    Retrieves the schema information for a given table from the database.

    Args:
        table_name (str): The name of the table for which to retrieve the schema information.

    Returns:
        str: A string containing the schema information, with each column on a new line in the format:
             (Column: column_name, Data Type: data_type)
             If an error occurs during execution, it returns an error message instead.
    """

    query = f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'"
    with ENGINE.connect() as connection:
        try:
            res = connection.execute(text(query))
        except Exception as e:
            return f'Wrong query, encountered exception {e}.'
    
    columns = []
    for column, data_type in res:
        columns.append(f'(Column: {column}, Data Type:{data_type})\n')
    result = ''.join(columns)
    print(f'Result: {result}')
    return result

@tool('get_distinct_column_values')
def get_distinct_column_values(
    table_name: str,
    column: str
) -> str:
    """
    Retrieves distinct values from a specified column in a given table.

    Args:
        table_name (str): The name of the table to query.
        column (str): The name of the column to retrieve distinct values from.

    Returns:
        str: A string containing the distinct values, each formatted as "(Value: <value>)\n".
             If an error occurs during query execution, it returns an error message.
    """
    
    query = f'SELECT DISTINCT {column} FROM {table_name};'
    with ENGINE.connect() as connection:
        try:
            res = connection.execute(text(query))
        except Exception as e:
            return f'Wrong query, encountered exception {e}.'
    
    values = []
    for value in res:
        values.append(f'(Value: {value})\n')
    result = ''.join(values)
    print(f'Result: {result}')
    return result

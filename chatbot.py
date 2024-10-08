from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
import constant
import re

# Load environment variables from a .env file using the 'dotenv' package.
load_dotenv()
preprocessing_location = constant.Location

# Load the API key from the environment variable.
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

class DataRecapper:
    def __init__(self):
        # Initialize the class with default MySQL connection details, which are fetched from environment variables.
        self.username = 'root'
        self.password = os.getenv('PASSWORD')  # MySQL password loaded from environment.
        self.host = os.getenv('HOST')  # MySQL host loaded from environment.
        self.database = os.getenv('DATABASE')  # Database name loaded from environment.
        self.table_name = os.getenv('TABLE_NAME')  # Table name loaded from environment.

        # Initialize the ChatGroq model using the provided API key and a specific model ("llama-3.1-70b-versatile").
        self.llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="llama-3.1-70b-versatile")

        # Define a template for generating SQL queries. This template consists of system and human messages.
        # The system message defines the assistant's role, and the human message provides the user input (prompt).
        self.gen_query_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant that generates only SQL query syntax. The table is named 'data_all' and contains the following attributes: 'STATE', 'CONTAINER', 'TGL. STATUS', 'JML. HARI', 'OWNER', 'BOOKNO', 'LOGISTIC', 'VESSEL TERAKHIR', 'TGL FXD', 'CY BLOCK', 'OPB ID', 'SHIP. TERAKHIR', 'CONS. TERAKHIR', 'CARGO TERAKHIR', 'TYPE', 'LOKASI', 'REMARK', 'FINDING DAMAGE', 'CROSS CHECK', 'MLO FREEUSER', 'USER_ID', 'NO. SEAL', 'CONTAINER GRADE'. Return only the SQL query based on the input, adjusting the date format to match the user input, without any additional explanation or words."
                ),
                (
                    "human", 
                    "input:\n{text}\n Please generate only the SQL query syntax based on the request, and ensure the date format matches the user input (whether it's DD/MM/YYYY or DD-MM-YYYY). Output only the query without redundant explanation or additional text."
                )
            ]


        )

        self.gen_summary_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant that is very proficient at generating a paragraph summary of the information derived from analysis based on a database table containing information about container shipping. "
                    "You must use the Indonesian language; otherwise, you will be punished for not speaking in Indonesian. "
                    "Do not explain abbreviations or acronyms; simply include them as they are. "
                    "Don't forget to format the response using HTML tags such as <p>, <ul>, <li>, etc., so that the display will be neat and attractive on the web."
                ),
                (
                    "human", "{text}\nPlease generate an appealing brief paragraph based on the provided information, formatted in HTML tags such as <p>, <li>, <h1>, etc., so that it can be rendered neatly in a web browser."
                )

            ]
        )

        # Create a chain that will generate SQL queries using the LLM and the prompt template defined above.
        self.generate_query_chain = self.gen_query_template | self.llm
        self.generate_summary_chain = self.gen_summary_template | self.llm

    # This method generates an SQL query by sending the user prompt to the language model (LLM).
    def generate_query(self, prompt):
        # Invoke the query generation chain with the provided prompt and return the SQL query as a response.
        response = self.generate_query_chain.invoke({'text': prompt}).content
        return response
    
    def extract_location(self, user_input):
        # Cek jika user_input adalah salah satu key lokasi (misal: 'BAU', 'JAKARTA', 'AMBON')
        if user_input in preprocessing_location:
            values = preprocessing_location[user_input]
            return ' & '.join([f"'{value}'" for value in values])
        
        # Cek apakah user_input cocok dengan salah satu nama lokasi individual
        for loc, names in preprocessing_location.items():
            for name in names:
                if name in user_input:
                    return f"'{name}'"  # Mengembalikan nama lokasi individual
            # Jika user_input adalah bagian dari key lokasi, kembalikan semua nama yang terkait dengan key
            if loc in user_input:
                return ' & '.join([f"'{name}'" for name in names])
        
        return None

    def extract_date(self, user_input):
        # Regex untuk mencari format tanggal DD/MM/YYYY atau DD-MM-YYYY
        date_pattern = r'\b\d{1,2}/\d{1,2}/\d{4}\b'
        match = re.search(date_pattern, user_input)
        if match:
            return match.group(0)
        return None

    def preprocess_input(self, user_input):
        # Ekstraksi lokasi dan tanggal dari user_input
        location_value = self.extract_location(user_input)
        date_value = self.extract_date(user_input)

        # Cek jika lokasi dan tanggal ditemukan
        if location_value and date_value:
            return f"Tampilkan data di 'LOKASI' = {location_value} dan 'TGL. STATUS' = {date_value}"
        # Cek jika hanya lokasi ditemukan
        elif location_value:
            return f"Tampilkan data di 'LOKASI' = {location_value}"
        # Cek jika hanya tanggal ditemukan
        elif date_value:
            return f"Tampilkan data dengan 'TGL. STATUS' = {date_value}"
        # Jika tidak ada lokasi atau tanggal ditemukan
        return f"tampilkan data di 'LOKASI' = {user_input}"

    def generate_summary(self, text):
        response = self.generate_summary_chain.invoke({'text':text}).content
        return response
    
    def count_per_state(self, table):
        df = pd.DataFrame(table)

        # Group data by relevant columns and get the total counts
        grouped = df.groupby(['STATE', 'TYPE', 'LOKASI', 'CONTAINER GRADE']).size().reset_index(name='count')

        # Menggabungkan data dengan informasi yang serupa
        summary_dict = grouped.groupby(['STATE', 'TYPE', 'CONTAINER GRADE']).agg({
            'count': 'sum', 
            'LOKASI': lambda x: ', '.join(x.unique())
        }).reset_index()

        text = ''
        for entry in summary_dict.to_dict(orient='records'):
            state = entry['STATE']
            type_ = entry['TYPE']
            grade_ = entry['CONTAINER GRADE']
            loc = entry['LOKASI']  # Menggabungkan lokasi yang berbeda dalam satu kalimat
            total_count = entry['count']
            
            # Skip entries where count is 0
            if total_count > 0:
                text += f"Di {loc}, terdapat {total_count} kontainer dengan STATE {state}, TYPE {type_}, dan GRADE {grade_}. "

        return text.strip()  # Remove trailing space at the end


    def merge_pivot_for_display(self, pivot_df):
        # Identify columns that should be "merged"
        cols_to_merge = ['LOKASI']

        # Loop through the columns and replace duplicate values with an empty string
        for col in cols_to_merge:
            pivot_df[col] = pivot_df[col].where(pivot_df[col] != pivot_df[col].shift(), '')
        return pivot_df

                    

    def generate_table(self, sql_query):
        connection = None
        cursor = None
        try:
            # Establish a connection to the MySQL database using the provided credentials.
            connection = mysql.connector.connect(host=self.host,
                                                user=self.username,
                                                password=self.password,
                                                database=self.database)
            if connection.is_connected():
                print('Successfully connected to the database.')

            # Create a cursor object that returns dictionaries instead of tuples.
            cursor = connection.cursor(dictionary=True)

            # Store the generated SQL query.
            Query = sql_query

            # Execute the SQL query.
            cursor.execute(Query)

            # Fetch all rows of the query result as a list of dictionaries.
            result = cursor.fetchall()

            # # Print the result to debug.
            # print(result)

            # If data is found, return the result as a list of dictionaries.
            if result:
                print("Data found. Returning the result as a dictionary...")
                return result
            else:
                print("Data not found.")
                return None

        except mysql.connector.Error as err:
            # Handle any database errors that occur during the execution of the SQL query.
            print(f"Error: {err}")
            return None

        finally:
            # Close the cursor and connection to free resources, regardless of success or failure.
            if cursor:
                cursor.close()
            if connection:
                connection.close()
                print("Connection closed.")
                
    
    
                
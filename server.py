from flask import Flask, request, jsonify, render_template, make_response
from chatbot import DataRecapper
import re
import pandas as pd
import constant

# Initialize Flask application
app = Flask(__name__)

# Create an instance of the DataRecapper class (responsible for generating SQL queries and interacting with the database).
processor = DataRecapper()

pivot_table_global = None

# Define the route for the homepage, which renders an HTML template (index.html).
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gen_query', methods=['POST'])
def generate_sql_query():
    global pivot_table_global  # Use the global pivot table

    # Extract the user message (prompt) from the incoming JSON request.
    user_prompt = request.json.get('userMessage')
    # Print the received user message for debugging
    print(f"Received userMessage: {user_prompt}")

    if not user_prompt:
        return jsonify({'error': 'No user message provided'}), 400

    # Preprocess the user input based on the dictionary
    processed_input = processor.preprocess_input(user_prompt)

    # Process the user input and generate an SQL query using the DataRecapper class.
    print(processed_input)
    response = processor.generate_query(processed_input)
    # Remove markdown formatting like ```sql and ```
    response = response.replace("```sql", "").replace("```", "").strip()
    # Assuming that the processor.generate_query function now returns only valid SQL query.
    if response:
        # Print the SQL query (optional for debugging)
        print(f"SQL_Query: {response}")
        try:
            # Execute the SQL query and get the result from the database.
            table_result = processor.generate_table(response)
            # If there is a result from the SQL query:
            if table_result:
                if len(table_result) == 1:
                    # Jika hanya satu record ditemukan, ambil nilai dari key tersebut.
                    return jsonify({'table_result': table_result[0]['COUNT(CONTAINER)']})

                else:
                    # Create a DataFrame from the list of tuples (table_result).
                    df = pd.DataFrame(table_result)
                    pivot_table = df.pivot_table(index=['LOKASI', 'STATE'], 
                             columns=['TYPE', 'CONTAINER GRADE'],
                             aggfunc='size', 
                             fill_value=0)

                    # Reset the index for easier manipulation
                    pivot_table = pivot_table.reset_index()

                    text_summary = processor.count_per_state(table_result)
                    summary = processor.generate_summary(text_summary)
                    print(text_summary)
                    print(summary)

                    # Apply this function to the pivot_table
                    pivot_table_for_display = processor.merge_pivot_for_display(pivot_table)

                    # Convert the modified DataFrame to HTML
                    table_html = pivot_table_for_display.to_html(index=False, border=1)

                    # Store the pivot table globally for the download route
                    pivot_table_global = pivot_table_for_display

                    csv_url = '/download_pivot'  # URL for downloading the CSV

                    # Send the HTML table back as the JSON response.
                    return jsonify({'table_html': table_html, 'summary': summary, 'csv_url': csv_url})

            return jsonify({'error': 'No results found for the SQL query'}), 404

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # If no valid SQL query is found, return an error message.
    return jsonify({'error': 'No valid SQL query found in the response', 'resp':response}), 400


@app.route('/download_pivot', methods=['GET'])
def download_pivot():
    global pivot_table_global  # Access the globally stored pivot table

    if pivot_table_global is None:
        return jsonify({'error': 'No pivot table available for download.'}), 400

    # Convert the pivot table DataFrame to CSV
    csv_data = pivot_table_global.to_csv(index=False)

    # Create a response to download the CSV file
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=pivot_table.csv"
    response.headers["Content-Type"] = "text/csv"
    
    return response

    

# Run the Flask app in debug mode to allow for easier troubleshooting and development.
if __name__ == '__main__':
    app.run(debug=True)

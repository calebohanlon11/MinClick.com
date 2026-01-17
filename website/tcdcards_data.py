# This file exports the poker members list from the database.
# It creates a CSV file you can download and open in Excel.
# Use it when you want a copy of the members list.
from sqlalchemy import text
import csv
from . import db  # Adjust the import according to your project structure


def export_poker_members_to_csv():
    # Define the file path
    file_path = 'poker_members.csv'

    # Execute the raw SQL query
    with db.engine.connect() as connection:
        result = connection.execute(text('SELECT * FROM poker_members'))

        # Open the CSV file for writing
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)

            # Write the header
            headers = result.keys()  # Get column names
            csv_writer.writerow(headers)

            # Write the data rows
            for row in result:
                csv_writer.writerow(row)

import csv
import mysql.connector
from mysql.connector import Error
import argparse

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "traccar"
}

# CSV file path
CSV_FILE = "Locations3.csv"

def insert_address(cursor, data):
    """
    Inserts a row into the addresses table.
    """
    sql = """
    INSERT INTO addresses (name, latitude, longitude, city, state, country, postal_code, user_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, data)

def main(user_id):
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Read the CSV file
        with open(CSV_FILE, newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                location_parts = row['Location'].split(",")
                if len(location_parts) < 3:
                    location_parts = row['Location'].split("  ")
                name = location_parts[0].strip()[:50]  # Extract the main name
                print(name)
                city = location_parts[1].strip() if len(location_parts) > 1 else None
                state = location_parts[2].strip() if len(location_parts) > 2 else None
                country = "Pakistan"  # Assuming all entries are in Pakistan for this case
                # Map CSV fields to DB columns
                data = (
                    name,                  # name
                    float(row['X']),       # latitude
                    float(row['Y']),       # longitude
                    city,                  # city
                    state,                 # state
                    country,               # country
                    None,                  # postal_code (not provided in CSV)
                    user_id                      # user_id (replace with appropriate value)
                )
                insert_address(cursor, data)

        # Commit the transaction
        connection.commit()
        print("Data inserted successfully.")

    except Error as e:
        print(f"Error: {e}")
        if connection:
            connection.rollback()

    finally:
        # Close the database connection
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insert address data into the database.")
    parser.add_argument("--user_id", type=int, required=True, help="User ID to associate with the data")
    args = parser.parse_args()
    # Call the main function with the user_id parameter
    main(args.user_id)

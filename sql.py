import csv
import mysql.connector
from mysql.connector import Error

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "traccar"
}

# CSV file path
CSV_FILE = "Locations.csv"

def insert_address(cursor, data):
    """
    Inserts a row into the addresses table.
    """
    sql = """
    INSERT INTO addresses (name, latitude, longitude, city, state, country, postal_code, user_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, data)

def main():
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Read the CSV file
        with open(CSV_FILE, newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                print(row)
                # Map CSV fields to DB columns
                data = (
                    row['Location'],            # name
                    float(row['X']),           # latitude
                    float(row['Y']),           # longitude
                    row['City'],               # city
                    row['District'],           # state
                    row['Province'],           # country
                    None,                      # postal_code (not provided in CSV)
                    1                          # user_id (replace with appropriate value)
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
    main()

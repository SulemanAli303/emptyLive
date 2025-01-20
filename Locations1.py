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
CSV_FILE = "Locations1.csv"

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
                name = row['Location'].strip()[:50] if row['Location'] else "Unknown"
                latitude = float(row['X']) if row['X'] else 0.0
                longitude = float(row['Y']) if row['Y'] else 0.0
                city = row['City'].strip() if row['City'] else "Unknown"
                state = row['Province'].strip() if row['Province'] else "Unknown"
                district = row['District'].strip() if row['District'] else "Unknown"
                area = row['Area'].strip() if row['Area'] else "Unknown"
                road = row['Road'].strip() if row['Road'] else "Unknown"
                country = "Pakistan"  # Default country
                postal_code = None  # Not provided in the CSV
                # Map CSV fields to DB columns
                data = (
                    name,          # name (Location)
                    latitude,      # latitude (X)
                    longitude,     # longitude (Y)
                    city,          # city
                    state,         # state
                    country,       # country
                    postal_code,   # postal_code (not in CSV)
                    user_id        # user_id (passed as parameter)
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

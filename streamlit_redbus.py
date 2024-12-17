import streamlit as st
import pandas as pd
import mysql.connector

# List of CSV file paths
csv_files = [
    "andhra_bus_details.csv", "assam_bus_details.csv", "chandigarh_bus_details.csv", 
    "himachal_bus_details.csv", "kadamba_bus_details.csv", "kerala_bus_details.csv",
    "rajasthan_bus_details.csv", "Telangana_bus_details.csv", 
    "up_bus_details.csv", "wb2_bus_details.csv"
]

# Streamlit UI for file upload
st.title("Bus Routes Data Processing")
st.subheader("Upload CSV files containing bus details")

# File uploader for CSVs
uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type="csv")

# If files are uploaded
if uploaded_files:
    df_list = []
    
    # Read the uploaded CSV files
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file)
            df_list.append(df)
            st.write(f"Successfully read {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
    
    # Concatenate DataFrames from uploaded files
    combined_df = pd.concat(df_list, ignore_index=True)
    st.write("Combined DataFrame", combined_df.head())  # Show a preview of the data
    
    # Add ID column
    combined_df['id'] = range(1, len(combined_df) + 1)
    
    # Data Cleaning
    combined_df['Price'] = combined_df['Price'].fillna('').str.replace('INR ', '')
    combined_df['Seat_Availability'] = combined_df['Seat_Availability'].str.extract(r'(\d+)').fillna(0)

    st.write("Cleaned Data", combined_df.head())  # Show cleaned data

    # Streamlit input for service code
    service_code = st.text_input("Enter Service Code (e.g., apsrtc)", value="apsrtc")

    # MySQL connection parameters (to be updated with your database credentials)
    host = 'localhost'
    user = 'root'
    passwd = '123456789'
    database = 'redbus'

    try:
        # MySQL connection
        myconnection = mysql.connector.connect(host=host, user=user, passwd=passwd, database=database)
        cursor = myconnection.cursor()

        # Define service-specific table name
        table_name = f"{service_code}_routes"

        # Create the service-specific table if it doesn't exist
        try:
            cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1")  # Check if table exists
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_NO_SUCH_TABLE:
                st.write(f"Table {table_name} does not exist. Creating it...")
                cursor.execute(f"""
                CREATE TABLE {table_name} (
                    route_id INT AUTO_INCREMENT PRIMARY KEY,
                    route_name VARCHAR(255),
                    route_link VARCHAR(255)
                );
                """)
                st.write(f"Table {table_name} created successfully.")
            else:
                st.error(f"Error: {err}")
                raise

        # Generate MySQL column definitions from DataFrame's dtypes
        columns = []
        for col, dtype in zip(combined_df.columns, combined_df.dtypes):
            if dtype == 'object':
                mysql_dtype = 'TEXT'
            elif dtype == 'int64':
                mysql_dtype = 'INT'
            elif dtype == 'float64':
                mysql_dtype = 'FLOAT'
            elif dtype == 'datetime64[ns]':
                mysql_dtype = 'DATETIME'
            else:
                mysql_dtype = 'TEXT'
            columns.append(f"`{col}` {mysql_dtype}")
        column_definition = ", ".join(columns)

        # Create the main bus_routes table if it doesn't exist
        cursor.execute(f"CREATE TABLE IF NOT EXISTS bus_routes ({column_definition})")

        # Insert data into the bus_routes table (batch insert for performance)
        insert_query = f"INSERT INTO bus_routes ({', '.join(combined_df.columns)}) VALUES (%s, " + ", ".join(["%s"] * (len(combined_df.columns) - 1)) + ")"
        cursor.executemany(insert_query, combined_df.values.tolist())

        # Commit the changes to bus_routes table
        myconnection.commit()

        # Insert data into the service-specific table (only route_name and route_link)
        insert_service_query = f"INSERT INTO {table_name} (route_name, route_link) VALUES (%s, %s)"
        routes_data = combined_df[['route_name', 'route_link']].values.tolist()
        cursor.executemany(insert_service_query, routes_data)

        # Commit the changes to the service-specific table
        myconnection.commit()

        # Close connection
        cursor.close()
        myconnection.close()

        st.success("Data inserted successfully into MySQL database")

    except mysql.connector.Error as e:
        st.error(f"Error with MySQL: {e}")
    
    # Option to download the cleaned data as CSV
    csv_file = combined_df.to_csv(index=False)
    st.download_button(
        label="Download Cleaned Data as CSV",
        data=csv_file,
        file_name="cleaned_bus_routes.csv",
        mime="text/csv"
    )
else:
    st.write("Please upload CSV files to proceed.")

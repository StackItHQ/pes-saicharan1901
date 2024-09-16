import streamlit as st
import mysql.connector
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MySQL configuration using environment variables
mysql_config = {
    'host': os.getenv('MYSQL_HOST'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': 'superjoin'
}

def get_tables():
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def get_table_data(table_name):
    try:
        conn = mysql.connector.connect(**mysql_config)
        query = f"SELECT * FROM `{table_name}`"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

def insert_row(table_name, values):
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        placeholders = ', '.join(['%s'] * len(values))
        sql = f"INSERT INTO `{table_name}` VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Row inserted successfully!")
    except Exception as e:
        st.error(f"Error: {e}")

def update_row(table_name, primary_key, primary_value, values):
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        columns_query = f"SHOW COLUMNS FROM `{table_name}`"
        cursor.execute(columns_query)
        columns = [column[0] for column in cursor.fetchall()]

        update_query = ', '.join([f"{col}=%s" for col in columns])
        sql = f"UPDATE `{table_name}` SET {update_query} WHERE {primary_key} = %s"
        
        # Append primary key value to values for WHERE clause
        cursor.execute(sql, values + [primary_value])
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Row updated successfully!")
    except Exception as e:
        st.error(f"Error: {e}")

# Streamlit app layout
st.title('MySQL Database Editor')

tables = get_tables()
if tables:
    selected_table = st.selectbox('Select a table', tables)

    if selected_table:
        st.write(f"### Data in table: {selected_table}")
        df = get_table_data(selected_table)
        st.dataframe(df)

        # Insert New Row
        st.write(f"### Insert a new row into {selected_table}")
        num_columns = len(df.columns)
        insert_values = [st.text_input(f"Column {i+1} (for insert)") for i in range(num_columns)]
        
        if st.button("Insert Row"):
            insert_row(selected_table, insert_values)

        # Update Existing Row
        st.write(f"### Update an existing row in {selected_table}")
        
        # Select primary key column
        primary_key = st.selectbox("Select the primary key column", df.columns)
        
        # Select the row based on primary key value
        primary_values = df[primary_key].tolist()
        selected_row_value = st.selectbox(f"Select {primary_key} value to update", primary_values)
        
        # Get the current row data based on the selected primary key value
        selected_row = df[df[primary_key] == selected_row_value].iloc[0]
        
        # Display text inputs with pre-filled values from the selected row
        update_values = [st.text_input(f"Update {col}", value=selected_row[col]) for col in df.columns]

        if st.button("Update Row"):
            update_row(selected_table, primary_key, selected_row_value, update_values)

else:
    st.write("No tables found in the database.")

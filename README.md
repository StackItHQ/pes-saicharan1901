[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/AHFn7Vbn)
# Superjoin Hiring Assignment

### Welcome to Superjoin's hiring assignment! 🚀

### Objective
Build a solution that enables real-time synchronization of data between a Google Sheet and a specified database (e.g., MySQL, PostgreSQL). The solution should detect changes in the Google Sheet and update the database accordingly, and vice versa.

### Problem Statement
Many businesses use Google Sheets for collaborative data management and databases for more robust and scalable data storage. However, keeping the data synchronised between Google Sheets and databases is often a manual and error-prone process. Your task is to develop a solution that automates this synchronisation, ensuring that changes in one are reflected in the other in real-time.

### Requirements:
1. Real-time Synchronisation
  - Implement a system that detects changes in Google Sheets and updates the database accordingly.
   - Similarly, detect changes in the database and update the Google Sheet.
  2.	CRUD Operations
   - Ensure the system supports Create, Read, Update, and Delete operations for both Google Sheets and the database.
   - Maintain data consistency across both platforms.
   
### Optional Challenges (This is not mandatory):
1. Conflict Handling
- Develop a strategy to handle conflicts that may arise when changes are made simultaneously in both Google Sheets and the database.
- Provide options for conflict resolution (e.g., last write wins, user-defined rules).
    
2. Scalability: 	
- Ensure the solution can handle large datasets and high-frequency updates without performance degradation.
- Optimize for scalability and efficiency.

## Submission ⏰
The timeline for this submission is: **Next 2 days**

Some things you might want to take care of:
- Make use of git and commit your steps!
- Use good coding practices.
- Write beautiful and readable code. Well-written code is nothing less than a work of art.
- Use semantic variable naming.
- Your code should be organized well in files and folders which is easy to figure out.
- If there is something happening in your code that is not very intuitive, add some comments.
- Add to this README at the bottom explaining your approach (brownie points 😋)
- Use ChatGPT4o/o1/Github Co-pilot, anything that accelerates how you work 💪🏽. 

Make sure you finish the assignment a little earlier than this so you have time to make any final changes.

Once you're done, make sure you **record a video** showing your project working. The video should **NOT** be longer than 120 seconds. While you record the video, tell us about your biggest blocker, and how you overcame it! Don't be shy, talk us through, we'd love that.

We have a checklist at the bottom of this README file, which you should update as your progress with your assignment. It will help us evaluate your project.

- [✔] My code's working just fine! 🥳
- [✔] I have recorded a video showing it working and embedded it in the README ▶️
- [✔] I have tested all the normal working cases 😎
- [✔] I have even solved some edge cases (brownie points) 💪
- [✔] I added my very planned-out approach to the problem at the end of this README 📜

## Got Questions❓
Feel free to check the discussions tab, you might get some help there. Check out that tab before reaching out to us. Also, did you know, the internet is a great place to explore? 😛

We're available at techhiring@superjoin.ai for all queries. 

All the best ✨.

## Developer's Section

# Google Sheets and MySQL Synchronization System

This project implements a system to synchronize data between Google Sheets and a MySQL database using RabbitMQ and Python. The system efficiently ensures that any changes made in either Google Sheets or the MySQL database are mirrored in the other, maintaining consistency across both platforms.

## Approach to the Solution

The system is designed with a **Producer-Consumer** architecture facilitated by RabbitMQ. Here's an overview of each component:

- **Producer**:
  - Handles communication with **Google Sheets** and **MySQL Database**.
  - Detects changes in the Google Sheet or database and publishes relevant messages to the RabbitMQ message queue.
  
- **Consumer**:
  - Listens to RabbitMQ for change notifications.
  - On receiving a message, the consumer processes the change and updates either Google Sheets or the MySQL database accordingly to ensure both platforms stay synchronized.

### Producer

1. **Google Sheets API**:
   - The producer uses the Google Sheets API to interact with Google Sheets. It fetches and pushes data based on updates detected either in Google Sheets or MySQL.
   - Here's a simple example of how the connection works:

     ```python
     import gspread

     # Authenticate and open the Google Sheet
     gc = gspread.service_account(filename='path/to/credentials.json')
     sheet = gc.open('Your Spreadsheet Name').sheet1

     # Fetch all data
     data = sheet.get_all_records()
     ```

2. **MySQL Database**:
   - The MySQL database stores the main data and is synchronized with Google Sheets. The producer also manages this connection and performs CRUD operations.
   - Below is a sample connection setup:

     ```python
     import mysql.connector

     # Connect to MySQL
     conn = mysql.connector.connect(
         host="localhost",
         user="yourusername",
         password="yourpassword",
         database="yourdatabase"
     )
     cursor = conn.cursor()

     # Example query
     cursor.execute("SELECT * FROM your_table")
     rows = cursor.fetchall()
     ```

### Consumer

The **Consumer** uses RabbitMQ to listen for updates sent by the Producer. It ensures data integrity between Google Sheets and MySQL by synchronizing changes whenever a message is received. Below is the core logic for the Consumer:

```python
import pika
import threading
import logging

def process_message(ch, method, properties, body):
    message = body.decode()
    sheet_title, change_type = message.split(':')

    client = get_google_sheets_client()
    connection = get_mysql_connection()
    cursor = connection.cursor()
    spreadsheet = client.open("superjoin")

    if change_type == 'sheet':
        sync_all_sheets_to_db(spreadsheet, cursor)
    elif change_type == 'db':
        sheet = spreadsheet.worksheet(sheet_title)
        sync_db_to_sheet(cursor, sheet)

    connection.commit()

def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.getenv('RABBITMQ_HOST', 'localhost')))
    channel = connection.channel()
    channel.queue_declare(queue='conflict_queue', durable=True)

    def callback(ch, method, properties, body):
        threading.Thread(target=process_message, args=(ch, method, properties, body)).start()

    channel.basic_consume(queue='conflict_queue', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()
```

## Synchronization Process

The synchronization between Google Sheets and MySQL is driven by the following logic:

1. **Change Detection**:
   - Changes are monitored in both Google Sheets and MySQL. When a change occurs, a message is published to the RabbitMQ queue.
   - Changes can be:
     - A new row/record is added.
     - A row/record is updated.
     - A row/record is deleted.

2. **Message Queue (RabbitMQ)**:
   - RabbitMQ acts as the message broker between the Producer and Consumer.
   - The **Producer** publishes a message whenever it detects a change.
   - The **Consumer** listens for messages, processes them, and updates either Google Sheets or MySQL based on the change type.

3. **Consumer Processing**:
   - The Consumer processes the message by reading the change type (Google Sheets or MySQL).
   - Based on the change, it updates the appropriate platform (e.g., syncing the sheet to the database or vice versa).

4. **Concurrency Handling**:
   - The system handles concurrency by spawning a new thread for each incoming message in the RabbitMQ queue. This allows for efficient parallel processing.

## Code Setup

To run the system, you need to set up both the Producer and Consumer. Below are the steps:

1. **Install Dependencies**:
   - Install required Python packages:
   
     ```bash
     pip install gspread mysql-connector-python pika streamlit
     ```

2. **Running the Producer**:
   - To start the producer which detects changes in Google Sheets and MySQL:

     ```bash
     python3 producer.py
     ```

3. **Running the Consumer**:
   - Start the RabbitMQ consumer that listens for changes and synchronizes data:

     ```bash
     python3 consumer.py
     ```

4. **Streamlit Application**:
   - If you want to interact with the MySQL database via a user-friendly interface instead of using the terminal, you can run the `app.py` which uses Streamlit.

     ```bash
     streamlit run app.py
     ```

## Test Folder

The `tests/` folder contains scripts to test the connection between RabbitMQ, Google Sheets API, and MySQL. It also checks whether the synchronization logic is working as expected.

## Handling Edge Cases

The system is designed to handle various scenarios:

1. **New Sheets**:
   - If a new sheet is added to the Google Sheets file, a new table is automatically created in the MySQL database.

2. **Inserts and Updates**:
   - Any new records inserted into Google Sheets are automatically added to MySQL and vice versa.

3. **Conflict Resolution**:
   - If conflicting updates occur, the system ensures the most recent change is synchronized.

## Running the Solution

1. **Start RabbitMQ**:
   - Ensure that RabbitMQ is running on your machine. You can start it using Docker:

     ```bash
     docker run -d --hostname my-rabbit --name rabbitmq -p 5672:5672 rabbitmq:3-management
     ```

2. **Start Producer and Consumer**:
   - Run the producer to detect changes and the consumer to synchronize data between Google Sheets and MySQL.

     ```bash
     python3 producer.py
     python3 consumer.py
     ```

3. **Make Changes**:
   - Any changes made to either Google Sheets or MySQL will be automatically detected and synchronized.

## Demo Video

For a visual demonstration of how the system works, watch the [Video Solution](/assets/solution.mp4).

## Architecture Diagram

Below is an architecture diagram that outlines how the components interact with each other:

![Architecture Diagram](/assets/architecture.png)

## Conclusion

This system provides a robust solution to keep data synchronized between Google Sheets and a MySQL database. By leveraging RabbitMQ for message queuing and Python for handling API interactions, the system ensures that updates made in one platform are reliably reflected in the other. The architecture is scalable and can handle large datasets with ease, making it suitable for enterprise applications.


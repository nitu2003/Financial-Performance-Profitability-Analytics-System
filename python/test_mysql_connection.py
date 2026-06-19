import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="ronit2727",
    database="financial_analytics"
)

print("Connected successfully!")

conn.close()
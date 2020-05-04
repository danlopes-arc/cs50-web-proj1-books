from sqlalchemy import create_engine
from sqlalchemy.sql import text
import csv

engine = create_engine("postgres://wrsgwrmkrvjnkg:315f2ff023c1d9b3d063fbd2c8c0ec20fe50daae75d8c89525821bfc7c088ffb@ec2-54-88-130-244.compute-1.amazonaws.com:5432/dde9dia2t0hl7o")

con = engine.connect()

with open("books.csv") as file:
  reader = csv.DictReader(file)
  for row in reader:
    statement = text("INSERT INTO books(isbn, title, author, year) VALUES(:isbn, :title, :author, :year);")
    
    data = {"isbn": row["isbn"], "title": row["title"], "author": row["author"], "year": row["year"]}

    con.execute(statement, data)

con.close()
engine.dispose()
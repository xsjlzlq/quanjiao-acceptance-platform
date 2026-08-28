import psycopg2
con = psycopg2.connect(dbname='quanjiao', user='postgres', password='123456', host='localhost', port='5432')
cursor = con.cursor()
cursor.execute("SELECT COUNT(*) FROM cbf WHERE cbfbm LIKE '34112410000801%'")
print(cursor.fetchone()[0])

from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')

db = client['Humidity']
users = db['Users']
Board_1 = db['Board_1']    
Board_2 = db['Board_2']
Board_3 = db["Board_3"]
setting= db['Setting']



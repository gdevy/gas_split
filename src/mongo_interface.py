import os

import dotenv
import pymongo as pymongo

dotenv.load_dotenv()

db_client = pymongo.MongoClient(
    f"mongodb+srv://{os.getenv('mongodb_user')}:{os.getenv('mongodb_pass')}"
    f"@cluster0.tb3xo.mongodb.net/Cluster0?retryWrites=true&w=majority")['gas_split']

db_client.command('serverStatus')

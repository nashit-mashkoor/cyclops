from datetime import datetime

import utils
from envs import env
from .miDatabase.database import Database as MiDatabase
from .telemetryDatabase.database import Database as TelemetryDatabase
from tqdm import tqdm

def seed_telemetry_db():
    print("Logging data to telemetry db")
    telemetry_database = TelemetryDatabase.get_instance()
    payload_1 = [['10000', '6029', '1000000', '69640', '170551', '7210', '131457', '1804', '1000000', '33106', '1000000', '1000000', '1000000', '18166', '680932', '6199', '807637', '1000000', '287683',
                '83686', '7004', '731640', '166646', '60706', '1000000', '44448', '22196', '424778', '7314', '1000000', '1000000', '717638', '68016', '27.51', '43.36', '100276_9646_0702707', '2022-11-04T14:12:54+0000']
                 ]* 500
    print("Saving payload 1")
    for id, p in enumerate(tqdm(payload_1)):
        current_time = datetime.now()
        p[-1] = current_time.strftime("%Y-%m-%dT%H:%M:%S+0000")
        telemetry_database.write(p)
        telemetry_database.update_log_sent_mqtt(id, True)

    payload_2 = [['4000', '6129', '1000000', '69940', '170551', '7210', '131457', '1804', '1000000', '33106', '1000000', '1000000', '1000000', '17166', '580932', '6299', '907637', '1000000', '187683',
                '83686', '6004', '731640', '166646', '60106', '1000000', '42448', '12296', '134778', '8314', '1000000', '1000000', '717638', '61016', '37.51', '33.36', '100276_9646_0702707', '2022-11-04T14:12:54+0000']
                 ]* 200
    print("Saving payload 2")
    for p in tqdm(payload_2):
        current_time = datetime.now()
        p[-1] = current_time.strftime("%Y-%m-%dT%H:%M:%S+0000")
        telemetry_database.write(p)




def seed_mi_db():
    print("Logging data to mi db")
    mi_database = MiDatabase.get_instance()

    config = utils.load_config()
    supported_analytes = config['supported_analytes']

    print("Saving predictions for Log ID 350 - 550")
    results_1 = {analyte: 0.5 for analyte in supported_analytes}

    for i in tqdm(range(250, 350)):
        mi_database.save_prediction(
            i, results_1, datetime.now())

    print("Saving predictions for Log ID 550 - 650")
    results_2 = {analyte: 1.0 for analyte in supported_analytes}
    for i in tqdm(range(550, 65000)):
        mi_database.save_prediction(
            i, results_2, datetime.now())

    print("Updating predictions id mqtt boolean from prediction Id 1002 - 1400")
    for i in tqdm(range(1002, 1401)):
        mi_database.update_sent_mqtt_predictions(i, True)


if __name__ == "__main__":
    seed_telemetry_db()
    seed_mi_db()

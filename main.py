from flask import Flask, jsonify, request
import meal
import datetime

from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
meal_db = meal.meal

@app.route('/', methods=["GET"])
def home():
    if (since_str:=request.args.get("since")) == None:
        return jsonify(meal_db.meals)
    else:
        if since_str == "today":
            since = datetime.datetime.now(tz=meal.KST).date()
        else:
            since = meal.text2date(since_str)
        return jsonify(meal_db.getSince(since))

@app.route('/beautify', methods=["GET"])
def beautify():
    if (since_str:=request.args.get("since")) == None:
        return str(meal_db).replace("\n", "<br>").replace(" ", "&nbsp"), 200
    else:
        if since_str == "today":
            since = datetime.datetime.now(tz=meal.KST).date()
        else:
            since = meal.text2date(since_str)
        return meal_db.meal_dict2str(meal_db.getSince(since)).replace("\n", "<br>").replace(" ", "&nbsp"), 200

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=meal.data_syncer.sync, trigger='interval', hours=1)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    app.run(host='0.0.0.0', port=5000)
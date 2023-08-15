import requests
import pandas as pd
import os
import json
from time import sleep
from datetime import datetime, timedelta
from io import StringIO
import boto3
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from dotenv import load_dotenv
load_dotenv()

s = requests.Session()
retries = Retry(total=5,
                backoff_factor=3,
                status_forcelist=[429, 500, 502, 503, 504])
s.mount('https://', HTTPAdapter(max_retries=retries))
base_url = "https://api.open.fec.gov/v1/"
headers = {
    "Content-Type": "application/json",
    "X-Api-Key": os.getenv("FEC_API_KEY")
}

def parse_data(data):
    res = data["results"]
    flatten = []
    for i in res:
        for j in i:
            flatten.append(j)
    df = pd.json_normalize(flatten)
    return df

def write_data(df, min_date, max_date):
    client = boto3.client('s3')
    date = datetime.now()
    min_key = "".join(min_date.split("/"))
    max_key = "".join(max_date.split("/"))
    key = f"{date.strftime('%Y')}/ \
            schedule-a-{min_key}-{max_key}.csv"
    buffer = StringIO()
    df.to_csv(buffer)
    client.put_object(
        Body=buffer.getvalue(),
        Key=key,
        Bucket=os.getenv("BUCKET_NAME")
    )

def update_params(params, pagination_params):
    params["last_index"] = pagination_params["last_indexes"]["last_index"]
    last_contrib = pagination_params["last_indexes"]["last_contribution_receipt_date"]
    if last_contrib is not None:
        params["last_contribution_receipt_date"] = last_contrib
    else:
        params["sort_null_only"] = True
    return params


def paginate_results(data, url, params):
    all_data = []
    all_data.append(data)
    p = 0
    new_params = params
    last_call = data
    while last_call["pagination"]["last_indexes"]:
        print("params", new_params)
        print("pagination params", last_call["pagination"])
        new_params = update_params(new_params, last_call["pagination"])
        res = s.get(url=url, headers=headers, params=new_params)
        if res.status_code == 200:
            content = json.loads(res.content.decode("utf-8"))
            p +=1
            last_call = content
            all_data.append(content)
            sleep(1)
        else:
            print(res.content.decode("utf-8"))
            break
    return pd.DataFrame(all_data)


def get_indiv_contributions(transaction_period=2024, **kwargs):
    url = f"{base_url}schedules/schedule_a/?"
    schedule_data={
        "two_year_transaction_period": transaction_period,
        "min_date": min_date,
        "max_date": max_date,
         "per_page": 100
    }
    res = requests.get(url=url, headers=headers, params=schedule_data)
    content = json.loads(res.content.decode("utf-8"))
    print(content["pagination"])
    if content["pagination"]["last_indexes"]:
        all_data = paginate_results(content, url, schedule_data)
        df = parse_data(all_data)
    else:
        df = parse_data(content)
    write_data(df, min_date=min_date, max_date=max_date)


if __name__ == "__main__":
    min_date = (datetime.now() - timedelta(days=14)).strftime("%m/%d/%Y")
    max_date = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
    get_indiv_contributions(min_date=min_date, max_date=max_date)

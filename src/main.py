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

def write_data(data):
    res = data["results"]
    flatten = []
    for i in res:
        inner_list = eval(i)
        for j in inner_list:
            flatten.append(j)
    df = pd.json_normalize(flatten)
    client = boto3.client('s3')
    date = datetime.now()
    key = f"{date.strftime('%Y')}/{date.strftime('%m')}/ \
            {date.strftime('%d')}/schedule-a.csv"
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
    num_calls = 1
    new_params = params
    last_call = data
    while (last_call["pagination"]["last_indexes"] or \
                p <= last_call["pagination"]["pages"]):
        new_params = update_params(new_params, last_call["pagination"])
        res = s.get(url=url, headers=headers, params=new_params)
        if res.status_code == 200:
            content = json.loads(res.content.decode("utf-8"))
            p +=1
            num_calls += 1
            last_call = content
            all_data.append(content)
            sleep(2)
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
    # print(content["results"])
    all_data = paginate_results(content, url, schedule_data)
    return all_data


if __name__ == "__main__":
    min_date = (datetime.now() - timedelta(days=2)).strftime("%m/%d/%Y")
    max_date = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
    data = get_indiv_contributions(min_date=min_date, max_date=max_date)
    write_data(data=data)

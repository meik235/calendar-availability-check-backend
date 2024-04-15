from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import googleapiclient.discovery
from enum import Enum
from datetime import datetime, timedelta
import pytz
import logging

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Set up the Google Calendar API client
service = googleapiclient.discovery.build('calendar', 'v3', developerKey='AIzaSyDAJCQnvWRSqkEsSNWL0p5clXpQ6wH-wxw')
api_key = 'AIzaSyAdrvSNUmkWLwPS_A9jp69Etx6RLi7wh7g'

class AvailableExperts(str, Enum):
    Person1 = "Person1"
    Person2 = "Person2"
    Person3 = "Person3"
    Person4 = "Person4"
    Person5 = "Person5"

expert_list = ["Person1", "Person2", "Person3", "Person4", "Person5"]

expert_calendar_id = {
    "Person1": "2bbc95bd029478d39239bdd59e976b525ba3bbf89389e46c46add3bb64abd4ad@group.calendar.google.com",
    "Person2": "8a17109242b1d2f9f3abfa2c61c9738d993e686c4c3841d94604714347fe82c4@group.calendar.google.com",
    "Person3": "3c4b74b53f04babf31ea8d912756449b677088a69e06bb1f051e8dcb30ae65a7@group.calendar.google.com",
    "Person4": "8f1114f32c0af8ede52482cb2ff9e89d9c662496ee5d3580fae2a91690824451@group.calendar.google.com",
    "Person5": "b1c742e7564f81bb20c53b01d2fa907eacc05333e480160dfa9ea221d82a23c5@group.calendar.google.com",
}

valid_experts = expert_calendar_id.keys()

@app.get("/get_expert_list")
async def get_expert_list():
    return expert_list

@app.get("/get_slots")
async def get_slots(
    startDateTime: str = Query(..., description="Start date and time", alias="startDateTime"),
    endDateTime: str = Query(..., description="End date and time", alias="endDateTime"),
    expertName: AvailableExperts = Query(..., description="Expert name", alias="expertName")
):
    current_datetime = datetime.now(pytz.utc)
    if startDateTime is None or endDateTime is None or expertName is None:
        raise HTTPException(status_code=400, detail="Please provide all required parameters")
    start_datetime = format_datetime(startDateTime)
    end_datetime = format_datetime(endDateTime)
    if start_datetime < current_datetime:
        raise HTTPException(status_code=422, detail="The start datetime should not be less than the current datetime.")
    if end_datetime < start_datetime:
        raise HTTPException(status_code=422, detail="The end datetime should not be less than the start datetime.")
    if not is_same_day(start_datetime, end_datetime):
        raise HTTPException(status_code=422, detail="Please ensure that the start datetime and end datetime are from the same day.")
    try:
        calendar_id = expert_calendar_id.get(expertName)
        freebusy_query={
            'timeMin': startDateTime,
            'timeMax': endDateTime,
            'timeZone': 'UTC',
            'items': [{'id': calendar_id}]
        }
        freebusy_result = service.freebusy().query(body=freebusy_query).execute()
        busy_slots = freebusy_result['calendars'][calendar_id]['busy']
        errors = freebusy_result['calendars'][calendar_id].get('errors')
        if errors:
            raise HTTPException(status_code=400, detail='Error: {}'.format(errors))
        elif busy_slots:
            free_slots = find_free_slots(start_datetime, end_datetime, busy_slots)
            return JSONResponse(content={'status': 'Busy/Free', 'busy_slots': busy_slots, 'free_slots': free_slots})
        else:
            return JSONResponse(content={'status': 'Free'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
def format_datetime(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc)

def is_same_day(datetime1: datetime, datetime2: datetime) -> bool:
    return datetime1.date() == datetime2.date()

def find_free_slots(start_time, end_time, schedule):
    slots = []
    current_slot_start = start_time
    current_slot_end = start_time + timedelta(minutes=15)
    while current_slot_end <= end_time:
        is_slot_free = True
        for task in schedule:
            task_start = datetime.strptime(task["start"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            task_end = datetime.strptime(task["end"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
            if (
                current_slot_start < task_end
                and current_slot_end > task_start
            ):
                is_slot_free = False
                break
        if is_slot_free:
            slots.append(
                {
                    "start": current_slot_start.astimezone(pytz.timezone('Asia/Kolkata')).isoformat(),
                    "end": current_slot_end.astimezone(pytz.timezone('Asia/Kolkata')).isoformat(),
                }
            )
        current_slot_start += timedelta(minutes=15)
        current_slot_end += timedelta(minutes=15)
    return slots
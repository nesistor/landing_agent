"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

from typing import Any, Callable, List, Optional, cast

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated

from react_agent.configuration import Configuration
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import json


async def search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> Optional[list[dict[str, Any]]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    configuration = Configuration.from_runnable_config(config)
    wrapped = TavilySearchResults(max_results=configuration.max_search_results)
    result = await wrapped.ainvoke({"query": query})
    return cast(list[dict[str, Any]], result)


class GoogleCalendarClient:
    def __init__(self, config: Configuration):
        self.credentials = service_account.Credentials.from_service_account_info(
            json.loads(config.google_service_account_json),
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        self.service = build('calendar', 'v3', credentials=self.credentials)
        self.calendar_id = config.google_calendar_id

async def check_availability(
    start_time: str, 
    duration: int, 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> dict:
    """Sprawdza dostępność terminów w kalendarzu Google"""
    configuration = Configuration.from_runnable_config(config)
    client = GoogleCalendarClient(configuration)
    
    start = datetime.datetime.fromisoformat(start_time)
    end = start + datetime.timedelta(minutes=duration)
    
    events_result = client.service.events().list(
        calendarId=client.calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    if not events_result.get('items'):
        return {"available": True}
    
    # Szukaj najbliższego wolnego terminu
    next_hour = datetime.datetime.now() + datetime.timedelta(hours=1)
    return {
        "available": False,
        "suggested_time": next_hour.isoformat(),
        "message": "Proponowany najbliższy wolny termin: " + next_hour.strftime("%Y-%m-%d %H:%M")
    }

async def book_meeting(
    start_time: str, 
    duration: int, 
    title: str, 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> dict:
    """Automatycznie rezerwuje spotkanie jeśli termin jest dostępny i zwraca linki"""
    configuration = Configuration.from_runnable_config(config)
    client = GoogleCalendarClient(configuration)
    
    # Sprawdź dostępność
    availability = await check_availability(start_time, duration, config=config)
    if not availability.get("available"):
        return {
            "status": "unavailable",
            "message": availability.get("message")
        }
    
    # Utwórz wydarzenie
    end_time = datetime.datetime.fromisoformat(start_time) + datetime.timedelta(minutes=duration)
    
    event = {
        'summary': title,
        'start': {'dateTime': start_time, 'timeZone': 'Europe/Warsaw'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Europe/Warsaw'},
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet_{datetime.datetime.now().timestamp()}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }
    
    created_event = client.service.events().insert(
        calendarId=client.calendar_id,
        conferenceDataVersion=1,
        body=event
    ).execute()
    
    # Generuj linki
    meet_link = created_event.get('hangoutLink', 'https://meet.google.com/new')
    calendar_link = f"https://calendar.google.com/calendar/event?eid={created_event['id']}"
    
    return {
        "status": "confirmed",
        "meet_link": meet_link,
        "calendar_link": calendar_link,
        "event_id": created_event['id']
    }

async def create_app_specification(
    purpose: str,
    target_platforms: List[str],
    main_features: List[str],
    design_preferences: str,
    budget_range: str,
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> dict:
    """Tworzy szczegółową specyfikację aplikacji i wycenę"""
    # Logika wyceny
    base_cost = 10000
    platform_cost = len(target_platforms) * 3000
    features_cost = len(main_features) * 2000
    design_multiplier = 1.5 if "premium" in design_preferences.lower() else 1.2
    
    total_cost = (base_cost + platform_cost + features_cost) * design_multiplier
    timeline_weeks = 4 + (len(target_platforms) * 2) + (len(main_features) * 1)
    
    return {
        "spec_id": f"spec_{datetime.datetime.now().timestamp()}",
        "estimated_cost": f"{total_cost:.2f} PLN",
        "timeline": f"{timeline_weeks} tygodni",
        "requirements": {
            "purpose": purpose,
            "platforms": target_platforms,
            "features": main_features,
            "design": design_preferences,
            "budget": budget_range
        },
        "next_steps": [
            "Weryfikacja wymagań",
            "Podpisanie umowy",
            "Płatność 30% zaliczki"
        ]
    }

TOOLS: List[Callable[..., Any]] = [search, check_availability, book_meeting, create_app_specification]
